"""Hero path on the real Swannanoa OSM graph (DEMO_MODE: cached parse + cached agent trace)."""
import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from app.routing import load_graph, load_anchors


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import os
    os.environ["DEMO_MODE"] = "true"
    app = create_app(load_graph(), load_anchors(), str(tmp_path_factory.mktemp("db") / "radio.db"))
    return TestClient(app)


NORTH = ["SOS-001", "SOS-002", "SOS-003", "SOS-004", "SOS-005"]


def test_beacon_report_cuts_off_families_north_of_bridge(client):
    seed = client.post("/api/radio/demo/seed").json()
    assert all(i["reachable"] for i in seed["state"]["incidents"])
    out = client.post("/api/radio", json={"message": seed["hero_message"], "source_type": "beacon",
                                          **seed["beacon_position"]}).json()
    assert out["parse"]["event_type"] == "bridge_collapse"
    assert out["assessment"]["affected_incident_ids"] == NORTH
    assert {s["status"] for s in out["statuses"].values()} == {"blocked"}
    status = client.get("/api/radio/status").json()
    assert [i["id"] for i in status["incidents"] if not i["reachable"]] == NORTH


def test_responder_report_without_position_asks_operator_then_confirms(client):
    seed = client.post("/api/radio/demo/seed").json()
    out = client.post("/api/radio", json={"message": seed["hero_message"], "unit": "Engine 4"}).json()
    assert out["assessment"]["needs_human_review"] is True
    assert out["assessment"]["affected_incident_ids"] == []
    assert client.get("/api/radio/status").json()["closed_edge_ids"] == []
    confirmed = client.post("/api/radio/confirm", json={"radio_id": out["radio_id"],
                                                        **seed["beacon_position"]}).json()
    assert confirmed["assessment"]["affected_incident_ids"] == NORTH


def test_unverified_open_report_does_not_reopen(client):
    seed = client.post("/api/radio/demo/seed").json()
    client.post("/api/radio", json={"message": seed["hero_message"], "source_type": "beacon",
                                    **seed["beacon_position"]})
    client.post("/api/radio", json={"message": seed["open_report"], "unit": "DOT"})
    assert len(client.get("/api/radio/status").json()["closed_edge_ids"]) == 2


def test_unknown_message_goes_to_review_not_guessing(client):
    client.post("/api/radio/demo/seed")
    out = client.post("/api/radio", json={"message": "something garbled about a road"}).json()
    assert out["parse"]["event_type"] == "other"
    assert out["assessment"]["needs_human_review"] is True
    assert client.get("/api/radio/status").json()["closed_edge_ids"] == []


def test_beacon_water_sensor_over_threshold_blocks_bridge(client):
    client.post("/api/radio/demo/seed")
    low = client.post("/api/beacon/beacon-ww-bridge/reading", json={"water_level_cm": 10}).json()
    assert low["over_threshold"] is False
    assert client.get("/api/radio/status").json()["closed_edge_ids"] == []
    high = client.post("/api/beacon/beacon-ww-bridge/reading", json={"water_level_cm": 45}).json()
    assert high["assessment"]["affected_incident_ids"] == NORTH
    sources = [s for st in high["statuses"].values() for s in st["sources"]]
    assert sources and all(s["type"] == "beacon_sensor" for s in sources)


def test_unknown_beacon_rejected(client):
    assert client.post("/api/beacon/nope/reading", json={"water_level_cm": 45}).status_code == 404


def test_beacon_voice_demo_recording_without_asr_server(client, monkeypatch):
    monkeypatch.delenv("ASR_BASE_URL", raising=False)
    client.post("/api/radio/demo/seed")
    out = client.post("/api/radio/audio", files={"file": ("demo_hero.wav", b"RIFF-fake", "audio/wav")},
                      data={"beacon_id": "beacon-ww-bridge"}).json()
    assert out["transcript"]["mode"] == "cached_demo_transcript"
    assert out["assessment"]["affected_incident_ids"] == NORTH


def test_audio_without_asr_and_unknown_file_is_503(client, monkeypatch):
    monkeypatch.delenv("ASR_BASE_URL", raising=False)
    response = client.post("/api/radio/audio", files={"file": ("live.wav", b"RIFF-fake", "audio/wav")})
    assert response.status_code == 503
