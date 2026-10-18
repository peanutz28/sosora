"""Radio examples are simulated; provider tests never use the network."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from ml.inference.app import app
from ml.inference import incident, radio

client = TestClient(app)


def body(message):
    return dict(message=message, received_at='2026-10-17T12:00:00Z', channel='radio')


@pytest.mark.parametrize('fixture', radio.DEMO_FIXTURES)
def test_simulated_cache_without_provider(monkeypatch, fixture):
    monkeypatch.setenv('DEMO_MODE', 'true')
    async def forbidden(*args, **kwargs):
        pytest.fail('Demo must not use provider')
    monkeypatch.setattr(incident, '_infer', forbidden)
    response = client.post('/ml/radio/parse', json=body(fixture['message']))
    assert response.status_code == 200
    result = response.json()
    assert 'SIMULATED' in result['raw']
    assert result == {**{k: v for k, v in fixture.items() if k != 'message'},
                      'raw': fixture['message'], 'needs_review': True}


def test_unknown_demo_is_conservative(monkeypatch):
    monkeypatch.setenv('DEMO_MODE', 'true')
    response = client.post('/ml/radio/parse', json=body('unknown bridge... static'))
    assert response.status_code == 200
    assert response.json()['event_type'] == 'other'
    assert response.json()['road_name'] is None
    assert response.json()['needs_review'] is True


@pytest.mark.parametrize('patch', [dict(message=''), dict(received_at='yesterday'),
                                    dict(channel='email'), dict(message=42)])
def test_invalid_request(patch):
    assert client.post('/ml/radio/parse', json={**body('static'), **patch}).status_code == 422


def provider(monkeypatch, output, finish='stop'):
    monkeypatch.setenv('DEMO_MODE', 'false')
    monkeypatch.setenv('LLM_PROVIDER', 'nvidia_api')
    monkeypatch.setenv('NVIDIA_API_KEY', 'test-only')
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_MODEL', raising=False)
    original = httpx.AsyncClient
    def respond(request):
        payload = json.loads(request.content)
        assert payload['stream'] is True
        assert payload['response_format'] == {'type': 'json_object'}
        event = {'choices': [{'delta': {'content': json.dumps(output)}, 'finish_reason': finish}]}
        return httpx.Response(200, text='data: ' + json.dumps(event) + '\n\ndata: [DONE]\n\n')
    monkeypatch.setattr(incident.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))


def output():
    return dict(event_type='road_open', road_name='Bee Tree Road', road_ref='NC 999',
                landmark='Imaginary bridge', location_text='Bee Tree Road', people_count=None,
                urgency='low', needs_review=False, raw='invented')


def test_streaming_and_grounding(monkeypatch):
    provider(monkeypatch, output())
    message = 'bee tree road reportedly open... unconfirmed'
    response = client.post('/ml/radio/parse', json=body(message))
    assert response.status_code == 200
    result = response.json()
    assert result['road_name'] == 'Bee Tree Road'
    assert result['road_ref'] is None and result['landmark'] is None
    assert result['needs_review'] is True and result['raw'] == message
    assert result['event_type'] == 'road_open'


def test_invented_road_name_removed(monkeypatch):
    provider(monkeypatch, output())
    assert client.post('/ml/radio/parse', json=body('bridge down, location unreadable')).json()['road_name'] is None


@pytest.mark.parametrize('changes', [dict(people_count=-1), dict(people_count='4'),
                                    dict(event_type='safe'), dict(extra='bad')])
def test_invalid_provider_schema(monkeypatch, changes):
    provider(monkeypatch, {**output(), **changes})
    assert client.post('/ml/radio/parse', json=body('static')).status_code == 502


def test_truncated_provider(monkeypatch):
    provider(monkeypatch, output(), finish='length')
    assert client.post('/ml/radio/parse', json=body('static')).status_code == 502
