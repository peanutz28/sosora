from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.ml_client import ISOLATED, demo_mode, explain_incident, fixture_detection
from app.routing import compute_route

EASTERN = ZoneInfo("America/New_York")
START = datetime(2024, 9, 27, 14, 12, tzinfo=EASTERN)

STEPS = [
    ("situation", "Standby", "Normal conditions"),
    ("initial_route", "Route", "Initial access route"),
    ("imagery", "Imagery", "Post-event imagery"),
    ("detection", "Evidence", "Damage evidence"),
    ("closure", "Closure", "Simulated closure"),
    ("invalidate", "Invalidate", "Route invalidated"),
    ("reroute", "Reroute", "Graph recalculated"),
    ("sos", "SOS", "SOS received"),
    ("explain", "Interpret", "Interpretation"),
    ("review", "Review", "Operator review"),
]

IMAGERY = {
    "before": {
        "label": "Earlier mosaic",
        "release_date": "2024-09-19",
        "release": "20337",
        "tiles": [
            "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/20337/{z}/{y}/{x}"
        ],
        "attribution": "Esri World Imagery Wayback",
    },
    "after": {
        "label": "Later mosaic",
        "release_date": "2025-01-30",
        "release": "36557",
        "tiles": [
            "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/36557/{z}/{y}/{x}"
        ],
        "attribution": "Esri World Imagery Wayback",
    },
    "alignment_note": (
        "Esri Wayback release dates, not confirmed local capture times. "
        "The two mosaics are not a controlled co-registered pair. "
        "The swipe is geographic context, not pixel-accurate change detection."
    ),
}

DEMO_SOS = {
    "client_id": "sos-swannanoa-demo-01",
    "source_id": "demo-handset-04",
    "message": "Water is at the doors. Two adults and a child are inside. One adult cannot walk out. The road toward the highway is underwater.",
    "people_affected": 3,
    "medical": "Child has asthma. Inhaler is nearly empty.",
    "mobility": "One adult needs assistance to move.",
}


class ScenarioEngine:
    def __init__(self, graph, anchors: dict, store):
        self.graph = graph
        self.anchors = anchors
        self.store = store
        self.revision = 0
        self.reset()

    def reset(self) -> None:
        self.step = 0
        self.clock = START
        self.revision += 1
        self.incidents = []
        self.events = []
        self.closed_ids = []
        self.detections = []
        self.explanation = None
        self.review_status = "not_requested"
        self.proposed = None
        self.active_route = None
        self.alternate = None
        self.route_status = "none"
        self.imagery_on = False
        self.ml_mode = "mock" if demo_mode() else "unchecked"
        self.ml_detail = (
            "Demo mode is on. The model service is not called."
            if demo_mode()
            else "Model service has not been called yet."
        )
        self.store.reset()
        self._situation()

    def advance(self) -> None:
        if self.step >= len(STEPS) - 1:
            return
        self.step += 1
        getattr(self, f"_{STEPS[self.step][0]}")()
        self.revision += 1

    def add_incident(self, payload: dict) -> dict:
        existing = next((item for item in self.incidents if item["client_id"] == payload["client_id"]), None)
        if existing:
            self._emit("sos", "Retransmitted SOS ignored. The existing incident was kept.", 15)
            self.revision += 1
            return {"incident": existing, "duplicate": True}
        incident = {
            "id": f"SOS-{len(self.incidents) + 1:03d}",
            "client_id": payload["client_id"],
            "source_id": payload.get("source_id") or "unknown",
            "lon": payload["lon"],
            "lat": payload["lat"],
            "message": payload.get("message") or "",
            "people_affected": payload.get("people_affected"),
            "medical": payload.get("medical"),
            "mobility": payload.get("mobility"),
            "urgency": "critical" if payload.get("medical") or (payload.get("people_affected") or 0) >= 3 else "watch",
            "delivery_status": "received",
            "verification": "unverified",
            "created_at": self.clock.isoformat(),
        }
        self.incidents.append(incident)
        self.store.save_incident(incident)
        self.revision += 1
        return {"incident": incident, "duplicate": False}

    def acknowledge(self) -> None:
        if self.review_status != "requested":
            return
        self.review_status = "acknowledged"
        self._emit("review", "Operator acknowledged the incident. No unit was dispatched.", 30)
        self.revision += 1

    def apply_closures(self, edge_ids: list) -> None:
        self.closed_ids = list(dict.fromkeys([*self.closed_ids, *edge_ids]))
        self._emit("closure", "Manual simulation closure applied to the requested edges.", 20)
        self.revision += 1

    def _emit(self, kind: str, message: str, seconds: int = 180) -> None:
        event = {
            "id": len(self.events) + 1,
            "at": self.clock.isoformat(),
            "kind": kind,
            "step": self.step,
            "message": message,
        }
        self.events.append(event)
        self.store.save_event(event)
        self.clock += timedelta(seconds=seconds)

    def _origin(self):
        point = self.anchors["origin"]
        return (point["lon"], point["lat"])

    def _destination(self):
        point = self.anchors["destination"]
        return (point["lon"], point["lat"])

    def _situation(self) -> None:
        self._emit(
            "situation",
            "Rescue 4 and a fictional objective are on the current OpenStreetMap graph. Nothing has been dispatched.",
        )

    def _initial_route(self) -> None:
        route = compute_route(self.graph, self._origin(), self._destination(), [])
        self.alternate = None
        if route["status"] == "ok":
            self.proposed = route
            self.active_route = route
            self.route_status = "proposed"
            self._emit(
                "route",
                f"Initial candidate route computed. Graph length {route['length_m'] / 1000:.2f} km. This is not a travel time.",
            )
            return
        self.proposed = None
        self.active_route = None
        self.route_status = "unreachable"
        self._emit("route", "No path found between Rescue 4 and the scenario objective.")

    def _imagery(self) -> None:
        self.imagery_on = True
        self._emit(
            "imagery",
            "Reference imagery selected. Release dates on the swipe are mosaic dates, not a claim of matched local capture.",
        )

    def _detection(self) -> None:
        detection = fixture_detection(self.anchors)
        self.detections = [detection] if detection.get("map_ready") else []
        self.ml_mode = "mock"
        self.ml_detail = "Damage geometry is a labeled scenario fixture. The vision model was not called."
        self._emit(
            "detection",
            "Scenario fixture placed on the segment chosen for closure. Suspected damage is not a verified closure.",
        )

    def _closure(self) -> None:
        self.closed_ids = list(self.anchors["closure_edge_ids"])
        name = self.anchors.get("closure_name") or "Selected segment"
        self._emit(
            "closure",
            f"Simulation action: {name} is marked closed. The fixture did not close it; this step applies the closure.",
        )

    def _invalidate(self) -> None:
        used = set(self.proposed["edge_ids"]) if self.proposed else set()
        if used.intersection(self.closed_ids):
            self.route_status = "invalidated"
            self.active_route = None
            self._emit("invalidate", "Candidate route withdrawn because it uses a closed segment.")
            return
        self._emit("invalidate", "The closed segment is not on the candidate route.")

    def _reroute(self) -> None:
        route = compute_route(self.graph, self._origin(), self._destination(), self.closed_ids)
        if route["status"] == "ok":
            self.active_route = route
            self.route_status = "rerouted"
            self.alternate = self._second_path(route["edge_ids"])
            self._emit(
                "reroute",
                f"Replacement path computed on the open graph. Graph length {route['length_m'] / 1000:.2f} km. It does not use the closed segment.",
            )
            return
        self.active_route = None
        self.alternate = None
        self.route_status = "unreachable"
        self._emit("reroute", ISOLATED)

    def _second_path(self, primary_ids: list):
        if not primary_ids:
            return None
        midpoint = primary_ids[len(primary_ids) // 2]
        banned = set(self.closed_ids)
        banned.add(midpoint)
        alternate = compute_route(self.graph, self._origin(), self._destination(), banned)
        if alternate["status"] != "ok":
            return None
        overlap = len(set(alternate["edge_ids"]).intersection(primary_ids)) / max(1, len(primary_ids))
        if overlap > 0.8:
            return None
        return alternate

    def _sos(self) -> None:
        self._emit("sos", "Simulated handset queued a message.", 15)
        self._emit("sos", "Simulated gateway accepted the message. This is not a radio link.", 15)
        payload = {
            **DEMO_SOS,
            "lon": self.anchors["destination"]["lon"],
            "lat": self.anchors["destination"]["lat"],
        }
        result = self.add_incident(payload)
        if result["duplicate"]:
            return
        self._emit("sos", f"Incident {result['incident']['id']} stored. Delivery status is received by this demo backend.", 30)

    def _explain(self) -> None:
        route = self.active_route or self.proposed or {}
        context = {
            "route_status": self.route_status,
            "length_m": route.get("length_m"),
            "closure_name": self.anchors.get("closure_name"),
            "message": self.incidents[-1]["message"] if self.incidents else None,
            "people_affected": self.incidents[-1]["people_affected"] if self.incidents else None,
            "closed_edge_ids": self.closed_ids,
        }
        self.explanation = explain_incident(context)
        mode = self.explanation.get("inference_mode", "mock")
        self.ml_mode = mode if mode in {"mock", "real", "unavailable"} else "unavailable"
        self.ml_detail = (
            "Local template. The language model was not called."
            if self.ml_mode == "mock"
            else "Model service returned an interpretation."
            if self.ml_mode == "real"
            else "Model service did not respond. Routing is unchanged."
        )
        self._emit("explain", "Interpretation panel updated from the current route state.")

    def _review(self) -> None:
        self.review_status = "requested"
        self._emit("review", "Operator review requested. No rescue unit is dispatched by this system.")

    def _conflicts(self) -> bool:
        route = self.active_route if self.route_status == "proposed" else None
        if not route or not self.closed_ids:
            return False
        return bool(set(route["edge_ids"]).intersection(self.closed_ids))

    def _closure_features(self) -> list:
        wanted = set(self.closed_ids)
        if not wanted:
            return []
        features = []
        for _u, _v, data in self.graph.edges(data=True):
            if data["id"] in wanted:
                features.append(
                    {
                        "id": data["id"],
                        "name": data["name"],
                        "highway": data["highway"],
                        "geometry": data["geometry"],
                        "source": "simulation",
                    }
                )
        return features

    def _public_route(self, route):
        if not route or route.get("status") != "ok":
            return None
        return {
            "length_m": route["length_m"],
            "edge_ids": route["edge_ids"],
            "edge_count": route["edge_count"],
            "geometry": route["geometry"],
            "roads": route["roads"],
            "origin_snap_m": route["origin_snap_m"],
            "destination_snap_m": route["destination_snap_m"],
        }

    def public_state(self) -> dict:
        step_id, step_label, step_title = STEPS[self.step]
        next_step = STEPS[self.step + 1][2] if self.step < len(STEPS) - 1 else None
        show_old = self.route_status in {"invalidated", "rerouted", "unreachable"}
        origin = self.anchors["origin"]
        destination = self.anchors["destination"]
        return {
            "revision": self.revision,
            "scenario": {
                "id": "helene-swannanoa",
                "name": "Hurricane Helene — Swannanoa corridor",
                "step": self.step,
                "step_count": len(STEPS),
                "step_id": step_id,
                "step_label": step_label,
                "step_title": step_title,
                "next_title": next_step,
                "mode": "simulated",
                "clock": (self.events[-1]["at"] if self.events else self.clock.isoformat()),
            },
            "steps": [
                {"id": item[0], "label": item[1], "title": item[2], "index": index}
                for index, item in enumerate(STEPS)
            ],
            "rescue_unit": {
                "id": "RSC-4",
                "name": "Rescue 4",
                "lon": origin["lon"],
                "lat": origin["lat"],
                "fictional": True,
            },
            "objective": {"lon": destination["lon"], "lat": destination["lat"], "label": "Scenario objective"},
            "incidents": self.incidents,
            "closures": self._closure_features(),
            "detections": self.detections,
            "routes": {
                "status": self.route_status,
                "conflicts": self._conflicts(),
                "active": self._public_route(self.active_route) if self.route_status in {"proposed", "rerouted"} else None,
                "invalidated": self._public_route(self.proposed) if show_old else None,
                "alternate": self._public_route(self.alternate) if self.route_status == "rerouted" else None,
            },
            "events": self.events,
            "explanation": self.explanation,
            "review": {
                "status": self.review_status,
                "note": "A person decides. This system does not dispatch a rescue unit.",
            },
            "ml": {"mode": self.ml_mode, "detail": self.ml_detail},
            "imagery": {
                "selected": self.imagery_on,
                "before": IMAGERY["before"],
                "after": IMAGERY["after"],
                "alignment_note": IMAGERY["alignment_note"],
            },
            "system": {
                "graph_nodes": self.graph.number_of_nodes(),
                "graph_edges": self.graph.number_of_edges(),
                "region": self.anchors.get("region") or "Swannanoa corridor, North Carolina",
                "graph_note": "Road graph is current OpenStreetMap, retrieved 17 October 2026. It is not a 27 September 2024 snapshot.",
                "demo_mode": demo_mode(),
                "closure_name": self.anchors.get("closure_name"),
                "disclaimer": "Simulation for a demonstration. A graph path is not a statement that a road is safe.",
            },
        }
