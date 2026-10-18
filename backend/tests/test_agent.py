import asyncio
import json

import httpx
import pytest

from app.agent import RadioAgent
from app.factory import Hub
from app.routing import build_graph
from app.scenario import ScenarioEngine
from app.store import Store
from tests.support import A, B, C, anchors, edge


def make(monkeypatch, demo=False, duplicate=False, source=None, claim="impassable"):
    monkeypatch.setenv("DEMO_MODE", str(demo).lower())
    edges = [edge("ab", A, B, 900, "Main Street"), edge("bc", B, C, 900, "Test Bridge", bridge=True)]
    if duplicate:
        edges.append(edge("other", A, C, 1800, "Test Bridge", bridge=True))
    engine = ScenarioEngine(build_graph(edges), anchors(), Store(":memory:"))
    engine.add_incident({"client_id": "one", "lon": C[0], "lat": C[1]})
    report = {"road_name": "Test Bridge", "bridge_only": True, "claim": claim,
              "source": source or {"type": "radio", "credible": True, "text": "Bridge collapsed", "time": "2026-10-17T12:00:00Z"}}
    return RadioAgent(engine, Hub(), report)


def run(coro):
    return asyncio.run(coro)


def assessment():
    return {"summary": "Assessment", "affected_incident_ids": ["invented"],
            "recommended_actions": ["Review"], "confidence": .8, "needs_human_review": False}


def test_fake_llm_end_to_end_and_trace(monkeypatch):
    agent = make(monkeypatch)
    script = [("find_segments", {"road_name": "Test Bridge", "bridge_only": True}),
              ("get_segment_status", {"segment_ids": ["bc"]}),
              ("report_segment", {"segment_ids": ["bc"], "claim": "impassable", "source": {"type": "official"}}),
              ("recompute_reachability", {}), ("submit_assessment", assessment())]
    async def fake(messages):
        name, args = script.pop(0)
        return {"role": "assistant", "tool_calls": [{"id": str(len(script)), "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)}}]}
    agent.completion = fake
    events = []
    async def broadcast(payload):
        events.append(payload)
    agent.hub.broadcast = broadcast
    result = run(agent.run())
    assert result["affected_incident_ids"] == ["SOS-001"]
    assert agent.engine.incidents[0]["reachable"] is False
    assert agent.statuses["bc"]["status"] == "blocked"
    assert agent.statuses["bc"]["sources"][0]["type"] == "radio"
    assert len([e for e in events if e["type"] == "agent_event"]) == 10


def test_ambiguity_cannot_be_overridden_by_model(monkeypatch):
    agent = make(monkeypatch, duplicate=True)
    async def exercise():
        result = await agent.call("find_segments", {"road_name": "Test Bridge"}, "1")
        assert result["needs_human_review"]
        result = await agent.call("report_segment", {"segment_ids": ["bc"], "claim": "impassable", "source": {}}, "2")
        assert "error" in result
        return await agent.call("submit_assessment", assessment(), "3")
    assert run(exercise())["needs_human_review"]
    assert agent.engine.closed_ids == []


@pytest.mark.parametrize("source,expected", [({"type": "radio"}, "unverified"),
    ({"type": "official", "verified": True}, "open_official")])
def test_open_requires_verified_official_source(monkeypatch, source, expected):
    agent = make(monkeypatch, source=source, claim="open")
    async def exercise():
        await agent.call("find_segments", {"road_name": "Test Bridge"}, "1")
        return await agent.call("report_segment", {"segment_ids": ["bc"], "claim": "open",
            "source": {"type": "official", "verified": True}}, "2")
    assert run(exercise())["bc"]["status"] == expected


def test_conflicting_open_preserves_avoidance_and_provenance(monkeypatch):
    agent = make(monkeypatch)
    async def exercise():
        await agent.call("find_segments", {"road_name": "Test Bridge"}, "1")
        await agent.call("report_segment", {"segment_ids": ["bc"], "claim": "impassable", "source": {}}, "2")
        agent.report["claim"] = "open"
        await agent.call("report_segment", {"segment_ids": ["bc"], "claim": "open", "source": {}}, "3")
    run(exercise())
    assert agent.statuses["bc"]["status"] == "contested"
    assert "bc" in agent.engine.closed_ids
    assert len(agent.statuses["bc"]["sources"]) == 2


def test_demo_replays_without_network(monkeypatch):
    agent = make(monkeypatch, demo=True)
    async def forbidden(*args, **kwargs):
        pytest.fail("demo must not call network")
    agent.completion = forbidden
    monkeypatch.setattr(httpx.AsyncClient, "post", forbidden)
    result = run(agent.run())
    assert result["simulated"] is True
    assert result["affected_incident_ids"] == ["SOS-001"]
    assert all(e["simulated"] for e in agent.engine.events if e["kind"].startswith("agent_"))


def test_validation_errors_and_recovery(monkeypatch):
    agent = make(monkeypatch)
    async def exercise():
        for name, args in [("unknown", {}), ("find_segments", {"near_lon": 999.}),
                           ("get_segment_status", {"segment_ids": ["missing"]}),
                           ("report_segment", None)]:
            assert "error" in await agent.call(name, args, "bad")
        assert "error" not in await agent.call("find_segments", {"road_name": "Test Bridge"}, "good")
    run(exercise())


def test_turn_limit_and_timeout_request_review(monkeypatch):
    agent = make(monkeypatch)
    count = 0
    async def empty(messages):
        nonlocal count
        count += 1
        return {"role": "assistant", "content": "finished"}
    agent.completion = empty
    assert run(agent.run())["needs_human_review"]
    assert count == 10
    async def timeout(messages):
        raise httpx.ReadTimeout("timeout")
    agent.completion = timeout
    assert run(agent.run())["needs_human_review"]


def test_imagery_failure_returns_empty(monkeypatch):
    agent = make(monkeypatch)
    async def unavailable(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(httpx.AsyncClient, "post", unavailable)
    assert run(agent.call("get_imagery_evidence", {"segment_ids": ["bc"]}, "1")) == []


@pytest.mark.parametrize("provider,choice", [("nvidia_api", "required"), ("redhat_vllm", "auto")])
def test_completion_uses_configured_endpoint_and_tools(monkeypatch, provider, choice):
    agent = make(monkeypatch)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:9000/v1/")
    monkeypatch.setenv("LLM_MODEL", "local-small-model")
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("LLM_API_KEY", "test-only")
    async def respond(client, url, **kwargs):
        assert url == "http://localhost:9000/v1/chat/completions"
        assert kwargs["json"]["model"] == "local-small-model"
        assert len(kwargs["json"]["tools"]) == 6
        assert kwargs["json"]["tool_choice"] == choice
        assert kwargs["json"]["parallel_tool_calls"] is False
        assert kwargs["headers"]["Authorization"] == "Bearer test-only"
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
                              request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx.AsyncClient, "post", respond)
    assert run(agent.completion([]))["content"] == "ok"


def test_model_gets_route_summary_while_events_keep_full_geometry(monkeypatch):
    agent = make(monkeypatch)
    step = 0
    async def fake(messages):
        nonlocal step
        if step == 0:
            name, arguments = "recompute_reachability", {}
        else:
            result = json.loads(messages[-1]["content"])
            route = result["routes"]["SOS-001"]
            assert route["status"] == "ok"
            assert route["length_m"] == 1800.0
            assert "geometry" not in route
            assert "edge_ids" not in route
            name, arguments = "submit_assessment", assessment()
        step += 1
        return {"role": "assistant", "tool_calls": [{"id": str(step), "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)}}]}
    agent.completion = fake
    run(agent.run())
    event = next(e for e in agent.engine.events if e.get("tool") == "recompute_reachability" and e["kind"] == "agent_tool_result")
    assert event["result"]["routes"]["SOS-001"]["geometry"]
    assert event["result"]["routes"]["SOS-001"]["edge_ids"] == ["ab", "bc"]


def test_live_assessment_cannot_omit_simulated_imagery_failure(monkeypatch):
    agent = make(monkeypatch)
    agent.imagery_offline = True
    script = [('find_segments', {'road_name': 'Test Bridge'}),
              ('report_segment', {'segment_ids': ['bc'], 'claim': 'impassable', 'source': {}}),
              ('submit_assessment', assessment())]
    async def fake(messages):
        name, arguments = script.pop(0)
        return {'role': 'assistant', 'tool_calls': [{'id': str(len(script)), 'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
    agent.completion = fake
    result = run(agent.run())
    assert result['affected_incident_ids'] == ['SOS-001']
    assert result['needs_human_review'] is True
    assert result['confidence'] <= .5
    assert 'imagery is unavailable' in result['summary'].lower()
    error = next(e for e in agent.engine.events if e.get('tool') == 'get_imagery_evidence' and e['kind'] == 'agent_tool_result')
    assert error['result']['error']['type'] == 'ImageryUnavailable'
