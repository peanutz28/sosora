from fastapi.testclient import TestClient

from app.factory import create_app
from tests.support import anchors, graph


def client(tmp_path):
    app = create_app(graph(), anchors(), str(tmp_path / "sosora.db"))
    return TestClient(app)


def test_sos_is_idempotent(tmp_path):
    api = client(tmp_path)
    body = {
        "client_id": "sos-1",
        "source_id": "handset",
        "lon": -82.38,
        "lat": 35.60,
        "message": "Need help",
        "people_affected": 2,
        "medical": "Difficulty breathing",
    }
    first = api.post("/api/incidents", json=body)
    second = api.post("/api/incidents", json=body)
    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert len(second.json()["state"]["incidents"]) == 1
    assert api.app.state.engine.store.counts()["incidents"] == 1


def test_scenario_replay_and_reset(tmp_path):
    api = client(tmp_path)
    for _ in range(9):
        advanced = api.post("/api/scenarios/advance")
        assert advanced.status_code == 200
    state = advanced.json()
    assert state["scenario"]["step"] == 9
    assert state["routes"]["status"] == "rerouted"
    assert "bc" not in state["routes"]["active"]["edge_ids"]
    assert "bc" in state["routes"]["invalidated"]["edge_ids"]
    assert state["incidents"][0]["id"] == "SOS-001"
    assert state["review"]["status"] == "requested"
    assert state["explanation"]["inference_mode"] == "mock"
    assert state["detections"][0]["inference_mode"] == "mock"
    assert state["detections"][0]["map_ready"] is True

    again = client(tmp_path)
    for _ in range(9):
        again.post("/api/scenarios/advance")
    repeat = again.get("/api/state").json()
    assert [event["message"] for event in repeat["events"]] == [event["message"] for event in state["events"]]
    assert repeat["routes"]["active"]["edge_ids"] == state["routes"]["active"]["edge_ids"]

    reset = api.post("/api/scenarios/reset")
    cleared = reset.json()
    assert cleared["scenario"]["step"] == 0
    assert cleared["incidents"] == []
    assert cleared["routes"]["status"] == "none"
    assert cleared["routes"]["active"] is None


def test_health_and_ml_failure_do_not_break_routing(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    api = client(tmp_path)
    status = api.get("/api/ml/status")
    assert status.status_code == 200
    assert status.json()["mode"] == "unavailable"
    route = api.post("/api/routes/calculate", json={"origin": [-82.40, 35.60], "destination": [-82.38, 35.60]})
    assert route.json()["route"]["status"] == "ok"
    assert api.get("/health").json()["status"] == "ok"
