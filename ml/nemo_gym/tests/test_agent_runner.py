import json
import sys
import pytest
from ml.nemo_gym import evaluate_agent


def test_missing_credentials_makes_no_output_or_calls(monkeypatch,tmp_path):
    monkeypatch.delenv('NVIDIA_API_KEY',raising=False)
    monkeypatch.setenv('LLM_PROVIDER','nvidia_api')
    out=tmp_path/'absent'
    monkeypatch.setattr(sys,'argv',['evaluate_agent','--policy','baseline','--output',str(out)])
    with pytest.raises(SystemExit,match='not configured'):evaluate_agent.main()
    assert not out.exists()


@pytest.mark.parametrize("policy", ["baseline", "grounded_v2"])
def test_runner_uses_real_task_and_verifier_with_mocked_provider(monkeypatch,tmp_path,policy):
    """Only provider responses are fixtures; Gym tools and verifier really run."""
    monkeypatch.setenv('LLM_PROVIDER','nvidia_api')
    monkeypatch.setenv('NVIDIA_API_KEY','fake-key-never-save')
    monkeypatch.delenv('LLM_BASE_URL',raising=False)
    out=tmp_path/'evaluation'
    calls=[('get_incident',{}),('get_road_status',{}),('calculate_candidate_routes',{'graph_version':2}),('check_reachability',{'graph_version':2}),('submit_recommendation',{'status':'reachable','graph_version':2,'path':['node_0','node_8'],'requires_human_review':True,'review_status':'unverified','reason':'Candidate graph path only; field verification required.'})]
    class Provider:
        index=0
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,headers,json):
            assert headers['Authorization']=='Bearer fake-key-never-save'
            assert url=='https://integrate.api.nvidia.com/v1/chat/completions'
            if policy == 'grounded_v2':
                assert 'Every assistant turn must call exactly ONE tool' in json['messages'][0]['content']
                assert json['tools'][0]['function']['description'].startswith('FIRST tool.')
                assert json['tools'][0]['function']['strict'] is True
                assert json['tools'][0]['function']['parameters']['additionalProperties'] is False
            else:
                assert json['messages'][0]['content'] == evaluate_agent.BASELINE
                assert json['tools'][0]['function']['description'] == 'Get reported incident and stale initial route.'
            name,args=calls[self.index];self.index+=1
            text=__import__('json').dumps(args)
            payload={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':[{'id':f'call_{self.index}','type':'function','function':{'name':name,'arguments':text}}]}}],'usage':{'total_tokens':10}}
            class Response:
                def raise_for_status(self):pass
                def json(self):return payload
            return Response()
    monkeypatch.setattr(evaluate_agent.httpx,'Client',Provider)
    monkeypatch.setattr(sys,'argv',['evaluate_agent','--policy',policy,'--split','validation','--limit','1','--output',str(out)])
    evaluate_agent.main()
    metrics=json.loads((out/'metrics.json').read_text())
    assert metrics['mean_reward']==1 and metrics['language_model_calls']==5
    assert metrics['improvement_claim'] is False
    assert all('fake-key-never-save' not in p.read_text() for p in out.iterdir())
