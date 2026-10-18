from __future__ import annotations

import os

import httpx

from app.geo import buffer_line, is_geographic

ISOLATED = "POTENTIALLY ISOLATED — No available path in the current road graph."


def demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "true").lower() in {"1", "true", "yes", "on"}


def ml_base_url() -> str:
    return os.environ.get("ML_SERVICE_BASE_URL", "http://127.0.0.1:8002").rstrip("/")


def fixture_detection(anchors: dict) -> dict:
    ring = buffer_line(anchors["closure_geometry"], 18)
    return {
        "id": "sim-flood-001",
        "class": "flooded_road",
        "confidence": None,
        "confidence_note": "Not measured. This polygon is a scenario fixture around the segment the simulation closes.",
        "geometry": {"type": "Polygon", "coordinates": [ring]} if ring else None,
        "road_segment_ids": list(anchors["closure_edge_ids"]),
        "review_status": "unverified",
        "inference_mode": "mock",
        "model_version": None,
        "image_id": "scenario-corridor",
        "map_ready": bool(ring),
        "crs": "EPSG:4326",
    }


def normalize_prediction(payload: dict) -> dict:
    detections = []
    for item in payload.get("detections", []):
        geometry = item.get("geometry") or {}
        ready = is_geographic(geometry)
        detections.append(
            {
                **item,
                "map_ready": ready,
                "map_note": None
                if ready
                else "Prediction is not in geographic coordinates, so it is not drawn on the map.",
            }
        )
    return {
        "image_id": payload.get("image_id"),
        "model_version": payload.get("model_version"),
        "inference_mode": payload.get("inference_mode", "real"),
        "crs": payload.get("crs"),
        "detections": detections,
    }


def template_explanation(context: dict) -> dict:
    status = context.get("route_status")
    length_m = context.get("length_m")
    name = context.get("closure_name") or "the selected segment"
    if status == "unreachable":
        access = ISOLATED
    elif status == "rerouted" and length_m:
        access = f"A replacement path of {length_m / 1000:.2f} km is on the graph and avoids the closed segment."
    elif status == "proposed" and length_m:
        access = f"A candidate path of {length_m / 1000:.2f} km is on the graph. No closure is applied."
    else:
        access = "No active candidate path."
    return {
        "inference_mode": "mock",
        "provider": "local-template",
        "model": None,
        "summary": (
            f"Fictional report at the scenario objective. The simulated closure is on {name}. "
            "This paragraph is a local template filled from the routing result. Nemotron was not called."
        ),
        "access": access,
        "uncertainties": [
            "The closure is a simulation action, not an authoritative road status.",
            "Suspected damage geometry is a fixture on that segment, not a model mask.",
            "The road graph is current OpenStreetMap, not a 27 September 2024 snapshot.",
            "A graph path does not mean the physical road is safe to drive.",
        ],
        "human_review": True,
    }


def explain_incident(context: dict) -> dict:
    local = template_explanation(context)
    if demo_mode():
        return local
    try:
        response = httpx.post(f"{ml_base_url()}/ml/incident/explain", json=context, timeout=2.5)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("explanation was not an object")
        data.setdefault("inference_mode", "real")
        data.setdefault("provider", "ml-service")
        return data
    except Exception:
        local["inference_mode"] = "unavailable"
        local["summary"] = "Model service did not respond. " + local["summary"]
        return local


def probe_ml() -> dict:
    if demo_mode():
        return {"mode": "mock", "detail": "Demo mode is on. The model service is not called."}
    try:
        response = httpx.get(f"{ml_base_url()}/health", timeout=0.8)
        response.raise_for_status()
        return {"mode": "real", "detail": "Model service responded.", "body": response.json()}
    except Exception:
        return {"mode": "unavailable", "detail": "Model service did not respond."}
