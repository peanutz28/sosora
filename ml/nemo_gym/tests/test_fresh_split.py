import hashlib
import json
from collections import Counter
from pathlib import Path
from ml.nemo_gym.scenarios import FAMILIES,generate

LEGACY={'train':'6259d74f38ab28f446193584856dca9979e4c8d9c407e1837f4a23bd67d78875','validation':'95cc3e20a782cd11c73c1ce5211b5fbdf9df5f867844472ed472b6abde643650','test':'2b86c0e594b586f733a03f23ae5e607dfaa02a5182e4a1111a921945a8587e3b'}

def test_fresh_generation_preserves_old_bytes_and_covers_disjoint_sizes(tmp_path):
    generate(tmp_path)
    old_ids=set()
    for split,digest in LEGACY.items():
        p=tmp_path/(split+'.jsonl');assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
        old_ids.update(json.loads(line)['scenario_id'] for line in p.read_text().splitlines())
    rows=[json.loads(line) for line in (tmp_path/'test_fresh.jsonl').read_text().splitlines()]
    assert len(rows)==len({r['scenario_id'] for r in rows})==42
    assert not old_ids.intersection(r['scenario_id'] for r in rows)
    assert Counter(r['scenario']['family'] for r in rows)=={f:6 for f in FAMILIES}
    assert {len(r['scenario']['initial_route']) for r in rows}==set(range(13,19))
    assert all(r['scenario']['split']=='test_fresh' for r in rows)
    assert (tmp_path/'test_fresh.jsonl').read_bytes()==Path('ml/nemo_gym/data/test_fresh.jsonl').read_bytes()
