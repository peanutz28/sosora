from fastapi.testclient import TestClient
from app.factory import create_app
from tests.support import graph, anchors


def test_local_cors_default_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv('APP_CORS_ORIGINS', raising=False)
    api = TestClient(create_app(graph(), anchors(), str(tmp_path/'local.db')))
    response = api.options('/api/radio/demo/seed', headers={
        'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST'})
    assert response.headers['access-control-allow-origin'] == '*'


def test_hosted_cors_allows_only_configured_origins(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_CORS_ORIGINS',' https://demo.example/ , https://preview.example ')
    api = TestClient(create_app(graph(), anchors(), str(tmp_path/'hosted.db')))
    for origin in ['https://demo.example','https://preview.example']:
        response = api.options('/api/radio/demo/seed', headers={
            'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == origin
    denied = api.options('/api/radio/demo/seed', headers={
        'Origin':'https://unrelated.example','Access-Control-Request-Method':'POST'})
    assert denied.status_code == 400
    assert 'access-control-allow-origin' not in denied.headers
