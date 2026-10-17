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

def mock_provider(monkeypatch, output=None, failure=None):
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-only')
    class Provider:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            assert url == 'https://integrate.api.nvidia.com/v1/chat/completions'
            assert kwargs['json']['temperature'] == 0
            if failure: raise failure
            return httpx.Response(200, request=httpx.Request('POST', url), json={'choices':[{'message':{'content':json.dumps(output)}}]})
    monkeypatch.setattr(incident.httpx, 'AsyncClient', Provider)

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

def test_unknown_citation(monkeypatch):
    mock_provider(monkeypatch, dict(explanation='Review', evidence_ids=['invented'], uncertainty=['Unknown'], review_status='unverified'))
    assert client.post('/ml/incident/explain', json=BODY).status_code == 502

def test_strict_evidence():
    body = {**BODY, 'road_evidence':[dict(BODY['road_evidence'][0], confidence='0.6')]}
    assert client.post('/ml/incident/explain', json=body).status_code == 422
    assert client.post('/ml/incident/explain', json={**BODY, 'road_evidence':BODY['road_evidence']*2}).status_code == 422
