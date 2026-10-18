import hashlib
import json
from collections import Counter
from pathlib import Path
from ml.nemo_gym.scenarios import FAMILIES, generate

PREVIOUS={
 'train':'6259d74f38ab28f446193584856dca9979e4c8d9c407e1837f4a23bd67d78875',
 'validation':'95cc3e20a782cd11c73c1ce5211b5fbdf9df5f867844472ed472b6abde643650',
 'test':'2b86c0e594b586f733a03f23ae5e607dfaa02a5182e4a1111a921945a8587e3b',
 'test_fresh':'37162bed13593d17438f7352173be649b486adff7c78328c4ff2206268cfd0e8',
}

def test_new_exam_preserves_all_previous_splits_and_covers_42_disjoint_cases(tmp_path):
    generate(tmp_path)
    previous_ids=set()
    for split,digest in PREVIOUS.items():
        file=tmp_path/(split+'.jsonl')
        assert hashlib.sha256(file.read_bytes()).hexdigest()==digest
        previous_ids.update(json.loads(line)['scenario_id'] for line in file.read_text().splitlines())
    file=tmp_path/'test_fresh2.jsonl'
    rows=[json.loads(line) for line in file.read_text().splitlines()]
    assert len(rows)==len({r['scenario_id'] for r in rows})==42
    assert not previous_ids.intersection(r['scenario_id'] for r in rows)
    assert Counter(r['scenario']['family'] for r in rows)=={f:6 for f in FAMILIES}
    assert Counter(len(r['scenario']['initial_route']) for r in rows)=={n:7 for n in range(19,25)}
    assert all(r['scenario']['split']=='test_fresh2' for r in rows)
    assert file.read_bytes()==Path('ml/nemo_gym/data/test_fresh2.jsonl').read_bytes()


def test_adapter_is_exactly_the_audited_version():
    file=Path('ml/nemo_gym/tool_arguments.py')
    assert hashlib.sha256(file.read_bytes()).hexdigest()=='35dadb940fce81f6822efaace52fe820bc0388208dc84086e25bb9ebcc9875f0'
