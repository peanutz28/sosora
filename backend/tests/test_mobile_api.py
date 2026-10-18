from fastapi.testclient import TestClient
from app.factory import create_app
from tests.support import graph, anchors


def test_phone_sos_broadcast_and_status(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    api = TestClient(create_app(graph(), anchors(), str(tmp_path / 'mobile.db')))
    body = dict(client_id='phone-1', message='Help at home', people=3,
                place='Main Street', lat=35.60, lng=-82.38)
    assert api.get('/api/health').json()['ok'] is True
    with api.websocket_connect('/ws/events') as ws:
        ws.receive_json()
        response = api.post('/api/incidents', json=body)
        assert response.status_code == 200
        incident = response.json()
        assert incident['people'] == 3 and incident['lng'] == body['lng']
        assert incident['status'] == 'Received'
        pin = ws.receive_json()['state']['incidents'][0]
        assert (pin['lon'], pin['lat']) == (body['lng'], body['lat'])
        assert pin['client_id'] == 'phone-1'
    assert api.post('/api/incidents', json=body).json()['duplicate'] is True
    assert len(api.get('/api/state').json()['incidents']) == 1
    updated = api.patch('/api/incidents/' + incident['id'], json={'status': 'Resolved'})
    assert updated.json()['status'] == 'Resolved'
    mobile = api.get('/api/mobile/state').json()
    assert isinstance(mobile['stage'], int)
    assert mobile['incidents'][0]['place'] == 'Main Street'
    assert mobile['incidents'][0]['status'] == 'Resolved'
    assert api.patch('/api/incidents/missing', json={'status': 'Received'}).status_code == 404
    assert api.patch('/api/incidents/' + incident['id'], json={'status': 'bad'}).status_code == 422
    assert api.post('/api/incidents', json={**body, 'lat': 100}).status_code == 422


def test_catalog_and_selected_road_agent(tmp_path, monkeypatch):
    monkeypatch.setenv('DEMO_MODE', 'true')
    api = TestClient(create_app(graph(), anchors(), str(tmp_path / 'mobile.db')))
    catalog = api.get('/api/road-segments').json()['segments']
    assert {s['id'] for s in catalog} == {'ab', 'bc', 'ae', 'ec'}
    assert all(isinstance(s['lng'], float) and isinstance(s['lat'], float) for s in catalog)
    body = dict(segment_id='ae', condition='blocked', source='official', verification='verified', evidence='Tree down')
    result = api.post('/api/road-reports', json=body)
    assert result.status_code == 200
    out = result.json()
    assert api.app.state.engine.closed_ids == ['ae']  # Ridge Road has another segment; no ambiguity.
    source = out['statuses']['ae']['sources'][0]
    assert source['type'] == 'responder_radio' and source['verified'] is False
    assert any(e.get('kind') == 'agent_tool_call' for e in out['state']['events'])
    opened = api.post('/api/road-reports', json={**body, 'condition': 'passable'}).json()
    assert opened['statuses']['ae']['status'] == 'contested'
    assert api.app.state.engine.closed_ids == ['ae']
    assert api.post('/api/road-reports', json={**body, 'segment_id': 'missing'}).status_code == 404
    assert api.post('/api/road-reports', json={**body, 'condition': 'bad'}).status_code == 422
    unknown = api.post('/api/road-reports', json={**body, 'segment_id': 'ec', 'condition': 'unknown'}).json()
    assert api.app.state.engine.closed_ids == ['ae']


def test_selected_road_closes_both_directions_in_live_mode(tmp_path, monkeypatch):
    monkeypatch.setenv('DEMO_MODE', 'false')
    network = graph()
    for _, _, data in network.edges(data=True):
        if data['id'] == 'bc':
            data['id'] = 'bc:f'
    from tests.support import B, C, edge
    from app.routing import build_graph
    reverse = build_graph([edge('bc:b', C, B, 900, 'Test Bridge', bridge=True)])
    network.add_edges_from(reverse.edges(data=True))
    api = TestClient(create_app(network, anchors(), str(tmp_path / 'directions.db')))
    response = api.post('/api/road-reports', json={'segment_id': 'bc:f', 'condition': 'blocked'})
    assert response.status_code == 200
    assert set(api.app.state.engine.closed_ids) == {'bc:f', 'bc:b'}
    assert response.json()['assessment']['needs_human_review'] is False
