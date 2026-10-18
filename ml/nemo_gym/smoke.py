"""Actual official Gym HTTP route smoke. Scripted fixtures, not LLM evaluation."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
import nemo_gym
from ml.nemo_gym.app import local_app
from ml.nemo_gym.scenarios import FAMILIES,make_scenario
from ml.nemo_gym.core import expected_status


def main():
    cases=[]
    with TestClient(local_app()) as client:
        for family in FAMILIES:
            scenario=make_scenario(family,7,'train')
            client.cookies.clear()
            client.post('/seed_session',json={'scenario_id':scenario.scenario_id}).raise_for_status()
            output=[]
            def call(name,args):
                result=client.post('/'+name,json=args);result.raise_for_status()
                call_id=f'call_{len(output)}'
                output.append({'type':'function_call','id':call_id,'call_id':call_id,'name':name,'arguments':json.dumps(args),'status':'completed'})
                output.append({'type':'function_call_output','call_id':call_id,'output':json.dumps(result.json())})
                return result.json()
            incident=call('get_incident',{})
            graph=call('get_road_status',{}) if incident['incident_node'] else None
            evidence=call('get_damage_evidence',{})
            if incident['incident_node'] is None:status='needs_location';path=[];version=None
            elif not graph.get('available'):status='unknown';path=[];version=None
            else:
                version=graph['graph_version']
                routes=call('calculate_candidate_routes',{'graph_version':version})
                reachability=call('check_reachability',{'graph_version':version})
                if not routes.get('available') or not reachability.get('available'):status='unknown';path=[]
                else:status='reachable' if reachability['reachable'] else 'unreachable';path=routes['candidate_paths'][0] if routes['candidate_paths'] else []
            final={'status':status,'graph_version':version,'path':path,'requires_human_review':True,'review_status':'unverified','reason':'Scripted fixture; graph planning only, no field safety clearance.'}
            call('submit_recommendation',final)
            response={'id':'scripted-protocol-smoke','created_at':0.0,'model':'none-scripted-fixture','object':'response','parallel_tool_calls':False,'tool_choice':'auto','tools':[], 'output':output}
            verify=client.post('/verify',json={'scenario_id':scenario.scenario_id,'responses_create_params':{'input':[]},'response':response});verify.raise_for_status()
            result=verify.json()
            cases.append({'scenario_id':scenario.scenario_id,'family':family,'scripted_status':status,'reward':result['reward'],'issues':result['issues'],'trace':output})
    summary={'verification_kind':'scripted integration fixtures; not language-agent benchmark','upstream_version':nemo_gym.__version__,'upstream_commit':'3045a793346a31291d7ea4ae6af3f94a35036ce5','language_model_calls':0,'cases':cases,'passed':sum(c['reward']==1 for c in cases),'total':len(cases)}
    path=Path(__file__).parent/'evidence/integration_smoke.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='cases'}))
    if summary['passed']!=summary['total']:raise SystemExit(1)
if __name__=='__main__':main()
