import copy
import json
import pytest
from ml.nemo_gym.core import route,score,tool_result,expected_status,REQUESTS
from ml.nemo_gym.scenarios import FAMILIES,make_scenario,generate


def oracle_calls(scenario):
    status=expected_status(scenario)
    calls=[('get_incident',{})]
    if status!='needs_location':calls.append(('get_road_status',{}))
    if scenario.damage_evidence:calls.append(('get_damage_evidence',{}))
    if status in {'reachable','unreachable'}:
        calls += [('calculate_candidate_routes',{'graph_version':2}),('check_reachability',{'graph_version':2})]
    calls.append(('submit_recommendation',{'status':status,'graph_version':None if status=='needs_location' or 'get_road_status' in scenario.failed_tools else 2,'path':route(scenario) if status=='reachable' else [],'requires_human_review':True,'review_status':'unverified','reason':'Synthetic graph planning; requires field verification.'}))
    return calls

@pytest.mark.parametrize('family',FAMILIES)
def test_oracle_verifier_contract(family):
    scenario=make_scenario(family,7,'train')
    assert score(scenario,oracle_calls(scenario))['reward']==1


def test_closed_edge_path_rejected_even_if_status_correct():
    scenario=make_scenario('bridge_closed',7,'train')
    calls=oracle_calls(scenario)
    calls[-1][1]['path']=scenario.initial_route
    result=score(scenario,calls)
    assert result['reward']==0 and 'invalid_or_closed_edge_path' in result['issues']


def test_no_tool_submission_cannot_receive_credit():
    scenario=make_scenario('isolated',7,'train')
    assert score(scenario,oracle_calls(scenario)[-1:])['reward']==0

@pytest.mark.parametrize('args',[None,[],{'graph_version':True},{'graph_version':'2'},{'graph_version':1}])
def test_invalid_or_stale_graph_version_fails(args):
    scenario=make_scenario('bridge_closed',7,'train'); calls=oracle_calls(scenario)
    calls[2]=('calculate_candidate_routes',args)
    assert score(scenario,calls)['reward']==0


def test_current_status_must_precede_routing():
    scenario=make_scenario('bridge_closed',7,'train');calls=oracle_calls(scenario)
    calls[1],calls[2]=calls[2],calls[1]
    assert 'route_tool_before_current_status' in score(scenario,calls)['issues']


def test_conflicting_evidence_requires_review_and_retrieval():
    scenario=make_scenario('conflicting_evidence',7,'train');calls=oracle_calls(scenario)
    calls[-1][1]['requires_human_review']=False
    assert 'missing_human_review' in score(scenario,calls)['issues']
    calls=oracle_calls(scenario);calls=[c for c in calls if c[0]!='get_damage_evidence']
    assert score(scenario,calls)['reward']==0


def test_failure_is_unknown_not_unreachable():
    scenario=make_scenario('tool_failure',7,'train')
    assert not tool_result(scenario,'get_road_status',{})['available']
    calls=oracle_calls(scenario);calls[-1][1]['status']='unreachable'
    assert score(scenario,calls)['reward']==0


def test_repeated_or_nonfinal_submission_rejected():
    scenario=make_scenario('bridge_closed',7,'train');calls=oracle_calls(scenario)
    assert score(scenario,calls+[calls[-1]])['reward']==0
    assert score(scenario,calls+[('get_incident',{})])['reward']==0


def test_data_reproducible_and_disjoint(tmp_path):
    generate(tmp_path/'a');generate(tmp_path/'b')
    a=json.loads((tmp_path/'a/methodology.json').read_text())
    b=json.loads((tmp_path/'b/methodology.json').read_text())
    assert a==b
    sets=[]
    for split in ['train','validation','test']:
        rows=[json.loads(line) for line in (tmp_path/'a'/f'{split}.jsonl').read_text().splitlines()]
        sets.append({row['scenario_id'] for row in rows})
        for row in rows:
            assert 'scenario' not in row['responses_create_params']
            assert len(row['responses_create_params']['tools'])==6
    assert not sets[0]&sets[1] and not sets[0]&sets[2] and not sets[1]&sets[2]
