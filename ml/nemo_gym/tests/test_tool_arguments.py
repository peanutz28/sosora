import json
import sys
import pytest
from ml.nemo_gym.tool_arguments import ADAPTER, adapt_arguments
from ml.nemo_gym.core import Recommendation, GraphRequest, score
from ml.nemo_gym.scenarios import make_scenario, tools


@pytest.mark.parametrize('spelling', ['None', 'null'])
def test_only_nullable_non_string_field_is_decoded(spelling):
    raw=json.dumps({'graph_version':spelling,'reason':'None','path':[]})
    effective,edits=adapt_arguments(raw,Recommendation.model_json_schema())
    assert json.loads(effective)=={'graph_version':None,'reason':'None','path':[]}
    assert edits==[{'field':'graph_version','before':spelling,'after':None}]
    assert json.loads(raw)['graph_version']==spelling


@pytest.mark.parametrize('value', [None,2,0,False,'2','NULL',' None ','unknown',''])
def test_other_values_are_never_repaired(value):
    raw=json.dumps({'graph_version':value})
    assert adapt_arguments(raw,Recommendation.model_json_schema())==(raw,[])


@pytest.mark.parametrize('raw', ['{broken','[]','null','2'])
def test_malformed_or_non_object_arguments_pass_through(raw):
    assert adapt_arguments(raw,Recommendation.model_json_schema())==(raw,[])


def test_missing_required_field_nonnullable_and_string_union_stay_invalid_or_literal():
    assert adapt_arguments('{}',Recommendation.model_json_schema())==('{}',[])
    raw='{"graph_version":"None"}'
    assert adapt_arguments(raw,GraphRequest.model_json_schema())==(raw,[])
    schema={'properties':{'graph_version':{'anyOf':[{'type':'string'},{'type':'null'}]}}}
    assert adapt_arguments(raw,schema)==(raw,[])


def test_adapter_cannot_invent_reachability_or_bypass_review():
    scenario=make_scenario('missing_location',17,'validation')
    raw=json.dumps({'status':'reachable','graph_version':'None','path':['node_0','node_16'],'requires_human_review':False,'review_status':'unverified','reason':'Bad model decision.'})
    effective,_=adapt_arguments(raw,Recommendation.model_json_schema())
    result=score(scenario,[('get_incident',{}),('submit_recommendation',json.loads(effective))])
    assert result['reward']==0
    assert {'incorrect_reachability','unsupported_path','missing_human_review'} <= set(result['issues'])


@pytest.mark.parametrize('family',['tool_failure','missing_location'])
@pytest.mark.parametrize('adapter',['none',ADAPTER])
def test_fake_provider_fresh_cases_real_runner_tools_and_verifier(monkeypatch,tmp_path,family,adapter):
    from ml.nemo_gym import evaluate_agent
    from ml.nemo_gym.app import local_app
    # Fresh topology size; deterministic fault-injection fixtures, not model eval.
    scenario=make_scenario(family,17,'validation')
    data=tmp_path/'data';data.mkdir()
    row={'scenario_id':scenario.scenario_id,'scenario':scenario.model_dump(),'responses_create_params':{'input':[{'role':'user','content':'Assess this SIMULATED incident.'}],'tools':tools()}}
    (data/'validation.jsonl').write_text(json.dumps(row)+'\n')
    monkeypatch.setattr(evaluate_agent,'__file__',str(tmp_path/'evaluate_agent.py'))
    monkeypatch.setattr(evaluate_agent,'local_app',lambda:local_app(data))
    monkeypatch.setenv('LLM_PROVIDER','nvidia_api');monkeypatch.setenv('NVIDIA_API_KEY','fake-only')
    monkeypatch.delenv('LLM_BASE_URL',raising=False)
    calls=[('get_incident',{})]
    if family=='tool_failure':calls.append(('get_road_status',{}))
    calls += [('get_damage_evidence',{}),('submit_recommendation',{'status':'unknown' if family=='tool_failure' else 'needs_location','graph_version':'None','path':[],'requires_human_review':True,'review_status':'unverified','reason':'SIMULATED unavailable information requires review.'})]
    class Provider:
        index=0
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            name,args=calls[self.index];self.index+=1
            payload={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':[{'id':str(self.index),'type':'function','function':{'name':name,'arguments':__import__('json').dumps(args)}}]}}]}
            class Response:
                def raise_for_status(self):pass
                def json(self):return payload
            return Response()
    monkeypatch.setattr(evaluate_agent.httpx,'Client',Provider)
    out=tmp_path/'results'
    monkeypatch.setattr(sys,'argv',['evaluate_agent','--policy','baseline','--limit','1','--output',str(out),'--argument-adapter',adapter])
    evaluate_agent.main()
    result=json.loads((out/'rollouts.jsonl').read_text())
    assert result['reward']==(1 if adapter==ADAPTER else 0)
    if adapter==ADAPTER:
        metrics=json.loads((out/'metrics.json').read_text())
        assert metrics['argument_adapter']==ADAPTER
        assert metrics['experiment_kind']=='system compatibility adapter; not prompt-only'
        audit=result['argument_audit'][-1]
        assert json.loads(audit['raw_arguments'])['graph_version']=='None'
        assert json.loads(audit['effective_arguments'])['graph_version'] is None
        assert len(audit['edits'])==1
    else:assert 'argument_audit' not in result
