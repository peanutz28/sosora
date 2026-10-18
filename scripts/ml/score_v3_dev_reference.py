"""Score the unchanged native v2 on the reviewed dev crops; no final data access."""
from datetime import datetime,timezone
import json
from pathlib import Path
import torch
from ml.experiments.train_comparator import make_model,sample,logits
from ml.experiments.v3_protocol import ROOT,MANIFEST_SHA256,preflight
from ml.vision.evaluate import binary_metrics
from ml.vision.provenance import checkpoint_identity
from scripts.ml.evaluate_road_tiles import aggregate


def main():
    preflight();torch.set_num_threads(2)
    output=ROOT/'docs/ml/evidence/v3_2026-10-18/v2_dev.json'
    if output.exists():raise ValueError('Refusing to overwrite reference evidence')
    path=ROOT/'ml/artifacts/sn8_native_cpu_v2/model';identity=checkpoint_identity(path)
    model=make_model('segformer',str(path)).eval()
    rows=json.loads((ROOT/'ml/artifacts/v3_experiment/reviewed_crop_manifest.json').read_text())
    results=[]
    with torch.inference_mode():
        for row in rows:
            if row['split']!='validation':continue
            x,y=sample(row);prediction=logits(model,x.unsqueeze(0)).argmax(1)[0].numpy()
            results.append({'source_image_id':row['source_image_id'],'image':row['image'],
                'metrics':binary_metrics(prediction,y.numpy())})
    metrics=aggregate([row['metrics'] for row in results])
    metrics['tn']=metrics['valid_pixels']-metrics['tp']-metrics['fp']-metrics['fn']
    if checkpoint_identity(path)!=identity:raise ValueError('v2 identity changed')
    result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'model':'native_v2',
        'checkpoint_id':identity,'parameters':sum(p.numel() for p in model.parameters()),
        'manifest_sha256':MANIFEST_SHA256,'metrics':metrics,'crop_count':len(results),
        'source_tile_count':len({row['source_image_id'] for row in results}),'per_crop':results,
        'support':'Same99 reviewed dev crops used by the runner; overlapping crops are correlated, not independent tiles.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('model','metrics','crop_count','source_tile_count')}))


if __name__=='__main__':main()
