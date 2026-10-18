"""Integration tests require the genuine pinned NeMo Gym core, never a mock."""
import json
import pytest
from fastapi.testclient import TestClient
pytest.importorskip('nemo_gym.base_resources_server')
from ml.nemo_gym.app import local_app
from ml.nemo_gym.scenarios import generate,make_scenario
from ml.nemo_gym.tests.test_rescue_core import oracle_calls

@pytest.fixture
def client(tmp_path):
    generate(tmp_path)
    with TestClient(local_app(tmp_path)) as client:yield client


def response_for(calls):
    return {'id':'deterministic-test-trace','created_at':0.0,'model':'no-language-model-test-fixture','object':'response','parallel_tool_calls':False,'tool_choice':'auto','tools':[], 'output':[{'type':'function_call','id':f'fc_{i}','call_id':f'call_{i}','name':name,'arguments':json.dumps(args),'status':'completed'} for i,(name,args) in enumerate(calls)]}


def test_seed_and_tools_are_official_server_routes(client):
    assert client.post('/get_incident',json={}).status_code==409
    assert client.post('/seed_session',json={'scenario_id':make_scenario('bridge_closed',7,'train').scenario_id}).status_code==200
    assert client.post('/get_incident',json={}).json()['incident_node']=='node_6'
    status=client.post('/get_road_status',json={}).json()
    assert status['graph_version']==2
    assert any(e['status']=='closed' for e in status['edges'])
    assert client.post('/calculate_candidate_routes',json={'graph_version':1}).json()['error']=='stale_graph_version'
    assert client.post('/check_reachability',json={'graph_version':2}).json()['reachable']
    assert client.get('/reverify_mode').json()=='stateless'


def test_session_isolation(tmp_path):
    generate(tmp_path); app=local_app(tmp_path)
    with TestClient(app) as a,TestClient(app) as b:
        a.post('/seed_session',json={'scenario_id':make_scenario('bridge_closed',7,'train').scenario_id})
        b.post('/seed_session',json={'scenario_id':make_scenario('isolated',7,'train').scenario_id})
        assert a.post('/check_reachability',json={'graph_version':2}).json()['reachable']
        assert not b.post('/check_reachability',json={'graph_version':2}).json()['reachable']


def test_verify_scores_actual_official_response_schema(client):
    scenario=make_scenario('bridge_closed',7,'train');calls=oracle_calls(scenario)
    body={'scenario_id':scenario.scenario_id,'responses_create_params':{'input':[]},'response':response_for(calls)}
    result=client.post('/verify',json=body)
    assert result.status_code==200,result.text
    assert result.json()['reward']==1
    calls[-1][1]['path']=scenario.initial_route
    body['response']=response_for(calls)
    result=client.post('/verify',json=body)
    assert result.status_code==200 and result.json()['reward']==0


def test_malformed_arguments_fail_without_crashing(client):
    scenario=make_scenario('bridge_closed',7,'train')
    response=response_for(oracle_calls(scenario));response['output'][-1]['arguments']='{not json'
    result=client.post('/verify',json={'scenario_id':scenario.scenario_id,'responses_create_params':{'input':[]},'response':response})
    assert result.status_code==200,result.text
    assert result.json()['reward']==0
