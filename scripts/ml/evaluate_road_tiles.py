"""Offline native-resolution road evaluation; held-out test requires --split test."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image
import torch
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor
from ml.vision.evaluate import binary_metrics
from ml.vision.provenance import model_metadata
from ml.vision.tiled import tiled_probabilities


def load_local(model_path):
    if not Path(model_path).is_dir():
        raise ValueError('Model must be an existing local checkpoint directory')
    model = SegformerForSemanticSegmentation.from_pretrained(model_path, local_files_only=True).to('cpu').eval()
    labels = {int(k): str(v).lower().replace('-', '_').replace(' ', '_') for k,v in model.config.id2label.items()}
    if labels.get(1) not in {'flooded_road', 'road_flooded'} or len(labels) != 2:
        raise ValueError('Evaluation requires binary flood checkpoint with class 1 flooded road')
    processor = SegformerImageProcessor.from_pretrained(model_path, local_files_only=True)
    return model, processor


def aggregate(metrics):
    counts = {key: sum(m[key] for m in metrics) for key in ['tp', 'fp', 'fn', 'valid_pixels']}
    tp,fp,fn = counts['tp'],counts['fp'],counts['fn']
    for key,a,b in [('iou',tp,tp+fp+fn),('precision',tp,tp+fp),('recall',tp,tp+fn),('f1',2*tp,2*tp+fp+fn)]:
        counts[key] = a/b if b else None
    return counts


def evaluate(manifest, model_path, output, split='validation', baseline_model=None,
             loader=load_local, infer=tiled_probabilities):
    if split not in {'validation', 'test'}:
        raise ValueError('Split must be validation or test')
    output = Path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output must be a new or empty directory')
    rows = json.loads(Path(manifest).read_text())
    selected = [r for r in rows if r['split'] == split]
    if not selected:
        raise ValueError('No tiles for requested split')
    if any(r.get('crop_pixel_bounds') for r in selected):
        raise ValueError('Use original full-tile manifest, not crop manifest')
    group_splits = {}
    for row in rows:
        group = row['spatial_group']
        if group in group_splits and group_splits[group] != row['split']:
            raise ValueError('Spatial group leakage')
        group_splits[group] = row['split']
    torch.set_num_threads(2)
    start = time.perf_counter()
    model_paths = {'tuned': model_path}
    if baseline_model is not None:
        model_paths['baseline'] = baseline_model
    identities = {name:model_metadata(path) for name,path in model_paths.items()}
    # Keep only a single model and tile probability array resident at a time.
    per_tile = [dict(source_image_id=r.get('source_image_id',r['image']), spatial_group=r['spatial_group'],
                     image=r['image'], mask=r['mask'], metrics={}) for r in selected]
    for name, path in model_paths.items():
        model, processor = loader(path)
        for item, row in zip(per_tile, selected):
            tile_start = time.perf_counter()
            with Image.open(row['mask']) as mask_image:
                target = np.asarray(mask_image)
            if target.ndim != 2 or not np.isin(target, [0,1,255]).all() or not np.any(target != 255):
                raise ValueError('Expected nonempty binary road labels with unknown=255')
            with Image.open(row['image']) as image:
                if image.size != (target.shape[1], target.shape[0]):
                    raise ValueError('Image/mask shape mismatch')
                probabilities = infer(model, processor, image)
            if probabilities.shape != (2, *target.shape) or not np.isfinite(probabilities).all():
                raise ValueError('Native probability shape/values invalid')
            item['metrics'][name] = binary_metrics(probabilities.argmax(0), target)
            item.setdefault('inference_seconds', {})[name] = time.perf_counter()-tile_start
            item['native_size'] = [target.shape[1], target.shape[0]]
            if name == 'tuned':
                item['metrics']['all_positive'] = binary_metrics(np.ones_like(target), target)
                item['metrics']['all_negative'] = binary_metrics(np.zeros_like(target), target)
            del probabilities, target
        del model, processor
    names = list(model_paths) + ['all_positive', 'all_negative']
    result = {
        'split': split, 'scale': 'original_native_resolution', 'manifest': str(manifest),
        'tile_count': len(selected), 'tile_size': 256, 'stride': 256,
        'decision': 'argmax across binary classes; no threshold tuning',
        'support': 'Identical original mask pixels labeled 0 or 1 for every model/control; 255 ignored',
        'provenance': identities['tuned'], 'model_provenance': identities,
        'metrics': {name:aggregate([r['metrics'][name] for r in per_tile]) for name in names},
        'per_tile': per_tile, 'elapsed_seconds': time.perf_counter()-start,
        'caveats': ['Tiny same-event pilot; not event-level generalization evidence',
                    'Corridor labels use existing reference-line buffers, not full-scene flood truth',
                    'Residual image/label registration errors remain uncorrected',
                    'Native tiled evaluation differs from earlier 256px full-tile resized evaluation',
                    'Validation may inform model development; explicit test evaluation is reserved for final assessment'],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output/'evaluation.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--baseline-model')
    parser.add_argument('--output', required=True)
    parser.add_argument('--split', choices=['validation','test'], default='validation')
    args = parser.parse_args()
    result = evaluate(args.manifest,args.model,args.output,args.split,args.baseline_model)
    print(json.dumps({k:result[k] for k in ['split','tile_count','metrics','elapsed_seconds']}, indent=2))
