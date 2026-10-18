"""Live weather and the archived Helene track. Failures stay empty; nothing is invented."""
from __future__ import annotations

import html
import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELENE_PATH = ROOT / "frontend" / "helene-best-track.geojson"
NWS_OBSERVATION = "https://api.weather.gov/stations/KAVL/observations/latest"
USGS_GAUGE = "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=03451000&parameterCd=00065,00060&siteStatus=all"
USER_AGENT = "SOSoraDemo/0.2 (hackathon demo; local dashboard)"
_CACHE: dict[str, tuple[float, dict]] = {}
_TTL = 600


def helene_track() -> dict:
    if not HELENE_PATH.exists():
        return {
            "available": False,
            "mode": "historical_helene",
            "reason": "The NHC best-track file is not in this project.",
        }
    payload = json.loads(HELENE_PATH.read_text())
    payload["available"] = True
    payload["mode"] = "historical_helene"
    payload["label"] = "HISTORICAL TRACK · Hurricane Helene · September 2024"
    return payload


def current_conditions() -> dict:
    cached = _CACHE.get("current")
    now = time.time()
    if cached and now - cached[0] < _TTL:
        body = dict(cached[1])
        body["cache"] = "memory"
        return body
    observation = _read_json(NWS_OBSERVATION, accept="application/geo+json")
    gauge = _read_json(USGS_GAUGE, accept="application/json")
    body = {
        "available": bool(observation["ok"] or gauge["ok"]),
        "mode": "current",
        "label": "CURRENT CONDITIONS",
        "as_of": None,
        "observation": _observation(observation["data"]) if observation["ok"] else None,
        "gauge": _gauge(gauge["data"]) if gauge["ok"] else None,
        "errors": [item["error"] for item in (observation, gauge) if not item["ok"]],
    }
    times = [part.get("observed_at") for part in (body["observation"], body["gauge"]) if part and part.get("observed_at")]
    body["as_of"] = max(times) if times else None
    if not body["available"]:
        body["reason"] = "Current weather sources did not respond. No substitute values are shown."
    else:
        _CACHE["current"] = (now, body)
    return body


def _ssl_context() -> ssl.SSLContext:
    for candidate in ("/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"):
        if Path(candidate).exists():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def _read_json(url: str, accept: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urllib.request.urlopen(request, timeout=8, context=_ssl_context()) as response:
            return {"ok": True, "data": json.loads(response.read().decode())}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": f"{url} unavailable ({exc.__class__.__name__})"}


def _observation(data: dict) -> dict:
    props = data.get("properties") or {}
    coords = (data.get("geometry") or {}).get("coordinates") or [None, None]
    temperature = (props.get("temperature") or {}).get("value")
    wind = (props.get("windSpeed") or {}).get("value")
    return {
        "provider": "National Weather Service",
        "station": props.get("stationName") or "KAVL",
        "station_id": props.get("stationId") or "KAVL",
        "text": props.get("textDescription"),
        "temperature_c": temperature,
        "wind_kmh": wind,
        "observed_at": props.get("timestamp"),
        "lng": coords[0],
        "lat": coords[1],
        "url": NWS_OBSERVATION,
        "note": "Current airport observation for Asheville. Not a September 2024 reconstruction.",
    }


def _gauge(data: dict) -> dict | None:
    series = ((data.get("value") or {}).get("timeSeries")) or []
    if not series:
        return None
    info = series[0].get("sourceInfo") or {}
    geo = ((info.get("geoLocation") or {}).get("geogLocation")) or {}
    readings = []
    observed = None
    for item in series:
        values = ((item.get("values") or [{}])[0].get("value")) or []
        if not values:
            continue
        latest = values[-1]
        observed = latest.get("dateTime") or observed
        variable = item.get("variable") or {}
        readings.append({
            "name": html.unescape(variable.get("variableName") or ""),
            "unit": (variable.get("unit") or {}).get("unitCode"),
            "value": latest.get("value"),
            "qualifier": ",".join(latest.get("qualifiers") or []),
        })
    return {
        "provider": "USGS Water Services",
        "site_no": "03451000",
        "name": info.get("siteName") or "SWANNANOA RIVER AT BILTMORE, NC",
        "lat": geo.get("latitude"),
        "lng": geo.get("longitude"),
        "observed_at": observed,
        "readings": readings,
        "url": USGS_GAUGE,
        "note": "Current gauge reading. Not the September 2024 flood crest.",
    }
