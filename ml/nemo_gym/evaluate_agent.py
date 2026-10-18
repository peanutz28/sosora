"""Run a real chat-completions agent against official Gym tools/verifier.
This custom agent loop does not claim to be Gym's full CLI rollout harness.
"""
import argparse
import json
import os
from pathlib import Path
import time
import httpx
from fastapi.testclient import TestClient
from ml.nemo_gym.app import local_app
from ml.nemo_gym.scenarios import SYSTEM

BASELINE='Assess this simulated rescue incident using the available tools. Finish by calling submit_recommendation. Candidate graph routes are not safety clearances.'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=['validation','test'],default='validation')
    parser.add_argument('--policy',choices=['baseline','evidence_first'],required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--limit',type=int,default=3)
    parser.add_argument('--max-turns',type=int,default=12)
    parser.add_argument('--max-seconds',type=float,default=180)
    args=parser.parse_args()
    if args.limit<1 or args.max_turns<1 or args.max_seconds<=0:raise SystemExit('Limits must be positive')
    provider=os.getenv('LLM_PROVIDER','nvidia_api')
    if provider not in {'nvidia_api','redhat_vllm'}:raise SystemExit('Unsupported LLM_PROVIDER')
    key=os.getenv('NVIDIA_API_KEY' if provider=='nvidia_api' else 'LLM_API_KEY')
    if not key:raise SystemExit('Provider API key is not configured; no model call made')
    base=os.getenv('LLM_BASE_URL','https://integrate.api.nvidia.com/v1' if provider=='nvidia_api' else '').rstrip('/')
    url=httpx.URL(base)
    if url.scheme not in {'http','https'} or not url.host or url.userinfo or url.query or url.fragment:raise SystemExit('Invalid LLM_BASE_URL')
    model=os.getenv('LLM_MODEL','nvidia/nemotron-3.5-lightning-30b-a3b')
    out=Path(args.output)
    if out.exists() and any(out.iterdir()):raise SystemExit('Use a new output directory')
    out.mkdir(parents=True,exist_ok=True)
    rows=[json.loads(l) for l in (Path(__file__).parent/'data'/f'{args.split}.jsonl').read_text().splitlines()][:args.limit]
    started=time.monotonic();results=[];calls_made=0
    with TestClient(local_app()) as task,httpx.Client(timeout=60) as llm:
        for row in rows:
            if time.monotonic()-started>=args.max_seconds:break
            task.cookies.clear()
            task.post('/seed_session',json={'scenario_id':row['scenario_id']}).raise_for_status()
            params=row['responses_create_params']
            messages=[{'role':'system','content':SYSTEM if args.policy=='evidence_first' else BASELINE},params['input'][-1]]
            tools=[{'type':'function','function':{k:v for k,v in t.items() if k!='type'}} for t in params['tools']]
            trajectory=[];latencies=[];usage=[];error=None
            for turn in range(args.max_turns):
                if time.monotonic()-started>=args.max_seconds:break
                try:
                    before=time.monotonic()
                    response=llm.post(base+'/chat/completions',headers={'Authorization':'Bearer '+key},json={'model':model,'messages':messages,'tools':tools,'parallel_tool_calls':False,'temperature':1.0,'max_tokens':1024})
                    calls_made+=1;latencies.append((time.monotonic()-before)*1000)
                    response.raise_for_status();payload=response.json();message=payload['choices'][0]['message']
                    usage.append(payload.get('usage'))
                    messages.append({k:v for k,v in message.items() if k in {'role','content','tool_calls'}})
                    tool_calls=message.get('tool_calls') or []
                    if not tool_calls:break
                    for tool_call in tool_calls:
                        name=tool_call['function']['name'];arguments=tool_call['function']['arguments'];call_id=tool_call['id']
                        trajectory.append({'type':'function_call','id':call_id,'call_id':call_id,'name':name,'arguments':arguments,'status':'completed'})
                        try:
                            tool_response=task.post('/'+name,json=json.loads(arguments)) if name in {t['name'] for t in params['tools']} else None
                            result=tool_response.json() if tool_response is not None else {'error':'unknown_tool'}
                        except ValueError:result={'error':'malformed_tool_arguments'}
                        text=json.dumps(result)
                        messages.append({'role':'tool','tool_call_id':call_id,'content':text})
                        trajectory.append({'type':'function_call_output','call_id':call_id,'output':text})
                    if any(t['function']['name']=='submit_recommendation' for t in tool_calls):break
                except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError) as exc:
                    error=type(exc).__name__;break
            official_response={'id':'real-agent-'+row['scenario_id'],'created_at':time.time(),'model':model,'object':'response','parallel_tool_calls':False,'tool_choice':'auto','tools':params['tools'],'output':trajectory}
            verify=task.post('/verify',json={'scenario_id':row['scenario_id'],'responses_create_params':params,'response':official_response})
            verify.raise_for_status();scored=verify.json()
            result={'scenario_id':row['scenario_id'],'reward':scored['reward'],'issues':scored['issues'],'error_type':error,'request_latencies_ms':latencies,'usage':usage,'trajectory':trajectory}
            results.append(result)
            with (out/'rollouts.jsonl').open('a') as handle:handle.write(json.dumps(result)+'\n')
    summary={'status':'evaluated' if results else 'not_evaluated','model':model,'provider':provider,'policy':args.policy,'split':args.split,'language_model_calls':calls_made,'scenarios_completed':len(results),'requested_limit':args.limit,'mean_reward':sum(r['reward'] for r in results)/len(results) if results else None,'error_count':sum(r['error_type'] is not None for r in results),'elapsed_seconds':time.monotonic()-started,'harness':'custom chat-completions agent using official NeMo Gym resource-server HTTP tools and verify; not full Gym CLI','upstream_commit':'3045a793346a31291d7ea4ae6af3f94a35036ce5','improvement_claim':False}
    (out/'metrics.json').write_text(json.dumps(summary,indent=2))
    (out/'evaluation_config.json').write_text(json.dumps({'split':args.split,'policy':args.policy,'limit':args.limit,'max_turns':args.max_turns,'max_seconds':args.max_seconds,'prompt':SYSTEM if args.policy=='evidence_first' else BASELINE,'model':model},indent=2))
    print(json.dumps(summary))
if __name__=='__main__':main()
