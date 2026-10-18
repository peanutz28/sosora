from types import SimpleNamespace
from threading import Lock

import pytest
from fastapi.testclient import TestClient
from beacon.asr_server import app


@pytest.fixture
def client():
    class Recognizer:
        def transcribe(self, stream, **kwargs):
            assert stream.read() == b'actual audio'
            assert kwargs['language'] == 'en'
            assert 'initial_prompt' not in kwargs
            return iter([SimpleNamespace(text=' Road flooded.'), SimpleNamespace(text=' Avoid the bridge.')]), None
    app.state.recognizer = Recognizer()
    app.state.recognition_lock = Lock()
    return TestClient(app)  # No lifespan/model download in unit tests.


def test_recognizes_audio_even_with_demo_filename(client):
    response = client.post('/audio/transcriptions', data={'model': 'tiny.en'},
                           files={'file': ('demo_hero.wav', b'actual audio', 'audio/wav')})
    assert response.status_code == 200
    assert response.json() == {'text': 'Road flooded. Avoid the bridge.', 'model': 'tiny.en', 'mode': 'live'}


@pytest.mark.parametrize('payload', [b'', b'bad audio'])
def test_invalid_audio_is_rejected(client, payload):
    response = client.post('/audio/transcriptions', files={'file': ('voice.wav', payload)})
    assert response.status_code == 422


def test_rejects_other_models(client):
    response = client.post('/audio/transcriptions', data={'model': 'large'},
                           files={'file': ('voice.wav', b'actual audio')})
    assert response.status_code == 422


def test_empty_transcript_rejected(client):
    app.state.recognizer = SimpleNamespace(transcribe=lambda *a, **kw: (iter([]), None))
    assert client.post('/audio/transcriptions', files={'file': ('voice.wav', b'actual audio')}).status_code == 422
