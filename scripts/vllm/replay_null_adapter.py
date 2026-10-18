"""Offline validation replay diagnostic; no LLM calls and no new test score."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from fastapi.testclient import TestClient
from ml.nemo_gym.app import local_app
from ml.nemo_gym.tool_arguments import ADAPTER, adapt_arguments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    source=root/'ml/nemo_gym/evidence/grounded_v2_2026-10-18/validation_grounded_v2_r02/rollouts.jsonl'
    data=root/'ml/nemo_gym/data/validation.jsonl'
    rows={x['scenario_id']:x for x in map(json.loads,data.read_text().splitlines())}
    out=Path(args.output)
    if out.exists():raise SystemExit('Use a fresh output directory')
    out.mkdir(parents=True)
    results=[]
    with TestClient(local_app()) as client:
        for original in map(json.loads,source.read_text().splitlines()):
            row=rows[original['scenario_id']];trajectory=deepcopy(original['trajectory']);audit=[]
            for call in trajectory:
                if call['type']!='function_call':continue
                schema=next((t['parameters'] for t in row['responses_create_params']['tools'] if t['name']==call['name']),{})
                raw=call['arguments'];effective,edits=adapt_arguments(raw,schema)
                call['arguments']=effective
                if edits:audit.append({'call_id':call['call_id'],'name':call['name'],'raw_arguments':raw,'effective_arguments':effective,'edits':edits})
            # Verify reads function calls; historical tool outputs are retained,
            # not re-labeled as newly executed successful tool responses.
            response={'id':'offline-validation-replay','created_at':0,'model':'recorded-validation-no-new-model','object':'response','parallel_tool_calls':False,'tool_choice':'auto','tools':row['responses_create_params']['tools'],'output':trajectory}
            verified=client.post('/verify',json={'scenario_id':row['scenario_id'],'responses_create_params':row['responses_create_params'],'response':response})
            verified.raise_for_status();v=verified.json()
            results.append({'scenario_id':row['scenario_id'],'family':row['scenario']['family'],'original_reward':original['reward'],'replay_reward':v['reward'],'issues':v['issues'],'argument_audit':audit})
    (out/'replay.json').write_text(json.dumps(results,indent=2)+'\n')
    summary={'kind':'offline recorded VALIDATION call replay diagnostic; NOT a fresh model evaluation','simulated':True,'adapter':ADAPTER,'new_llm_calls':0,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'validation_tasks_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'before_passed':sum(x['original_reward']==1 for x in results),'after_replay_passed':sum(x['replay_reward']==1 for x in results),'total':len(results),'edited_calls':sum(len(x['argument_audit']) for x in results),'limitations':['Historical tool outputs are retained; only call arguments are reverified.','No new test or live model evaluation.','Verifies encoding repair, not improved reasoning or broad generalization.']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))


if __name__=='__main__':main()
