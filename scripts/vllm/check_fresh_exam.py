"""Audit sealed fresh-exam provenance and completed/raw result consistency."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def main():
    root=ROOT/'ml/nemo_gym/evidence/test_fresh_2026-10-18';seal=read(root/'seal.json');opened=read(root/'opened.json');commit=opened['seal_commit']
    assert subprocess.check_output(['git','show',commit+':'+str((root/'seal.json').relative_to(ROOT))],cwd=ROOT)==(root/'seal.json').read_bytes()
    assert seal['test_fresh_opened_by_model_run'] is False and seal['model_calls_on_test_fresh']==0
    for name,h in seal['legacy_hashes_before'].items():assert sha(ROOT/name)==h==seal['legacy_hashes_after'][name]
    for name,h in seal['frozen_source_sha256'].items():assert sha(ROOT/name)==h
    for arm,h in seal['policy_sha256'].items():assert sha(root/'policies'/f'{arm}.json')==h
    assert sha(ROOT/'ml/nemo_gym/data/test_fresh.jsonl')==seal['fresh_task_sha256']
    commit_time=dt.datetime.fromtimestamp(int(subprocess.check_output(['git','show','-s','--format=%ct',commit],cwd=ROOT)),dt.timezone.utc)
    assert commit_time<=dt.datetime.fromisoformat(opened['opened_utc'])
    rows=list(map(json.loads,(ROOT/'ml/nemo_gym/data/test_fresh.jsonl').read_text().splitlines()));ids={r['scenario_id'] for r in rows};assert len(ids)==42
    reports=[];calls=0
    for repeat,order in enumerate(seal['repeat_order'],1):
        for arm in order:
            folder=root/f'{arm}_r{repeat}';raw=folder/'raw';p=raw/'rollouts.jsonl'
            if not p.exists():continue
            run=read(folder/'exam_run.json');assert run['arm']==arm and run['configuration_sha256']==seal['policy_sha256'][arm]
            output=list(map(json.loads,p.read_text().splitlines()));assert len(output)==len({r['scenario_id'] for r in output}) and set(r['scenario_id'] for r in output)<=ids
            if (raw/'metrics.json').exists():
                m=read(raw/'metrics.json');c=read(raw/'evaluation_config.json');assert m['scenarios_completed']==len(output) and m['mean_reward']==sum(r['reward'] for r in output)/len(output)
                assert m['error_count']==sum(r['error_type'] is not None for r in output)
                assert c['split']=='test_fresh' and c['limit']==42 and c['max_turns']==12 and c['argument_adapter']=='none'
                assert c['prompt']==read(root/'policies'/f'{arm}.json')['prompt'];calls+=m['language_model_calls']
            reports.append({'arm':arm,'repeat':repeat,'cases':len(output),'provider_errors':sum(r['error_type'] is not None for r in output)})
    completion=read(root/'completion.json');assert dt.datetime.fromisoformat(completion['at_utc'])<dt.datetime(2026,10,18,10,30,tzinfo=dt.timezone.utc)
    result={'passed':True,'seal_commit':commit,'commit_precedes_exam_open':True,'legacy_bytes_unchanged':True,'frozen_source_and_policy_hashes_unchanged':True,'unique_fresh_cases':42,'recorded_model_calls':calls,'runs':reports,'completion_status':completion['status'],'completed_before0630et':True}
    (root/'integrity_check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
