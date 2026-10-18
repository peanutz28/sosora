"""Verify saved repeated-run coverage, raw accuracy and latency aggregation."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import tarfile

ROOT=Path(__file__).resolve().parents[2]

def read(p):return json.loads(p.read_text())
def main():
    gym=ROOT/'ml/nemo_gym/evidence/ablation_reliability_2026-10-18';radio=ROOT/'docs/evidence/reliability_2026-10-18';protocol=read(gym/'protocol.json');calls=0
    for split in ['validation','test']:
        ids={x['scenario_id'] for x in map(json.loads,(ROOT/f'ml/nemo_gym/data/{split}.jsonl').read_text().splitlines())}
        for arm in protocol['arms']:
            policy=read(gym/'policies'/f'{arm}.json')
            assert hashlib.sha256((gym/'policies'/f'{arm}.json').read_bytes()).hexdigest()==protocol['policy_sha256'][arm]
            for repeat in range(1,4):
                raw=gym/f'{split}_{arm}_r{repeat}'/'raw';rows=list(map(json.loads,(raw/'rollouts.jsonl').read_text().splitlines()));m=read(raw/'metrics.json');c=read(raw/'evaluation_config.json');assert len(rows)==14 and {x['scenario_id'] for x in rows}==ids
                assert c['prompt']==policy['prompt'] and c['argument_adapter']=='none'
                assert m['scenarios_completed']==14 and m['error_count']==sum(x['error_type'] is not None for x in rows)==0
                assert m['mean_reward']==sum(x['reward'] for x in rows)/14;calls+=m['language_model_calls']
    assert calls==1944
    x=read(radio/'radio_runs.json');rows=x['runs'];assert len(rows)==30 and [r['run'] for r in rows]==list(range(1,31))
    assert all(r['seed_ms']>0 and r['live_success'] for r in rows)
    for i,r in enumerate(rows):
        if i<20:
            assert r['kind']=='beacon' and set(r['closed_segment_ids'])=={'549633356:0:b','549633356:0:f'}
            assert set(r['lost_incident_ids'])=={f'SOS-{j:03}' for j in range(1,6)}==set(r['assessment']['affected_incident_ids'])
        else:assert r['kind']=='ambiguous_responder' and not r['closed_segment_ids'] and not r['lost_incident_ids'] and r['assessment']['needs_human_review']
    for kind in ['beacon','ambiguous_responder']:
        group=[r for r in rows if r['kind']==kind]
        values={'agent_calls':[t['latency_ms'] for r in group for t in r['turns']],'agent_request':[r['agent_request_ms'] for r in group],'end_to_end':[r['end_to_end_ms'] for r in group]}
        for name,v in values.items():
            summary=x['summary'][kind][name];assert summary['n']==len(v) and summary['median_ms']==statistics.median(v) and summary['p95_ms']==sorted(v)[math.ceil(.95*len(v))-1]
    summary=read(radio/'summary.json');assert summary['strict_ambiguity_no_mutation_attempt']['numerator']==1
    assert summary['isolation']['vllm_success_counter_delta']==sum(len(r['turns']) for r in rows)+30==209
    manifest=read(radio/'measurement_sources.json')['backend_runtime_sha256']
    with tarfile.open(radio/'backend_sources.tar.gz') as tar:
        for member in tar.getmembers():assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==manifest[member.name]
    result={'passed':True,'checks':['24 complete unique Gym runs, 336 scenarios, frozen policy hashes and prompt selections, adapter off, metric consistency','1944 Gym calls; no provider errors','20 exact bridge + five-incident outcomes and10 guarded ambiguity outcomes; all fresh-seed requests live','median and nearest-rank p95 recomputed from every raw timing','strict model abstention caveat retained;209 generation request counter match','frozen backend archive matches source manifest']}
    (radio/'evidence_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
