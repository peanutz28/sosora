"""Model metadata is measured at the serving HTTP boundary, never inferred by the UI."""
import httpx
import pytest

from tests.test_agent import make, run


def test_runtime_uses_response_model_and_measured_last_call(monkeypatch):
    agent = make(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "requested-model-alias")
    monkeypatch.setenv("LLM_PROVIDER", "redhat_vllm")
    clock = iter([10.0, 10.854])
    monkeypatch.setattr("app.agent.perf_counter", lambda: next(clock))

    async def respond(client, url, **kwargs):
        return httpx.Response(200, json={"model": "nvidia/nemotron-3.5-lightning-30b-a3b", "choices": [{"message": {"role": "assistant"}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", respond)
    run(agent.completion([]))
    assert agent.runtime["model_id"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert agent.runtime["serving_backend"] == "vLLM"
    assert agent.runtime["cached"] is False
    assert agent.runtime["last_call_latency_ms"] == pytest.approx(854)
    run(agent.call("find_segments", {"road_name": "Test Bridge"}, "metadata-check"))
    assert agent.engine.events[-1]["agent_runtime"] == agent.runtime


def test_cached_replay_has_no_invented_model_or_latency(monkeypatch):
    agent = make(monkeypatch, demo=True)
    run(agent.run())
    assert agent.runtime == {"cached": True, "model_id": None, "serving_backend": None, "last_call_latency_ms": None}
    assert all(event["agent_runtime"] == agent.runtime for event in agent.engine.events if event["kind"].startswith("agent_"))
