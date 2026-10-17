"""Offline native-resolution road crops; test rows are preserved verbatim.

Selection uses only each train/validation tile's existing labels, never test data.
No resize, interpolation, mask dilation, or relabeling is performed.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from PIL import Image


def select_windows(mask, size=256, limit=8, min_valid=64):
    if mask.ndim != 2 or not np.isin(mask, [0, 1, 255]).all():
        raise ValueError('Expected single-channel mask with 0, 1 and 255 labels')
    height, width = mask.shape
    if min(height, width) < size:
        raise ValueError('Source smaller than crop; padding is not permitted')
    # Quantized road-pixel centers provide candidates without privileging RGB appearance.
    ys, xs = np.nonzero(mask != 255)
    candidates = set()
    for y, x in zip(ys, xs):
        top = min(max((int(y) // 64) * 64 - size // 2, 0), height-size)
        left = min(max((int(x) // 64) * 64 - size // 2, 0), width-size)
        candidates.add((left, top, left+size, top+size))
    scored = []
    for box in sorted(candidates):
        left, top, right, bottom = box
        crop = mask[top:bottom, left:right]
        n0, n1 = int((crop == 0).sum()), int((crop == 1).sum())
        if n0+n1 >= min_valid:
            scored.append((box, n0, n1))
    selected = []
    # Alternate flooded-dominant and dry-dominant crops; use actual class counts,
    # not invented labels. Mixed tiles can supply both; single-class tiles cannot.
    for target in [1, 0] * limit:
        if len(selected) >= limit:
            break
        eligible = []
        for candidate in scored:
            box, n0, n1 = candidate
            if candidate in selected or (n1 >= n0) != (target == 1):
                continue
            x, y, r, b = box
            overlap = max((max(0, min(r, q[0][2])-max(x, q[0][0])) *
                           max(0, min(b, q[0][3])-max(y, q[0][1])) / (size*size)
                           for q in selected), default=0)
            if overlap > 0.5:
                continue
            eligible.append(candidate)
        if eligible:
            selected.append(min(eligible, key=lambda c: (-(c[1]+c[2]), c[0])))
    return selected


def build(manifest, output):
    source = Path(manifest)
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new or empty')
    output.mkdir(parents=True, exist_ok=True)
    rows = json.loads(source.read_text())
    result = []
    counts = Counter()
    class_counts = {'train': Counter(), 'validation': Counter()}
    for index, row in enumerate(rows):
        if row['split'] == 'test':
            result.append(dict(row))
            counts['test_original_tiles'] += 1
            continue
        if row['split'] not in {'train', 'validation'}:
            raise ValueError('Unknown split')
        with Image.open(row['image']) as image:
            rgb = np.asarray(image.convert('RGB'))
        with Image.open(row['mask']) as image:
            mask = np.asarray(image)
        if rgb.shape[:2] != mask.shape:
            raise ValueError('Image/mask shape mismatch')
        windows = select_windows(mask, limit=8 if row['split'] == 'train' else 6)
        if not windows:
            raise ValueError('No informative road crops in ' + row['image'])
        for number, (box, n0, n1) in enumerate(windows):
            left, top, right, bottom = box
            stem = f'{row["split"]}_{index:02d}_{number:02d}'
            image_path, mask_path = output/(stem+'.png'), output/(stem+'_mask.png')
            Image.fromarray(rgb[top:bottom, left:right]).save(image_path)
            Image.fromarray(mask[top:bottom, left:right]).save(mask_path)
            crop = dict(row, image=str(image_path), mask=str(mask_path),
                        parent_source_image_id=row.get('source_image_id', row['image']),
                        parent_image=row['image'], parent_mask=row['mask'],
                        crop_pixel_bounds=list(box), crop_size=[256, 256],
                        crop_method='native_resolution_label_centered_v1',
                        label_counts={'0': n0, '1': n1, '255': 256*256-n0-n1})
            # Parent bounds are not the geographic bounds of this crop.
            if 'bounds_epsg3857' in crop:
                crop['parent_bounds_epsg3857'] = crop.pop('bounds_epsg3857')
            result.append(crop)
            counts[row['split']+'_crops'] += 1
            class_counts[row['split']].update({'0': n0, '1': n1})
    methodology = {
        'source_manifest': str(source), 'method': 'native_resolution_label_centered_v1',
        'crop_size': [256, 256], 'candidate_center_grid_pixels': 64,
        'max_overlap_fraction_per_parent': 0.5, 'minimum_labeled_pixels': 64,
        'max_crops_per_parent': {'train': 8, 'validation': 6},
        'selection': 'alternate flood/dry-dominant candidates; maximize supervised pixels; deterministic coordinate ties',
        'labels': {'0': 'non_flooded_road', '1': 'flooded_road', '255': 'unknown_ignored'},
        'split_policy': 'preserve parent split and spatial_group; test rows copied verbatim, never opened or used for selection',
        'test_preprocessing': 'Existing trainer resizes unchanged full test tiles to 256; test performance is not directly comparable with native crop validation.',
        'limitations': ['tiny same-event pilot', 'overlapping crops are correlated; counts are sampled supervision, not unique pixels',
                       'class balance is constrained by available source labels', 'existing label alignment and corridor convention unchanged'],
        'counts': dict(counts), 'sampled_class_pixels': {k:dict(v) for k,v in class_counts.items()},
    }
    (output/'manifest.json').write_text(json.dumps(result, indent=2))
    (output/'methodology.json').write_text(json.dumps(methodology, indent=2))
    total_bytes = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
    if total_bytes >= 30*1024*1024:
        raise ValueError('Output exceeds 30 MiB budget')
    return dict(methodology, output_bytes=total_bytes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='ml/artifacts/sn8_pilot/manifest.json')
    parser.add_argument('--output', default='ml/artifacts/sn8_road_crops')
    args = parser.parse_args()
    print(json.dumps(build(args.manifest, args.output), indent=2))
