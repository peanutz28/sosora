import asyncio
import json
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ml.inference import incident

app = FastAPI()
app.include_router(incident.router)
client = TestClient(app)
FACTS = dict(location_text=None, people_count=None, needs=[], hazards=[], missing_information=['location'], summary='Water reported')
BODY = dict(incident=FACTS, road_evidence=[dict(evidence_id='road-1', observation='Water overlaps road prediction', source='frame-1', confidence=0.6)])

@pytest.fixture(autouse=True)
def environment(monkeypatch):
    for name in ['LLM_PROVIDER', 'NVIDIA_API_KEY', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']:
        monkeypatch.delenv(name, raising=False)

def mock_provider(monkeypatch, output=None, failure=None, frames=None, finish='stop'):
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-only')
    original_client = httpx.AsyncClient
    def respond(request):
        assert str(request.url) == 'https://integrate.api.nvidia.com/v1/chat/completions'
        body = json.loads(request.content)
        if failure:
            raise failure
        if body.get('stream'):
            assert body['chat_template_kwargs'] == {'enable_thinking': False}
            assert body['response_format'] == {'type': 'json_object'}
            assert body['temperature'] == 1.0
            assert body['top_p'] == 0.95
            text = json.dumps(output)
            middle = len(text) // 2
            events = frames if frames is not None else [
                {'choices': []},
                {'choices': [{'delta': {'reasoning_content': 'Never an answer'}}]},
                {'choices': [{'delta': {'content': text[:middle]}}]},
                {'choices': [{'delta': {'content': text[middle:]}, 'finish_reason': finish}]},
            ]
            data = ''.join('data: '+json.dumps(event)+'\n\n' for event in events)+'data: [DONE]\n\n'
            return httpx.Response(200, text=data, headers={'Content-Type': 'text/event-stream'})
        assert 'chat_template_kwargs' not in body
        assert 'response_format' not in body
        assert body['temperature'] == 0
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(output)}}]})
    monkeypatch.setattr(incident.httpx, 'AsyncClient',
                        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))

def test_unconfigured():
    assert not incident.llm_configuration()['configured']
    assert client.post('/ml/incident/parse', json={'report':'Water'}).status_code == 503

def test_redhat_requires_explicit_base(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'redhat_vllm')
    monkeypatch.setenv('LLM_API_KEY', 'test-only')
    assert not incident.llm_configuration()['configured']
    monkeypatch.setenv('LLM_BASE_URL', 'http://localhost:8000/v1')
    assert incident.llm_configuration()['configured']
    assert 'test-only' not in json.dumps(incident.llm_configuration())

@pytest.mark.parametrize('base', ['ftp://host', 'https://user:password@host/v1', 'https://host/v1?key=secret'])
def test_unsafe_base(monkeypatch, base):
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-only')
    monkeypatch.setenv('LLM_BASE_URL', base)
    assert not incident.llm_configuration()['configured']

def test_parse_success(monkeypatch):
    mock_provider(monkeypatch, FACTS)
    response = client.post('/ml/incident/parse', json={'report':'Water reported'})
    assert response.status_code == 200
    assert response.json()['incident'] == FACTS
    assert response.json()['inference_mode'] == 'real'

def test_explain_success(monkeypatch):
    output = dict(explanation='Water overlap requires review.', evidence_ids=['road-1'], uncertainty=['Prediction is unverified.'], review_status='unverified')
    mock_provider(monkeypatch, output)
    response = client.post('/ml/incident/explain', json=BODY)
    assert response.status_code == 200
    assert response.json()['explanation'] == output

@pytest.mark.parametrize('output', [{}, {'summary':7}, None])
def test_malformed_provider(monkeypatch, output):
    mock_provider(monkeypatch, output)
    assert client.post('/ml/incident/parse', json={'report':'Water'}).status_code == 502

def test_timeout(monkeypatch):
    mock_provider(monkeypatch, failure=httpx.ReadTimeout('timeout'))
    assert client.post('/ml/incident/parse', json={'report':'Water'}).status_code == 502

@pytest.mark.parametrize('finish', ['length', None])
def test_truncated_stream_rejected_even_with_valid_json(monkeypatch, finish):
    mock_provider(monkeypatch, FACTS, finish=finish)
    assert client.post('/ml/incident/parse', json={'report': 'Water'}).status_code == 502

def test_reasoning_is_not_used_as_output(monkeypatch):
    frames = [{'choices': [{'delta': {'reasoning_content': json.dumps(FACTS)}, 'finish_reason': 'stop'}]}]
    mock_provider(monkeypatch, frames=frames)
    assert client.post('/ml/incident/parse', json={'report': 'Water'}).status_code == 502

def test_stream_error_is_sanitized(monkeypatch):
    mock_provider(monkeypatch, frames=[{'error': {'message': 'private provider detail'}}])
    response = client.post('/ml/incident/parse', json={'report': 'Water'})
    assert response.status_code == 502
    assert 'private provider detail' not in response.text

def test_total_deadline_bounds_a_stalled_stream(monkeypatch):
    original_client = httpx.AsyncClient
    class StalledStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"choices": []}\n\n'
            await asyncio.sleep(1)
            yield b'data: [DONE]\n\n'
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-only')
    monkeypatch.setattr(incident, '_PROVIDER_TIMEOUT_SECONDS', 0.01)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=StalledStream()))
    monkeypatch.setattr(incident.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=transport, **kwargs))
    assert client.post('/ml/incident/parse', json={'report': 'Water'}).status_code == 502

def test_completed_answer_does_not_wait_for_stream_connection_to_close(monkeypatch):
    original_client = httpx.AsyncClient
    class CompletedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            event = {'choices': [{'delta': {'content': json.dumps(FACTS)}, 'finish_reason': 'stop'}]}
            yield ('data: '+json.dumps(event)+'\n\n').encode()
            await asyncio.sleep(1)
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-only')
    monkeypatch.setattr(incident, '_PROVIDER_TIMEOUT_SECONDS', 0.05)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=CompletedStream()))
    monkeypatch.setattr(incident.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=transport, **kwargs))
    response = client.post('/ml/incident/parse', json={'report': 'Water'})
    assert response.status_code == 200
    assert response.json()['incident'] == FACTS

def test_redhat_keeps_nonstreaming_protocol(monkeypatch):
    mock_provider(monkeypatch, FACTS)
    monkeypatch.setenv('LLM_PROVIDER', 'redhat_vllm')
    monkeypatch.setenv('LLM_API_KEY', 'test-only')
    monkeypatch.setenv('LLM_BASE_URL', 'https://integrate.api.nvidia.com/v1')
    response = client.post('/ml/incident/parse', json={'report': 'Water'})
    assert response.status_code == 200
    assert response.json()['provider'] == 'redhat_vllm'

def test_unknown_citation(monkeypatch):
    mock_provider(monkeypatch, dict(explanation='Review', evidence_ids=['invented'], uncertainty=['Unknown'], review_status='unverified'))
    assert client.post('/ml/incident/explain', json=BODY).status_code == 502

def test_strict_evidence():
    body = {**BODY, 'road_evidence':[dict(BODY['road_evidence'][0], confidence='0.6')]}
    assert client.post('/ml/incident/explain', json=body).status_code == 422
    assert client.post('/ml/incident/explain', json={**BODY, 'road_evidence':BODY['road_evidence']*2}).status_code == 422
