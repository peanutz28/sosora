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


def test_imagery_outage_records_error_but_still_blocks_bridge_safely(client):
    seed = client.post('/api/radio/demo/seed').json()
    toggled = client.post('/api/radio/demo/imagery', json={'offline': True})
    assert toggled.status_code == 200
    assert toggled.json()['state']['imagery']['offline'] is True
    out = client.post('/api/radio', json={'message': seed['hero_message'], 'source_type': 'beacon',
                                        **seed['beacon_position']}).json()
    events = out['state']['events']
    failed = next(e for e in events if e.get('tool') == 'get_imagery_evidence' and e['kind'] == 'agent_tool_result')
    assert failed['result']['error']['type'] == 'ImageryUnavailable'
    assert failed['result']['error']['recoverable'] is True
    assert 'simulated outage' in failed['result']['error']['message']
    assert out['assessment']['affected_incident_ids'] == NORTH
    assert 'imagery is unavailable' in out['assessment']['summary'].lower()
    assert out['assessment']['needs_human_review'] is True
    assert out['assessment']['confidence'] <= .5
    assert {s['status'] for s in out['statuses'].values()} == {'blocked'}
    assert [i['id'] for i in out['state']['incidents'] if not i['reachable']] == NORTH
    final = next(e for e in events if e.get('tool') == 'submit_assessment' and e['kind'] == 'agent_tool_result')
    assert final['id'] > failed['id'] and 'error' not in final['result']
    assert client.post('/api/radio/demo/imagery', json={'offline': False}).json()['state']['imagery']['offline'] is False
    restored = client.post('/api/radio', json={'message': seed['hero_message'], 'source_type': 'beacon',
                                             **seed['beacon_position']}).json()
    evidence = [e for e in restored['state']['events'] if e.get('tool') == 'get_imagery_evidence' and e['kind'] == 'agent_tool_result'][-1]
    assert evidence['result'] == []
    client.post('/api/radio/demo/imagery', json={'offline': True})
    assert client.post('/api/radio/demo/seed').json()['state']['imagery']['offline'] is False


def test_seed_exposes_new_generation_and_clears_previous_take(client):
    before = client.post('/api/radio/demo/seed').json()['state']
    after = client.post('/api/radio/demo/seed').json()['state']
    assert after['reset_generation'] == before['reset_generation'] + 1
    assert after['revision'] > before['revision']
    assert len(after['incidents']) == 9
    assert after['closures'] == []
    assert not any(e['kind'].startswith('agent_') for e in after['events'])
