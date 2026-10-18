"""Field radio intake: message -> Nemotron Lightning parse -> tool-calling agent -> map.

The hero path for the demo. All demo messages and SOS incidents are SIMULATED; roads
and bridges are real OpenStreetMap data for Swannanoa, NC.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.agent import RadioAgent
from app.ml_client import demo_mode, ml_base_url

router = APIRouter()

CLAIMS = {"bridge_collapse": "impassable", "road_washout": "impassable", "flooding": "impassable",
          "road_blocked": "impassable", "road_open": "open"}
CHANNELS = {"responder_radio": "radio", "beacon": "lora", "resident": "sms"}
CREDIBLE = {"responder_radio", "beacon"}

# Eastern Warren Wilson Road bridge over the Swannanoa River (OSM way 549633356).
# In our map area it is the only road crossing for the neighbourhoods north of it.
BEACON_POSITION = {"lon": -82.42702, "lat": 35.61258}

HERO = ("[SIMULATED] Command, Engine 4... the bridge on Warren Wilson Road is gone, river took it... "
        "three families on the far side, we can't get across. Over.")
OPEN_REPORT = "[SIMULATED] Command, DOT crew... Warren Wilson Road bridge is open, inspected and clear. Over."

# Cached parses for SIMULATED demo messages, used only in DEMO_MODE or when the
# model service is unreachable. Unknown text is never guessed: it goes to review.
FIXTURES = {
    HERO: dict(event_type="bridge_collapse", road_name="Warren Wilson Road", road_ref=None, landmark=None,
               location_text="bridge on Warren Wilson Road", people_count=3, urgency="critical"),
    OPEN_REPORT: dict(event_type="road_open", road_name="Warren Wilson Road", road_ref=None, landmark=None,
                      location_text="Warren Wilson Road bridge", people_count=None, urgency="low"),
}

# SIMULATED SOS incidents placed on real roads. North of the bridge: cut off when it fails.
SEED = [
    ("demo-sos-01", -82.40719, 35.63129, "Bee Tree Road. Water in the house, 2 adults and a baby.", 3, "infant"),
    ("demo-sos-02", -82.41446, 35.61981, "Riddle Road. Elderly couple, no power, oxygen running low.", 2, "oxygen"),
    ("demo-sos-03", -82.41475, 35.64090, "Long Branch Road. Family of 4, road below the house washed out.", 4, None),
    ("demo-sos-04", -82.41149, 35.62712, "Watch Knob Lane. Neighbor hurt by a fallen tree.", 1, "injury"),
    ("demo-sos-05", -82.42622, 35.62413, "Smokey Mountain Drive. 5 people sheltering, need water.", 5, None),
    ("demo-sos-06", -82.38961, 35.60577, "Grovemont Avenue. Basement flooding, family of 3.", 3, None),
    ("demo-sos-07", -82.40563, 35.58711, "Patton Cove Road. Stranded driver, car stalled in water.", 1, None),
    ("demo-sos-08", -82.39470, 35.60405, "Old US Highway 70. Two people on a porch roof.", 2, None),
    ("demo-sos-09", -82.36796, 35.62178, "Lake Eden Road. Diabetic resident needs insulin.", 1, "insulin"),
]


class RadioIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    source_type: Literal["responder_radio", "beacon", "resident"] = "responder_radio"
    unit: Optional[str] = Field(default=None, max_length=80)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    received_at: Optional[datetime] = None


class ConfirmIn(BaseModel):
    radio_id: str
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


def _norm(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def _fixture(message: str) -> Optional[dict]:
    for text, parse in FIXTURES.items():
        if _norm(text) == _norm(message):
            return {**parse, "needs_review": True, "raw": message, "parse_mode": "cached_demo"}
    return None


async def parse_message(body: RadioIn, received_at: datetime) -> dict:
    if demo_mode():
        return _fixture(body.message) or _unparsed(body.message, "demo_unknown_message")
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(ml_base_url() + "/ml/radio/parse", json={
                "message": body.message, "received_at": received_at.isoformat(),
                "channel": CHANNELS[body.source_type]})
            response.raise_for_status()
            return {**response.json(), "parse_mode": "nemotron_lightning"}
    except (httpx.HTTPError, ValueError):
        cached = _fixture(body.message)
        return cached or _unparsed(body.message, "model_service_unavailable")


def _unparsed(message: str, reason: str) -> dict:
    return {"event_type": "other", "road_name": None, "road_ref": None, "landmark": None,
            "location_text": message, "people_count": None, "urgency": "low", "needs_review": True,
            "raw": message, "parse_mode": reason}


def build_report(parse: dict, body: RadioIn, received_at: datetime) -> dict:
    report = {"road_name": parse.get("road_name"), "road_ref": parse.get("road_ref"),
              "landmark": parse.get("landmark"),
              # Grounded in the literal text, so a model labeling it road_blocked still searches bridges.
              "bridge_only": parse.get("event_type") == "bridge_collapse" or "bridge" in body.message.casefold(),
              "claim": CLAIMS.get(parse.get("event_type"), "unverified"),
              "event_type": parse.get("event_type"), "people_count": parse.get("people_count"),
              "urgency": parse.get("urgency"), "text": body.message,
              "source": {"type": body.source_type, "unit": body.unit, "time": received_at.isoformat(),
                         "text": body.message, "credible": body.source_type in CREDIBLE,
                         "verified": False, "simulated": demo_mode()}}
    if body.lon is not None and body.lat is not None:
        report.update(near_lon=body.lon, near_lat=body.lat)
    return {k: v for k, v in report.items() if v is not None}


async def run_report(request: Request, report: dict) -> dict:
    state = request.app.state
    if not hasattr(state, "radio_lock"):
        state.radio_lock = asyncio.Lock()
    async with state.radio_lock:
        agent = RadioAgent(state.engine, state.hub, report)
        assessment = await agent.run()
        return {"assessment": assessment, "statuses": agent.statuses, "agent_runtime": dict(agent.runtime)}


async def _event(request: Request, kind: str, payload: dict) -> None:
    engine = request.app.state.engine
    event = {"id": len(engine.events) + 1, "at": datetime.now(timezone.utc).isoformat(), "kind": kind,
             "step": engine.step, "message": payload.get("message", kind), "simulated": demo_mode(), **payload}
    engine.events.append(event)
    await request.app.state.hub.broadcast({"type": "radio_event", "event": event})


@router.post("/api/radio")
async def radio(body: RadioIn, request: Request):
    """One field message in, one map update out. Every agent tool call streams on /ws/events."""
    engine = request.app.state.engine
    received_at = body.received_at or datetime.now(timezone.utc)
    radio_id = "radio-" + uuid.uuid4().hex[:8]
    await _event(request, "radio_received", {"radio_id": radio_id, "source_type": body.source_type,
                                             "unit": body.unit, "message": body.message})
    parse = await parse_message(body, received_at)
    await _event(request, "radio_parsed", {"radio_id": radio_id, "parse": parse,
                                           "message": f"Parsed as {parse['event_type']}"})
    if parse["event_type"] == "sos" and body.lon is not None and body.lat is not None:
        result = engine.add_incident({"client_id": radio_id, "source_id": body.source_type, "lon": body.lon,
                                      "lat": body.lat, "message": body.message,
                                      "people_affected": parse.get("people_count")})
        outcome = {"incident": result["incident"]}
    else:
        report = build_report(parse, body, received_at)
        if not hasattr(request.app.state, "radio_reports"):
            request.app.state.radio_reports = {}
        request.app.state.radio_reports[radio_id] = report
        outcome = await run_report(request, report)
    state = engine.public_state()
    await request.app.state.hub.broadcast({"type": "state", "state": state})
    return {"radio_id": radio_id, "parse": parse, **outcome, "state": state}


@router.post("/api/radio/confirm")
async def confirm(body: ConfirmIn, request: Request):
    """Operator picks the location for an ambiguous report; the agent reruns with it."""
    reports = getattr(request.app.state, "radio_reports", {})
    if body.radio_id not in reports:
        raise HTTPException(404, "Unknown radio report")
    report = {**reports[body.radio_id], "near_lon": body.lon, "near_lat": body.lat}
    report["source"] = {**report["source"], "operator_confirmed_location": True}
    await _event(request, "radio_location_confirmed", {"radio_id": body.radio_id, "lon": body.lon,
                                                       "lat": body.lat, "message": "Operator confirmed location"})
    outcome = await run_report(request, report)
    state = request.app.state.engine.public_state()
    await request.app.state.hub.broadcast({"type": "state", "state": state})
    return {"radio_id": body.radio_id, **outcome, "state": state}


@router.get("/api/radio/status")
def radio_status(request: Request):
    engine = request.app.state.engine
    return {"segment_statuses": getattr(engine, "segment_statuses", {}),
            "assessment": getattr(engine, "agent_assessment", None),
            "closed_edge_ids": engine.closed_ids,
            "incidents": [{k: i.get(k) for k in ("id", "client_id", "lon", "lat", "message",
                           "people_affected", "reachable")} for i in engine.incidents]}


class ImageryOutageIn(BaseModel):
    offline: bool


@router.post("/api/radio/demo/imagery")
async def imagery_outage(body: ImageryOutageIn, request: Request):
    """Simulated evidence-service outage; the basemap/imagery layers are unchanged."""
    engine = request.app.state.engine
    engine.imagery_offline = body.offline
    engine.revision += 1
    await _event(request, "imagery_outage", {
        "offline": body.offline, "simulated": True,
        "message": "[SIMULATED] Imagery offline" if body.offline else "[SIMULATED] Imagery restored"})
    state = engine.public_state()
    await request.app.state.hub.broadcast({"type": "state", "state": state})
    return {"state": state}


@router.post("/api/radio/demo/seed")
async def seed(request: Request):
    """Reset to the radio demo: 9 SIMULATED SOS incidents on real Swannanoa roads."""
    engine = request.app.state.engine
    engine.reset()
    engine.segment_statuses = {}
    engine.agent_assessment = None
    for client_id, lon, lat, message, people, medical in SEED:
        engine.add_incident({"client_id": client_id, "source_id": "simulated_seed", "lon": lon, "lat": lat,
                             "message": "[SIMULATED] " + message, "people_affected": people, "medical": medical})
    request.app.state.radio_reports = {}
    from app.routing import incident_routes
    bases = engine.anchors.get("rescue_bases") or [engine.anchors["origin"]]
    routes = incident_routes(engine.graph, bases, engine.incidents, engine.closed_ids, engine.route_snaps)
    for incident in engine.incidents:
        incident["route"] = routes[incident["id"]]
        incident["reachable"] = incident["route"]["status"] == "ok"
    state = engine.public_state()
    await request.app.state.hub.broadcast({"type": "state", "state": state})
    return {"seeded": len(SEED), "hero_message": HERO, "open_report": OPEN_REPORT,
            "beacon_position": BEACON_POSITION, "state": state}


# ---------------------------------------------------------------------------
# SOSora Beacon: Raspberry Pi with USB mic + water-level sensor at a known crossing.
# Registry of deployed beacons. A beacon's fixed position lets the agent resolve
# "the bridge" without asking the operator. Add new beacons here (see beacon/README.md).
# ---------------------------------------------------------------------------
BEACONS = {
    "beacon-ww-bridge": {"name": "Warren Wilson Road bridge, Swannanoa River", "road_name": "Warren Wilson Road",
                         "bridge": True, **BEACON_POSITION},
}


class ReadingIn(BaseModel):
    water_level_cm: float = Field(ge=0, le=2000)
    threshold_cm: float = Field(default=30, gt=0, le=2000)
    measured_at: Optional[datetime] = None


def _beacon(beacon_id: str) -> dict:
    if beacon_id not in BEACONS:
        raise HTTPException(404, f"Unknown beacon {beacon_id}; register it in BEACONS")
    return BEACONS[beacon_id]


@router.get("/api/beacons")
def beacons():
    return {"beacons": [{"id": k, **v} for k, v in BEACONS.items()]}


@router.post("/api/beacon/{beacon_id}/reading")
async def beacon_reading(beacon_id: str, body: ReadingIn, request: Request):
    """Water-level sensor reading. Over threshold -> flooding report through the agent.

    Sensor data skips language parsing: it is already structured, so it goes straight to
    the same tool-calling agent and trust rule as voice reports.
    """
    beacon = _beacon(beacon_id)
    at = body.measured_at or datetime.now(timezone.utc)
    flooded = body.water_level_cm >= body.threshold_cm
    await _event(request, "sensor_reading", {"beacon_id": beacon_id, "water_level_cm": body.water_level_cm,
                                             "threshold_cm": body.threshold_cm, "over_threshold": flooded,
                                             "message": f"{beacon['name']}: water {body.water_level_cm:.0f} cm"})
    if not flooded:
        return {"beacon_id": beacon_id, "over_threshold": False, "state": request.app.state.engine.public_state()}
    text = (f"Beacon {beacon_id} water-level sensor: {body.water_level_cm:.0f} cm at {beacon['name']} "
            f"(threshold {body.threshold_cm:.0f} cm).")
    report = {"road_name": beacon["road_name"], "bridge_only": beacon.get("bridge", False),
              "near_lon": beacon["lon"], "near_lat": beacon["lat"], "claim": "impassable",
              "event_type": "flooding", "urgency": "high", "text": text,
              "source": {"type": "beacon_sensor", "unit": beacon_id, "time": at.isoformat(), "text": text,
                         "credible": True, "verified": False, "simulated": demo_mode()}}
    outcome = await run_report(request, report)
    state = request.app.state.engine.public_state()
    await request.app.state.hub.broadcast({"type": "state", "state": state})
    return {"beacon_id": beacon_id, "over_threshold": True, **outcome, "state": state}


@router.post("/api/radio/audio")
async def radio_audio(request: Request):
    """Voice report from a Beacon or radio bridge: WAV in, same pipeline as /api/radio.

    multipart/form-data fields: file (WAV), source_type, beacon_id (optional), unit (optional).
    A beacon_id attaches that beacon's known position so the agent can resolve the road.
    """
    from app.asr import ASRUnavailable, transcribe

    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise HTTPException(422, "file is required")
    audio = await upload.read()
    if not audio or len(audio) > 20_000_000:
        raise HTTPException(422, "audio must be 1 byte to 20 MB")
    try:
        heard = await transcribe(audio, upload.filename or "audio.wav")
    except ASRUnavailable as exc:
        raise HTTPException(503, str(exc))
    beacon_id = form.get("beacon_id")
    position = {}
    if beacon_id:
        beacon = _beacon(str(beacon_id))
        position = {"lon": beacon["lon"], "lat": beacon["lat"]}
    await _event(request, "voice_transcribed", {"text": heard["text"], "asr_mode": heard["mode"],
                                                "beacon_id": beacon_id, "message": "Voice report transcribed"})
    body = RadioIn(message=heard["text"], source_type=str(form.get("source_type") or ("beacon" if beacon_id else "responder_radio")),
                   unit=form.get("unit") or beacon_id, **position)
    result = await radio(body, request)
    return {"transcript": heard, **result}
