from fastapi.testclient import TestClient
from ml.inference.app import app
client = TestClient(app)

def test_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("ML_METRICS_PATH",str(tmp_path))
    assert client.get('/health').status_code == 200
    assert client.get('/ml/metrics').json()['baseline'] is None
    assert '/ml/predict' in client.get('/openapi.json').json()['paths']

def test_validation_and_missing_image():
    assert client.post('/ml/predict', json={'image_id':'unknown'}).status_code == 404
    for threshold in [-1, 1.1]:
        assert client.post('/ml/predict', json={'image_id':'x','threshold':threshold}).status_code == 422

def test_no_local_paths_exposed():
    assert all('path' not in row for row in client.get('/ml/images').json())

def test_incident_without_credentials(monkeypatch):
    monkeypatch.delenv('NVIDIA_API_KEY', raising=False)
    monkeypatch.setenv('LLM_PROVIDER','nvidia_api')
    assert client.post('/ml/incident/parse',json={'report':'Need water near Swannanoa'}).status_code == 503


def test_actual_metrics_are_explicit():
    result = client.get("/ml/metrics").json()
    if result["status"] == "pilot_evaluated":
        assert result["baseline"]["initialization"].startswith("pretrained backbone")
        assert result["fine_tuned"]["valid_pixels"] > 0
        assert result["limitations"]


def test_partial_vision_import_keeps_health_and_metadata_available(monkeypatch):
    import sys
    import types
    monkeypatch.setitem(sys.modules, 'ml.vision.predict', types.ModuleType('ml.vision.predict'))
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['vision_loaded'] is False
    result = client.get('/ml/model-info')
    assert result.status_code == 200
    assert result.json()['metadata_scope'] == 'configured_model_not_loaded'
