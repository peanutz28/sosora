"""Postmortem on reviewed train/dev data only; never opens the spent final data."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import torch
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

from ml.experiments.train_comparator import sample, logits
from ml.experiments.v3_models import load_candidate
from ml.vision.evaluate import binary_metrics
from ml.vision.provenance import checkpoint_identity
from ml.vision.tiled import tiled_probabilities
from scripts.ml.evaluate_road_tiles import aggregate

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'ml/artifacts/v3_experiment'
ORIGINAL = ROOT / 'docs/ml/evidence/v3_2026-10-18'
OUTPUT = ROOT / 'docs/ml/evidence/v3_diagnosis_2026-10-18'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2) + '\n')


def counts(mask):
    return {'dry': int((mask == 0).sum()), 'flood': int((mask == 1).sum())}


def summarize(records):
    grouped = {}
    for key in sorted({(r['split'], r['prefix']) for r in records}):
        subset = [r for r in records if (r['split'], r['prefix']) == key]
        combined = Counter()
        for row in subset:
            combined.update({k: v for k, v in row.items() if isinstance(v, int)})
        combined['source_tiles'] = len(subset)
        combined['crop_flood_fraction'] = combined['crop_flood'] / (combined['crop_flood'] + combined['crop_dry'])
        combined['full_flood_fraction'] = combined['full_flood'] / (combined['full_flood'] + combined['full_dry'])
        combined['supervised_crop_repeat_factor'] = (combined['crop_dry'] + combined['crop_flood']) / combined['unique_covered_supervised_pixels']
        grouped[' / '.join(key)] = dict(combined)
    return grouped


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / 'development_inference.json').exists():
        raise ValueError('Refusing to overwrite diagnostic inference evidence')
    manifest = DATA / 'reviewed_crop_manifest.json'
    approved = read(DATA / 'readiness.json')['approved_manifest_sha256']
    assert digest(manifest) == approved
    crops = read(manifest)
    # Membership guards precede every image/mask access. Only seal identifiers are read.
    sealed = set(read(DATA / 'protocol.json')['final_ids'])
    assert all(r['split'] in {'train', 'validation'} and r['source_image_id'] not in sealed for r in crops)
    parents = {r['source_image_id']: r for r in read(DATA / 'train_dev_manifest.json')}
    selected = {r['source_image_id'] for r in crops}
    assert selected <= parents.keys() and not selected & sealed
    selection = read(ORIGINAL / 'selection.json')
    assert digest(ROOT / selection['checkpoint']) == selection['checkpoint_sha256']
    assert checkpoint_identity(ROOT / 'ml/artifacts/sn8_native_cpu_v2/model') == selection['v2_checkpoint_id']
    by_parent = defaultdict(list)
    for row in crops:
        by_parent[row['source_image_id']].append(row)
    stats = []
    coverage_by_id = {}
    opened = []
    for ident in sorted(selected):
        parent = parents[ident]
        assert parent['split'] == by_parent[ident][0]['split']
        path = Path(parent['mask']).resolve()
        assert path == DATA / 'prepared' / (ident + '_mask.png')
        with Image.open(path) as source:
            mask = np.asarray(source).copy()
        opened.append(str(path.relative_to(ROOT)))
        coverage = np.zeros(mask.shape, dtype=bool)
        crop_counts = Counter()
        for row in by_parent[ident]:
            left, top, right, bottom = row['crop_pixel_bounds']
            values = counts(mask[top:bottom, left:right])
            assert values == {'dry': row['label_counts']['0'], 'flood': row['label_counts']['1']}
            coverage[top:bottom, left:right] = True
            crop_counts.update(values)
        full = counts(mask)
        stats.append({'source_image_id': ident, 'prefix': ident.rsplit('_', 2)[0], 'split': parent['split'],
                      'crops': len(by_parent[ident]), 'full_dry': full['dry'], 'full_flood': full['flood'],
                      'crop_dry': crop_counts['dry'], 'crop_flood': crop_counts['flood'],
                      'unique_covered_supervised_pixels': int((coverage & (mask != 255)).sum()),
                      'tile_pixels': int(mask.size)})
        if parent['split'] == 'validation':
            coverage_by_id[ident] = coverage
    save('sampling_audit.json', {'manifest_sha256': approved, 'per_tile': stats, 'by_split_and_capture': summarize(stats),
                                'scope': 'Reviewed train/dev parent masks only; no final imagery, masks or predictions opened.'})

    histories = {}
    for path in sorted((ORIGINAL / 'runs').glob('*/run.json')):
        run = read(path)
        complete = [r for r in run['history'] if r['complete'] and r['f1'] is not None]
        if complete:
            histories[path.parent.name] = {'selected_epoch': run['selected_epoch'], 'epoch_count': len(complete),
                'best_dev_f1': max(r['f1'] for r in complete), 'last_dev_f1': complete[-1]['f1'],
                'min_dev_f1': min(r['f1'] for r in complete),
                'largest_adjacent_dev_f1_change': max(abs(a['f1']-b['f1']) for a,b in zip(complete,complete[1:])),
                'source_sha256': digest(path)}
    save('training_history_audit.json', {'runs': histories, 'training_loss_recorded': False,
                                       'scope': 'Original development histories; no new training or checkpoint selection.'})

    torch.set_num_threads(2)
    dev = [parents[ident] for ident in sorted(selected) if parents[ident]['split'] == 'validation']
    assert len(dev) == 19 and all(r['source_image_id'] not in sealed for r in dev)
    result = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'device': 'cpu', 'threads': 2,
              'scope': 'Diagnostic only on the original reviewed development tiles. No model selection, threshold search, final-set access or promotion.',
              'manifest_sha256': approved, 'selection_sha256': digest(ORIGINAL / 'selection.json'), 'per_tile': [], 'models': {}}
    started = time.perf_counter()
    for role in ('v2', 'v3'):
        base = ROOT / 'ml/artifacts/sn8_native_cpu_v2' / ('model' if role == 'v2' else 'baseline_model')
        processor = SegformerImageProcessor.from_pretrained(base, local_files_only=True)
        model = (SegformerForSemanticSegmentation.from_pretrained(base, local_files_only=True).eval() if role == 'v2'
                 else load_candidate(selection['architecture'], ROOT / selection['checkpoint'], base))
        first_crop = next(row for row in crops if row['split'] == 'validation')
        manual, _ = sample(first_crop)
        with Image.open(first_crop['image']) as image:
            processed = processor(images=image, return_tensors='pt')['pixel_values'][0]
        with torch.inference_mode():
            manual_logits = logits(model, manual[None])
            processor_logits = logits(model, processed[None])
        result['models'][role] = {'parameters': sum(p.numel() for p in model.parameters()),
            'preprocessor_max_abs_input_difference': float((manual-processed).abs().max()),
            'preprocessor_max_abs_logit_difference': float((manual_logits-processor_logits).abs().max()),
            'batchnorm_modules': [name for name,m in model.named_modules() if isinstance(m,torch.nn.modules.batchnorm._BatchNorm)]}
        for row in dev:
            ident = row['source_image_id']
            image_path = Path(row['image']).resolve();mask_path = Path(row['mask']).resolve()
            assert image_path == DATA / 'prepared' / (ident+'.png') and ident not in sealed
            opened.append(str(image_path.relative_to(ROOT)))
            with Image.open(image_path) as image:
                probabilities = tiled_probabilities(model,processor,image,tile_size=256,stride=256)
            with Image.open(mask_path) as image:
                target = np.asarray(image).copy()
            prediction = probabilities.argmax(0)
            cropped = target.copy();cropped[~coverage_by_id[ident]] = 255
            item = {'model': role, 'source_image_id': ident, 'prefix': ident.rsplit('_',2)[0],
                    'full_tile': binary_metrics(prediction,target), 'unique_crop_coverage': binary_metrics(prediction,cropped)}
            result['per_tile'].append(item)
            with (OUTPUT / 'development_progress.jsonl').open('a') as stream:
                stream.write(json.dumps(item)+'\n')
            print('Development only: '+role+' '+ident,flush=True)
        del model,processor
    result['aggregate'] = {role: {scope: aggregate([r[scope] for r in result['per_tile'] if r['model']==role])
                                 for scope in ('full_tile','unique_crop_coverage')} for role in ('v2','v3')}
    result['by_capture'] = {prefix: {role: aggregate([r['full_tile'] for r in result['per_tile'] if r['prefix']==prefix and r['model']==role])
                                    for role in ('v2','v3')} for prefix in sorted({r['prefix'] for r in result['per_tile']})}
    result['elapsed_seconds'] = time.perf_counter()-started
    result['data_access'] = {'opened_parent_image_mask_paths': sorted(set(opened)), 'sealed_id_intersection': [],
                             'final_data_paths_opened': False, 'model_weights_changed': False, 'model_selection_changed': False}
    save('development_inference.json', result)
    print(json.dumps(result['aggregate']),flush=True)


if __name__ == '__main__':
    main()
