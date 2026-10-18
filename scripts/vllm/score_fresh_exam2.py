"""Offline scoring and seal audit. No inference request or argument repair is performed."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
from fastapi.testclient import TestClient
from ml.nemo_gym.app import local_app
from ml.nemo_gym.tool_arguments import adapt_arguments
from scripts.vllm.run_fresh_exam2 import verify_seal
from scripts.vllm.summarize_fresh_exam2 import main as summarize

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',default='ml/nemo_gym/evidence/test_fresh2_2026-10-18')
    args=parser.parse_args();root=Path(args.evidence).resolve()
    opened=json.loads((root/'opened.json').read_text());seal=verify_seal(root,opened['seal_commit'])
    committed=dt.datetime.fromtimestamp(int(subprocess.check_output(['git','show','-s','--format=%ct',opened['seal_commit']],cwd=ROOT)),dt.timezone.utc)
    assert committed<=dt.datetime.fromisoformat(opened['opened_utc'])
    catalog={r['scenario_id']:r for r in map(json.loads,(ROOT/'ml/nemo_gym/data/test_fresh2.jsonl').read_text().splitlines())}
    verified=0;calls=0;run_order=[]
    with TestClient(local_app()) as client:
        for repeat,order in enumerate(seal['repeat_order'],1):
            for arm in order:
                folder=root/f'{arm}_r{repeat}';raw=folder/'raw'
                if not (raw/'rollouts.jsonl').exists():continue
                run=json.loads((folder/'exam_run.json').read_text());run_order.append(run)
                assert run['configuration_sha256']==seal['policy_sha256'][arm]
                assert run['argument_adapter']==seal['argument_adapters'][arm]
                rows=list(map(json.loads,(raw/'rollouts.jsonl').read_text().splitlines()))
                assert len(rows)==len({r['scenario_id'] for r in rows})
                for row in rows:
                    params=catalog[row['scenario_id']]['responses_create_params']
                    result=client.post('/verify',json={'scenario_id':row['scenario_id'],'responses_create_params':params,'response':{'id':'offline-'+row['scenario_id'],'created_at':0,'model':seal['model'],'object':'response','parallel_tool_calls':False,'tool_choice':'auto','tools':params['tools'],'output':row['trajectory']}})
                    result.raise_for_status();score=result.json()
                    assert score['reward']==row['reward'] and score['issues']==row['issues']
                    if seal['argument_adapters'][arm]=='none':assert not row.get('argument_audit')
                    else:
                        for entry in row['argument_audit']:
                            schema=next((t['parameters'] for t in params['tools'] if t['name']==entry['name']),{})
                            effective,edits=adapt_arguments(entry['raw_arguments'],schema)
                            assert effective==entry['effective_arguments'] and edits==entry['edits']
                    verified+=1
                if (raw/'metrics.json').exists():
                    metrics=json.loads((raw/'metrics.json').read_text());config=json.loads((raw/'evaluation_config.json').read_text())
                    assert metrics['scenarios_completed']==len(rows)
                    assert metrics['mean_reward']==sum(r['reward'] for r in rows)/len(rows)
                    assert metrics['error_count']==sum(r['error_type'] is not None for r in rows)
                    assert config['argument_adapter']==seal['argument_adapters'][arm]
                    assert config['prompt']==json.loads((root/'policies'/f'{arm}.json').read_text())['prompt']
                    assert config['max_turns']==12 and config['limit']==42 and config['split']=='test_fresh2'
                    calls+=metrics['language_model_calls']
    starts=[dt.datetime.fromisoformat(r['started_utc']) for r in run_order]
    assert starts==sorted(starts)
    completion=json.loads((root/'completion.json').read_text())
    assert dt.datetime.fromisoformat(completion['at_utc'])<dt.datetime(2026,10,18,12,40,tzinfo=dt.timezone.utc)
    audit={'passed':True,'seal_commit':opened['seal_commit'],'commit_precedes_open':True,'rescored_attempts':verified,'recorded_model_calls':calls,'adapter_raw_effective_edits_verified':True,'previous_split_bytes_unchanged':True,'completion':completion}
    (root/'integrity_check.json').write_text(json.dumps(audit,indent=2)+'\n')
    import sys
    sys.argv=[sys.argv[0],'--evidence',str(root)];summarize()
    print(json.dumps(audit))
if __name__=='__main__':main()
