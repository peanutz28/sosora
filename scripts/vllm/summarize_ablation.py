"""Summarize all 24 frozen repeated runs, keeping requested denominators."""
import argparse
import collections
import json
from pathlib import Path
import statistics

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);a=p.parse_args();root=Path(a.evidence);protocol=json.loads((root/'protocol.json').read_text());result=[];family_detail={}
    for split in protocol['split_order']:
        catalog={r['scenario_id']:r['scenario']['family'] for r in map(json.loads,(Path('ml/nemo_gym/data')/f'{split}.jsonl').read_text().splitlines())}
        for arm in protocol['arms']:
            passes=[];errors=[];families={};issues=collections.Counter()
            for repeat in range(1,4):
                folder=root/f'{split}_{arm}_r{repeat}'/'raw';rows=list(map(json.loads,(folder/'rollouts.jsonl').read_text().splitlines()));assert len(rows)==14 and {r['scenario_id'] for r in rows}==set(catalog)
                metrics=json.loads((folder/'metrics.json').read_text());assert metrics['scenarios_completed']==14
                passes.append(sum(r['reward']==1 for r in rows));errors.append(sum(r['error_type'] is not None for r in rows))
                for r in rows:
                    f=families.setdefault(catalog[r['scenario_id']],{'passed':0,'attempts':0});f['passed']+=r['reward']==1;f['attempts']+=1;issues.update(r['issues'])
            result.append({'split':split,'arm':arm,'passes_per_14':passes,'mean_passes':statistics.mean(passes),'min_passes':min(passes),'max_passes':max(passes),'mean_percent':100*statistics.mean(passes)/14,'range_percent':[100*min(passes)/14,100*max(passes)/14],'provider_errors_per_run':errors})
            family_detail[split+'_'+arm]={'families':families,'overlapping_verifier_issue_counts':dict(issues)}
    (root/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(root/'family_analysis.json').write_text(json.dumps(family_detail,indent=2)+'\n')
    lines=['| Split | Policy | Passes in three runs /14 | Mean /14 | Range /14 | Mean % | Provider errors |','|---|---|---|---:|---|---:|---|']
    for r in result:lines.append(f"| {r['split']} | {r['arm']} | {', '.join(map(str,r['passes_per_14']))} | {r['mean_passes']:.2f} | {r['min_passes']}–{r['max_passes']} | {r['mean_percent']:.1f}% | {', '.join(map(str,r['provider_errors_per_run']))} |")
    (root/'summary.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
if __name__=='__main__':main()
