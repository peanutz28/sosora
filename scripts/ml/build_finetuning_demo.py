"""Recreate validation-only before/after assets from saved checkpoints. Never trains."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scripts.ml.evaluate_road_tiles import load_local
from ml.vision.tiled import tiled_probabilities
from ml.vision.evaluate import binary_metrics
from ml.vision.provenance import checkpoint_identity

ROOT = Path(__file__).resolve().parents[2]
COLORS = {0: (103, 219, 173, 230), 1: (255, 120, 92, 230)}


def class_overlay(classes, support):
    if classes.shape != support.shape or not np.isin(classes[support], [0, 1]).all():
        raise ValueError('Expected aligned binary classes and support')
    rgba = np.zeros((*classes.shape, 4), dtype=np.uint8)
    for label, color in COLORS.items():
        rgba[support & (classes == label)] = color
    return rgba


def verify_counts(actual, saved):
    if any(actual[key] != saved[key] for key in ('tp', 'fp', 'fn', 'valid_pixels')):
        raise ValueError('Generated prediction disagrees with saved validation evaluation')


def build(output):
    import torch
    torch.set_num_threads(2)
    validation = json.loads((ROOT/'ml/artifacts/sn8_native_cpu_v2_validation/evaluation.json').read_text())
    external = json.loads((ROOT/'docs/ml/evidence/frozen_external/evaluation.json').read_text())
    config = json.loads((ROOT/'ml/artifacts/sn8_native_cpu_v2/evaluation_config.json').read_text())
    registrations = json.loads((ROOT/'data/manifests/native_demo.json').read_text())
    model_paths = {'baseline': ROOT/'ml/artifacts/sn8_native_cpu_v2/baseline_model',
                   'tuned': ROOT/'ml/artifacts/sn8_native_cpu_v2/model'}
    hashes = {name: checkpoint_identity(path) for name, path in model_paths.items()}
    for name, digest in hashes.items():
        if digest != external['model_provenance'][name]['checkpoint_id']:
            raise ValueError('Checkpoint does not match frozen evaluation')
    if json.loads((model_paths['baseline']/'preprocessor_config.json').read_text()) != json.loads((model_paths['tuned']/'preprocessor_config.json').read_text()):
        raise ValueError('Before/after processors must match')
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    scenes = []
    for index, item in enumerate(validation['per_tile']):
        row = next(r for r in registrations if r.get('source_image_id') == item['source_image_id'] and r.get('split') == 'validation')
        rgb = Image.open(ROOT/item['image']).convert('RGB')
        target = np.asarray(Image.open(ROOT/item['mask']))
        roi = np.asarray(Image.open(ROOT/row['road_roi_path']))
        if target.shape != roi.shape or rgb.size != (roi.shape[1], roi.shape[0]) or not np.isin(roi, [0, 1, 255]).all():
            raise ValueError('Image, labels and independent road ROI must align')
        roi = roi > 0
        prefix = f'validation-{index}'
        rgb.save(output/(prefix+'-source.jpg'), quality=95)
        Image.fromarray(class_overlay(target, target != 255)).save(output/(prefix+'-reference.png'))
        binary = Image.fromarray(roi.astype(np.uint8)*255)
        border = np.asarray(binary.filter(ImageFilter.MaxFilter(3))) != np.asarray(binary.filter(ImageFilter.MinFilter(3)))
        outline = np.zeros((*roi.shape, 4), dtype=np.uint8); outline[border] = (255, 255, 255, 170)
        Image.fromarray(outline).save(output/(prefix+'-roi.png'))
        scenes.append({'id': item['source_image_id'], 'prefix': prefix, 'split': 'validation',
                       'size': list(rgb.size), 'metrics': item['metrics'],
                       'roi_labeled_coverage': int((roi & (target != 255)).sum()),
                       'source_url': row['source_url']})
    for name, path in model_paths.items():
        model, processor = load_local(path)
        for scene, item in zip(scenes, validation['per_tile']):
            rgb = Image.open(ROOT/item['image']).convert('RGB')
            target = np.asarray(Image.open(ROOT/item['mask']))
            row = next(r for r in registrations if r.get('source_image_id') == scene['id'] and r.get('split') == 'validation')
            roi = np.asarray(Image.open(ROOT/row['road_roi_path'])) > 0
            prediction = tiled_probabilities(model, processor, rgb).argmax(0)
            verify_counts(binary_metrics(prediction, target), item['metrics'][name])
            Image.fromarray(class_overlay(prediction, roi)).save(output/(scene['prefix']+'-'+name+'.png'))
        del model, processor
    if hashes != {name: checkpoint_identity(path) for name, path in model_paths.items()}:
        raise ValueError('Checkpoint changed during asset generation')
    payload = {'scenes': scenes, 'validation_metrics': validation['metrics'],
               'external_metrics': external['metrics'], 'external_per_tile': external['per_tile'],
               'hashes': hashes, 'selected_epoch': config['selected_epoch'], 'epochs': config['epochs'],
               'history': config['history'], 'experiment': config['provenance']}
    (output/'experiment.json').write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps({'validation_tiles': len(scenes), 'saved_confusion_counts_reproduced': True, 'checkpoint_hashes': hashes}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/ml/viewer/assets/finetuning')
    build(parser.parse_args().output)
