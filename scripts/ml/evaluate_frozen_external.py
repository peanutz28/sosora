import json,datetime
from pathlib import Path
from scripts.ml.evaluate_road_tiles import evaluate
from ml.vision.provenance import checkpoint_identity
root=Path('ml/artifacts/sn8_frozen_external');freeze=json.loads((root/'freeze.json').read_text())
assert checkpoint_identity(freeze['model'])==freeze['checkpoint_id']
result=evaluate(root/'manifest.json',freeze['model'],root/'evaluation','test','ml/artifacts/sn8_native_cpu_v2/baseline_model')
assert checkpoint_identity(freeze['model'])==freeze['checkpoint_id']
result.update({'dataset':'SpaceNet8 Germany_Training_Public','event':'Germany2021 floods; exact imagery capture dates unverified','assessment':'Frozen cross-event external spatial subset; small pilot, not an official competition benchmark','freeze':freeze,'evaluated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preparation_failures':json.loads((root/'failures.json').read_text()),'preparation':json.loads((root/'methodology.json').read_text()),'selection':json.loads((root/'selection.json').read_text()),'sources':json.loads((root/'sources.json').read_text()),'inference_failures':[]})
result['caveats']=['Six label-blind sampled tiles from one new event/acquisition; small convenience subset, not representative deployment accuracy','Checkpoint/config/threshold frozen before new labels; no tuning or re-selection based on these outcomes','Different event and continent from Louisiana training and development data','Only narrow annotated road corridors evaluated; not full-scene road extraction or routing accuracy','Four-source-pixel road buffers and uncorrected pre/post registration may introduce label noise','Exact capture dates unverified; source registry identifies Germany2021 flooding','No Helene accuracy claim; this result must not be substituted for unmeasured Swannanoa transfer']
for item in result['per_tile']:
 for metrics in item['metrics'].values():metrics['tn']=metrics['valid_pixels']-metrics['tp']-metrics['fp']-metrics['fn']
for metrics in result['metrics'].values():metrics['tn']=metrics['valid_pixels']-metrics['tp']-metrics['fp']-metrics['fn']
(root/'evaluation'/'evaluation.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ['dataset','tile_count','metrics','elapsed_seconds','preparation_failures','inference_failures']},indent=2))
