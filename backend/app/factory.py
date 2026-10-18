from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response
from typing import Optional

from pydantic import AliasChoices, BaseModel, Field

from app.ml_client import probe_ml
from app.scenario import ScenarioEngine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class IncidentIn(BaseModel):
    client_id: str
    source_id: str = "unknown"
    lon: float = Field(validation_alias=AliasChoices("lon", "lng"), ge=-180, le=180, allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    message: str = ""
    people_affected: Optional[int] = Field(default=None, validation_alias=AliasChoices("people_affected", "people"))
    place: str = Field(default="", max_length=180)
    medical: Optional[str] = None
    mobility: Optional[str] = None


class RouteIn(BaseModel):
    origin: list[float] = Field(min_length=2, max_length=2)
    destination: list[float] = Field(min_length=2, max_length=2)


class ClosureIn(BaseModel):
    edge_ids: list[str]
    reason: str = "simulation"


class ReviewIn(BaseModel):
    decision: str


class GotoIn(BaseModel):
    step: int = Field(ge=0)


class Hub:
    def __init__(self):
        self.connections = set()

    async def connect(self, socket: WebSocket) -> None:
        await socket.accept()
        self.connections.add(socket)

    def disconnect(self, socket: WebSocket) -> None:
        self.connections.discard(socket)

    async def broadcast(self, payload: dict) -> None:
        dead = []
        for socket in list(self.connections):
            try:
                await socket.send_json(payload)
            except Exception:
                dead.append(socket)
        for socket in dead:
            self.connections.discard(socket)


def create_app(graph, anchors: dict, db_path: str) -> FastAPI:
    app = FastAPI(title="SOSora", version="0.1.0")
    app.add_middleware(GZipMiddleware, minimum_size=800)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    engine = ScenarioEngine(graph, anchors, _store(db_path))
    hub = Hub()
    app.state.engine = engine
    app.state.hub = hub
    from app.radio_api import router as radio_router

    app.include_router(radio_router)
    from app.mobile_api import router as mobile_router
    app.include_router(mobile_router)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "demo_mode": engine.public_state()["system"]["demo_mode"],
            "graph_nodes": graph.number_of_nodes(),
            "graph_edges": graph.number_of_edges(),
            "ml": engine.public_state()["ml"],
        }

    @app.get("/api/ml/status")
    def ml_status():
        return probe_ml()

    @app.get("/api/scenarios")
    def scenarios():
        state = engine.public_state()
        return {"scenario": state["scenario"], "steps": state["steps"]}

    @app.post("/api/scenarios/reset")
    async def reset():
        engine.reset()
        state = engine.public_state()
        await hub.broadcast({"type": "state", "state": state})
        return state

    @app.post("/api/scenarios/advance")
    async def advance():
        engine.advance()
        state = engine.public_state()
        await hub.broadcast({"type": "state", "state": state})
        return state

    @app.post("/api/scenarios/goto")
    async def goto(body: GotoIn):
        engine.goto(body.step)
        state = engine.public_state()
        await hub.broadcast({"type": "state", "state": state})
        return state

    @app.get("/api/state")
    def state():
        return engine.public_state()

    @app.get("/api/incidents")
    def incidents():
        return {"incidents": engine.incidents}

    @app.post("/api/incidents")
    async def create_incident(body: IncidentIn):
        result = engine.add_incident(body.model_dump())
        if not result["duplicate"]:
            incident = result["incident"]
            engine._emit(
                "sos",
                f"Incident {incident['id']} stored from {incident['source_id']}.",
                20,
            )
        state_out = engine.public_state()
        await hub.broadcast({"type": "state", "state": state_out})
        from app.mobile_api import incident_dto
        return {**incident_dto(result["incident"]), "incident": result["incident"], "duplicate": result["duplicate"], "state": state_out}

    @app.get("/api/roads")
    def roads():
        path = DATA_DIR / "roads.geojson"
        if not path.exists():
            return {"type": "FeatureCollection", "features": []}
        return Response(content=path.read_text(), media_type="application/geo+json")

    @app.post("/api/routes/calculate")
    def calculate(body: RouteIn):
        from app.routing import compute_route

        route = compute_route(graph, (body.origin[0], body.origin[1]), (body.destination[0], body.destination[1]), engine.closed_ids)
        return {"route": route, "closed_edge_ids": engine.closed_ids}

    @app.post("/api/roads/closures")
    async def closures(body: ClosureIn):
        engine.apply_closures(body.edge_ids)
        state_out = engine.public_state()
        await hub.broadcast({"type": "state", "state": state_out})
        return state_out

    @app.post("/api/imagery/analyze")
    def analyze():
        from app.ml_client import fixture_detection

        detection = fixture_detection(anchors)
        if detection.get("map_ready"):
            engine.detections = [detection]
            engine.ml_mode = "mock"
            engine.ml_detail = "Analyze returned the labeled scenario fixture. The vision model was not called."
            engine.revision += 1
        return {"prediction": detection, "state": engine.public_state()}

    @app.get("/api/events")
    def events():
        return {"events": engine.events}

    @app.post("/api/review")
    async def review(body: ReviewIn):
        if body.decision == "acknowledged":
            engine.acknowledge()
        state_out = engine.public_state()
        await hub.broadcast({"type": "state", "state": state_out})
        return state_out

    @app.websocket("/ws/events")
    async def events_socket(socket: WebSocket):
        await hub.connect(socket)
        try:
            await socket.send_json({"type": "state", "state": engine.public_state()})
            while True:
                await socket.receive_text()
        except WebSocketDisconnect:
            hub.disconnect(socket)

    return app


def _store(db_path: str):
    from app.store import Store

    return Store(db_path)


def empty_roads() -> dict:
    return json.loads('{"type":"FeatureCollection","features":[]}')
