"""Frozen four-way prompt ablation using the unchanged Gym execution loop.

Only config contents differ. Temporary config roots let the existing grounded_v2
file loader select each JSON without modifying runner code or tool schemas.
Raw metrics retain runner policy=grounded_v2; ablation_run.json names the arm.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from ml.nemo_gym import evaluate_agent

ARMS=['baseline','tool_descriptions_only','system_prompt_only','grounded_v2']
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['ml/nemo_gym/evaluate_agent.py','ml/nemo_gym/tool_arguments.py','ml/nemo_gym/core.py','ml/nemo_gym/app.py','ml/nemo_gym/scenarios.py','ml/nemo_gym/data/validation.jsonl','ml/nemo_gym/data/test.jsonl','scripts/vllm/serve_brev.sh']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def prepare(out):
    out.mkdir(parents=True,exist_ok=False);(out/'policies').mkdir()
    full=json.loads((ROOT/'ml/nemo_gym/policies/grounded_v2.json').read_text())
    configs={
        'baseline':{'prompt':evaluate_agent.BASELINE,'tool_descriptions':{}},
        'tool_descriptions_only':{'prompt':evaluate_agent.BASELINE,'tool_descriptions':full['tool_descriptions']},
        'system_prompt_only':{'prompt':full['prompt'],'tool_descriptions':{}},
        'grounded_v2':{'prompt':full['prompt'],'tool_descriptions':full['tool_descriptions']}}
    for name,c in configs.items():save(out/'policies'/f'{name}.json',c)
    save(out/'protocol.json',{'created_utc':now(),'simulated':True,'arms':ARMS,'repetitions_per_split':3,'split_order':['validation','test'],'run_order':'rotate arm order by repeat index; sequential, no concurrent requests','test_previously_used':True,'policy_changes_after_test':False,'development_or_selection_in_this_experiment':False,'argument_adapter':'none','runner_policy_label':'grounded_v2 for every arm; actual arm in ablation_run.json','configuration_selection':'Only __file__ config-root lookup differs; unchanged main() reads same-name JSON and byte-identical task files. No execution, schema, sampling or verifier patch.','sampling':{'temperature':1.0,'max_tokens':1024,'parallel_tool_calls':False,'max_turns':12,'per_call_timeout_seconds':60},'source_sha256':{p:sha(ROOT/p) for p in SOURCES},'policy_sha256':{a:sha(out/'policies'/f'{a}.json') for a in ARMS}})

def run(out):
    protocol=json.loads((out/'protocol.json').read_text())
    def check():
        assert all(sha(ROOT/p)==h for p,h in protocol['source_sha256'].items()),'Source changed'
        assert all(sha(out/'policies'/f'{a}.json')==h for a,h in protocol['policy_sha256'].items()),'Policy changed'
    check()
    with (out/'session_started.json').open('x') as f:json.dump({'started_utc':now()},f)
    with tempfile.TemporaryDirectory(prefix='sosora-frozen-ablation-') as tmp:
        tmp=Path(tmp);(tmp/'data').mkdir();(tmp/'policies').mkdir()
        for split in ['validation','test']:shutil.copyfile(ROOT/f'ml/nemo_gym/data/{split}.jsonl',tmp/'data'/f'{split}.jsonl')
        original=evaluate_agent.__file__
        try:
            evaluate_agent.__file__=str(tmp/'evaluate_agent.py')
            for split in ['validation','test']:
                if split=='test':save(out/'test_opened.json',{'opened_utc':now(),'policy_hashes':protocol['policy_sha256'],'all_validation_complete':True})
                for repeat in range(3):
                    order=ARMS[repeat:]+ARMS[:repeat]
                    for arm in order:
                        check();dest=out/f'{split}_{arm}_r{repeat+1}'
                        if dest.exists():raise SystemExit('Never overwrite or retry a run')
                        shutil.copyfile(out/'policies'/f'{arm}.json',tmp/'policies'/'grounded_v2.json')
                        dest.mkdir();save(dest/'ablation_run.json',{'arm':arm,'split':split,'repeat':repeat+1,'started_utc':now(),'configuration_sha256':protocol['policy_sha256'][arm]})
                        sys.argv=['evaluate_agent','--policy','grounded_v2','--split',split,'--limit','14','--max-turns','12','--max-seconds','14400','--argument-adapter','none','--output',str(dest/'raw')]
                        print(json.dumps({'starting':arm,'split':split,'repeat':repeat+1}),flush=True)
                        evaluate_agent.main();check()
            save(out/'session_completed.json',{'completed_utc':now(),'runs':24})
        finally:evaluate_agent.__file__=original

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--prepare',action='store_true');a=p.parse_args();out=Path(a.output).resolve()
    prepare(out) if a.prepare else run(out)
if __name__=='__main__':main()
