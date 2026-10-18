import json
from pathlib import Path
from scripts.vllm.run_ablation import prepare, ARMS
from ml.nemo_gym.evaluate_agent import BASELINE


def test_ablation_is_exact_two_by_two_configuration_matrix(tmp_path):
    out=tmp_path/'frozen';prepare(out)
    configs={a:json.loads((out/'policies'/f'{a}.json').read_text()) for a in ARMS}
    full=json.loads(Path('ml/nemo_gym/policies/grounded_v2.json').read_text())
    assert configs['baseline']=={'prompt':BASELINE,'tool_descriptions':{}}
    assert configs['tool_descriptions_only']=={'prompt':BASELINE,'tool_descriptions':full['tool_descriptions']}
    assert configs['system_prompt_only']=={'prompt':full['prompt'],'tool_descriptions':{}}
    assert configs['grounded_v2']=={'prompt':full['prompt'],'tool_descriptions':full['tool_descriptions']}
    p=json.loads((out/'protocol.json').read_text())
    assert p['argument_adapter']=='none'
    assert p['test_previously_used'] is True
    assert p['repetitions_per_split']==3
    assert p['split_order']==['validation','test']
