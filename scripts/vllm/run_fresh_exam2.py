"""Committed, fixed-policy fresh exam; terminate generation by08:35ET.

Uses the existing config-root loader, runner and official tools/verifier unchanged.
No policy selection or retries; completed/partial runs remain on disk.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
ARMS=['baseline','grounded_v2','grounded_v2_nullable']
STOP=dt.datetime(2026,10,18,12,35,tzinfo=dt.timezone.utc)

def now():return dt.datetime.now(dt.timezone.utc)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def verify_seal(out,commit):
    seal=out/'seal.json';relative=str(seal.relative_to(ROOT));record=json.loads(seal.read_text())
    assert subprocess.check_output(['git','show',commit+':'+relative],cwd=ROOT)==seal.read_bytes(),'Seal not committed'
    assert record['test_fresh2_opened_by_model_run'] is False and record['model_calls_on_test_fresh2']==0
    for p,h in record['frozen_source_sha256'].items():assert sha(ROOT/p)==h,p
    for arm,h in record['policy_sha256'].items():
        p=out/'policies'/f'{arm}.json';assert sha(p)==h
        assert subprocess.check_output(['git','show',commit+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
    p=ROOT/'ml/nemo_gym/data/test_fresh2.jsonl';assert sha(p)==record['fresh_task_sha256']
    assert subprocess.check_output(['git','show',commit+':ml/nemo_gym/data/test_fresh2.jsonl'],cwd=ROOT)==p.read_bytes()
    for path,h in record['legacy_hashes_before'].items():
        assert sha(ROOT/path)==h==record['legacy_hashes_after'][path],path
    assert record['policy_sha256']['grounded_v2']==record['policy_sha256']['grounded_v2_nullable']
    assert record['argument_adapters']=={'baseline':'none','grounded_v2':'none','grounded_v2_nullable':'nullable-null-v1'}
    return record

def run(out,commit):
    record=verify_seal(out,commit)
    if now()>=STOP:raise SystemExit('Evaluation cutoff passed; no exam opened')
    if os.environ.get('LLM_MODEL')!='nvidia/nemotron-3.5-lightning-30b-a3b':raise SystemExit('Unexpected model')
    with (out/'opened.json').open('x') as f:json.dump({'opened_utc':now().isoformat(),'seal_commit':commit,'policy_hashes':record['policy_sha256'],'evaluation_cutoff_utc':STOP.isoformat(),'documentation_deadline_utc':'2026-10-18T12:40:00+00:00','retries':False,'selection':False},f,indent=2)
    outcomes=[]
    with tempfile.TemporaryDirectory(prefix='sosora-fresh-exam-') as tmp:
        tmp=Path(tmp);(tmp/'data').mkdir();(tmp/'policies').mkdir()
        shutil.copyfile(ROOT/'ml/nemo_gym/data/test_fresh2.jsonl',tmp/'data/test_fresh2.jsonl')
        for repeat in range(3):
            for arm in ARMS[repeat:]+ARMS[:repeat]:
                verify_seal(out,commit)
                remaining=(STOP-now()).total_seconds()
                if remaining<=65:
                    save(out/'completion.json',{'status':'stopped_before_deadline','at_utc':now().isoformat(),'runs':outcomes});return
                dest=out/f'{arm}_r{repeat+1}';dest.mkdir(exist_ok=False)
                shutil.copyfile(out/'policies'/f'{arm}.json',tmp/'policies/grounded_v2.json')
                save(dest/'exam_run.json',{'arm':arm,'repeat':repeat+1,'started_utc':now().isoformat(),'configuration_sha256':record['policy_sha256'][arm],'requested_cases':42,'runner_policy_label':'grounded_v2; arm selected by frozen config root','argument_adapter':record['argument_adapters'][arm]})
                code='import sys; from ml.nemo_gym import evaluate_agent; evaluate_agent.__file__=sys.argv.pop(1); evaluate_agent.main()'
                cmd=[sys.executable,'-c',code,str(tmp/'evaluate_agent.py'),'--policy','grounded_v2','--split','test_fresh2','--limit','42','--max-turns','12','--max-seconds',str(min(14400,remaining-60)),'--argument-adapter',record['argument_adapters'][arm],'--output',str(dest/'raw')]
                print(json.dumps({'starting':arm,'repeat':repeat+1,'at_utc':now().isoformat()}),flush=True)
                with (dest/'session.log').open('w') as log:
                    child=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:exit_code=child.wait(timeout=max(1,(STOP-now()).total_seconds()))
                    except subprocess.TimeoutExpired:
                        child.terminate()
                        try:child.wait(timeout=5)
                        except subprocess.TimeoutExpired:child.kill();child.wait()
                        outcomes.append({'arm':arm,'repeat':repeat+1,'status':'partial_deadline','exit_code':child.returncode})
                        save(out/'completion.json',{'status':'hard_stopped','at_utc':now().isoformat(),'runs':outcomes});return
                outcomes.append({'arm':arm,'repeat':repeat+1,'status':'completed' if exit_code==0 else 'failed_no_retry','exit_code':exit_code})
                save(out/'progress.json',{'at_utc':now().isoformat(),'runs':outcomes});print(json.dumps(outcomes[-1]),flush=True)
                if exit_code!=0:
                    save(out/'completion.json',{'status':'stopped_on_run_error_no_retry','at_utc':now().isoformat(),'runs':outcomes});return
    verify_seal(out,commit);save(out/'completion.json',{'status':'completed','at_utc':now().isoformat(),'runs':outcomes})

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--seal-commit',required=True);a=p.parse_args();run(Path(a.output).resolve(),a.seal_commit)
if __name__=='__main__':main()
