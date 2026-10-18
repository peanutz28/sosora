"""Offline accounting tests; no provider or repair logic is changed."""
import importlib.util
import json
from pathlib import Path
import sys


def test_summary_separates_field_call_and_scenario_repairs_and_retains_partial_runs(tmp_path, monkeypatch):
    script=Path('scripts/vllm/summarize_fresh_exam2.py').resolve()
    spec=importlib.util.spec_from_file_location('fresh2_summary',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    arms=['baseline','grounded_v2','grounded_v2_nullable']
    (tmp_path/'seal.json').write_text(json.dumps({'arms':arms}))
    scenario=json.loads(Path('ml/nemo_gym/data/test_fresh2.jsonl').read_text().splitlines()[0])['scenario_id']
    for arm in arms:
        raw=tmp_path/f'{arm}_r1/raw';raw.mkdir(parents=True)
        row={'scenario_id':scenario,'reward':1,'issues':[],'error_type':None}
        if arm=='grounded_v2_nullable':
            row['argument_audit']=[{'edits':[{'field':'graph_version','before':'None','after':None}]},{'edits':[]},{'edits':[{'field':'graph_version','before':'null','after':None}]}]
        (raw/'rollouts.jsonl').write_text(json.dumps(row)+'\n')
    monkeypatch.setattr(sys,'argv',[str(script),'--evidence',str(tmp_path)])
    module.main()
    summary=json.loads((tmp_path/'summary.json').read_text())
    assert summary['evaluated_scenario_attempts']==3
    assert summary['complete_runs']==0
    adapted=next(p for p in summary['policies'] if p['arm']=='grounded_v2_nullable')
    assert adapted['repaired_fields']==2
    assert adapted['repaired_tool_calls']==2
    assert adapted['repaired_scenarios']==1
    assert adapted['mean_passes_per42'] is None
    assert adapted['range_passes_per42'] is None
    assert adapted['runs'][0]['status']=='partial'
    assert adapted['runs'][1]['status']=='not_completed'
    assert all(p['repaired_fields']==0 for p in summary['policies'] if p['arm']!='grounded_v2_nullable')
