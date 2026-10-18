"""Report every fresh-exam run, including incomplete runs without retry."""
import argparse
import collections
import json
from pathlib import Path
import statistics

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);a=p.parse_args();root=Path(a.evidence);repo=Path(__file__).resolve().parents[2]
    catalog={x['scenario_id']:x['scenario']['family'] for x in map(json.loads,(repo/'ml/nemo_gym/data/test_fresh.jsonl').read_text().splitlines())}
    seal=json.loads((root/'seal.json').read_text());results=[];family_counts={};all_runs=[]
    for arm in seal['arms']:
        full_scores=[];arm_runs=[];families={f:{'passed':0,'evaluated':0,'planned':18,'passes_per_run':[]} for f in sorted(set(catalog.values()))};errors=collections.Counter();issues=collections.Counter()
        for repeat in range(1,4):
            folder=root/f'{arm}_r{repeat}';file=folder/'raw/rollouts.jsonl'
            rows=list(map(json.loads,file.read_text().splitlines())) if file.exists() else []
            assert len({r['scenario_id'] for r in rows})==len(rows) and set(r['scenario_id'] for r in rows)<=set(catalog)
            complete=len(rows)==42 and (folder/'raw/metrics.json').exists()
            if complete:
                m=json.loads((folder/'raw/metrics.json').read_text());assert m['scenarios_completed']==42 and m['mean_reward']==sum(r['reward'] for r in rows)/42
                full_scores.append(sum(r['reward']==1 for r in rows))
            for r in rows:
                f=families[catalog[r['scenario_id']]];f['passed']+=r['reward']==1;f['evaluated']+=1;issues.update(r['issues'])
                if r['error_type']:errors[r['error_type']]+=1
            for name,f in families.items():f['passes_per_run'].append(sum(r['reward']==1 for r in rows if catalog[r['scenario_id']]==name) if rows else None)
            entry={'arm':arm,'repeat':repeat,'status':'complete' if complete else ('partial' if rows else 'not_completed'),'passed':sum(r['reward']==1 for r in rows),'evaluated':len(rows),'requested':42,'provider_errors':sum(r['error_type'] is not None for r in rows)}
            arm_runs.append(entry);all_runs.append(entry)
        results.append({'arm':arm,'complete_runs':len(full_scores),'passes_per_complete_run':full_scores,'mean_passes_per42':statistics.mean(full_scores) if full_scores else None,'range_passes_per42':[min(full_scores),max(full_scores)] if full_scores else None,'provider_errors':dict(errors),'provider_error_count':sum(errors.values()),'runs':arm_runs,'verifier_issue_counts':dict(issues)})
        family_counts[arm]=families
    report={'policies':results,'families':family_counts,'runs':all_runs,'planned_scenario_attempts':378,'evaluated_scenario_attempts':sum(r['evaluated'] for r in all_runs),'provider_errors':sum(r['provider_errors'] for r in all_runs),'complete_runs':sum(r['status']=='complete' for r in all_runs),'selection':False,'policy_changes':False,'mean_denominator':'Only complete42-case runs enter mean/range. Any incomplete run stays separately reported; no retry or imputed score.'}
    (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['| Policy | Complete runs | Passes /42 | Mean /42 | Range /42 | Provider errors |','|---|---:|---|---:|---|---:|']
    for r in results:
        mean=f"{r['mean_passes_per42']:.2f}" if r['mean_passes_per42'] is not None else 'N/A';ran='–'.join(map(str,r['range_passes_per42'])) if r['range_passes_per42'] else 'N/A';lines.append(f"| {r['arm']} | {r['complete_runs']}/3 | {', '.join(map(str,r['passes_per_complete_run'])) or 'none'} | {mean} | {ran} | {r['provider_error_count']} |")
    lines+=['','Per-family counts are passes / evaluated attempts across three runs (planned 18 each):','','| Family | Baseline | System prompt only | grounded_v2 |','|---|---|---|---|']
    for family in sorted(set(catalog.values())):
        cells=[]
        for arm in seal['arms']:
            f=family_counts[arm][family];cells.append(f"{f['passed']}/{f['evaluated']} ({', '.join('—' if n is None else str(n) for n in f['passes_per_run'])})")
        lines.append('| '+family+' | '+' | '.join(cells)+' |')
    incomplete=[r for r in all_runs if r['status']!='complete']
    if incomplete:lines+=['','Incomplete runs (not retried):','',json.dumps(incomplete,indent=2)]
    (root/'summary.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
if __name__=='__main__':main()
