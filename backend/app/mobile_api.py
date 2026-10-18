"""iOS wire adapters; Command state and routing contracts stay intact."""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.ml_client import demo_mode
from app.radio_api import RadioIn, build_report, run_report, _event

router = APIRouter()


def incident_dto(incident):
    return {**incident, "lng": incident["lon"], "people": incident.get("people_affected"),
            "description": incident["message"], "source": incident["source_id"],
            "priority": incident["urgency"], "status": incident.get("status", "Received")}


@router.get("/api/health")
def health():
    return {"ok": True, "mode": "demo" if demo_mode() else "live", "database": "sqlite"}


@router.get("/api/mobile/state")
def state(request: Request):
    engine = request.app.state.engine
    return {"stage": engine.step, "incidents": [incident_dto(i) for i in engine.incidents]}


@router.get("/api/road-segments")
def catalog(request: Request):
    segments = {}
    for _, _, edge in request.app.state.engine.graph.edges(data=True):
        points = edge["geometry"]
        segments[edge["id"]] = {"id": edge["id"], "name": edge.get("name"),
                                "lng": sum(p[0] for p in points) / len(points),
                                "lat": sum(p[1] for p in points) / len(points)}
    return {"segments": list(segments.values())}


class StatusIn(BaseModel):
    status: Literal["Queued", "Received", "Acknowledged", "Under review", "Resolved"]


@router.patch("/api/incidents/{incident_id}")
async def update_status(incident_id: str, body: StatusIn, request: Request):
    engine = request.app.state.engine
    incident = next((i for i in engine.incidents if i["id"] == incident_id), None)
    if incident is None:
        raise HTTPException(404, "Unknown incident")
    incident["status"] = body.status
    engine.store.save_incident(incident)
    engine.revision += 1
    await request.app.state.hub.broadcast({"type": "state", "state": engine.public_state()})
    return incident_dto(incident)


class RoadReportIn(BaseModel):
    segment_id: str
    condition: Literal["passable", "blocked", "unknown"]
    source: str = "operator"
    evidence: str = Field(default="", max_length=2000)
    verification: str = "unverified"


@router.post("/api/road-reports")
async def road_report(body: RoadReportIn, request: Request):
    edges = {e["id"]: e for _, _, e in request.app.state.engine.graph.edges(data=True)}
    edge = edges.get(body.segment_id)
    if edge is None:
        raise HTTPException(404, "Unknown segment")
    points = edge["geometry"]
    at = datetime.now(timezone.utc)
    radio_id = "radio-" + uuid4().hex[:8]
    message = f"{edge.get('name') or body.segment_id}: {body.condition}. {body.evidence}"
    radio = RadioIn(message=message, source_type="responder_radio", unit="iOS operator")
    parse = {"event_type": {"blocked": "road_blocked", "passable": "road_open", "unknown": "other"}[body.condition],
             "road_name": edge.get("name")}
    report = {**build_report(parse, radio, at), "segment_id": body.segment_id,
              "near_lon": sum(p[0] for p in points) / len(points),
              "near_lat": sum(p[1] for p in points) / len(points)}
    await _event(request, "radio_received", {"radio_id": radio_id, "source_type": "responder_radio", "message": message})
    outcome = await run_report(request, report)
    command_state = request.app.state.engine.public_state()
    await request.app.state.hub.broadcast({"type": "state", "state": command_state})
    return {"radio_id": radio_id, **outcome, "state": command_state}
