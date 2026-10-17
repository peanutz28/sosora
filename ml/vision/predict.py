"""Real SegFormer inference. Labels are never promoted to road closure decisions."""
import os
import time
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom
import torch
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

DEFAULT_MODEL = 'nvidia/segformer-b0-finetuned-ade-512-512'

@lru_cache(maxsize=1)
def load_model():
    model_id = os.getenv('VISION_MODEL', DEFAULT_MODEL)
    revision = os.getenv('VISION_REVISION', '489d5cd81a0b59fab9b7ea758d3548ebe99677da' if model_id == DEFAULT_MODEL else 'main')
    model = SegformerForSemanticSegmentation.from_pretrained(model_id, revision=revision)
    model.eval()
    from ml.vision.provenance import model_metadata
    model._sosora_provenance = model_metadata(model_id, revision=getattr(model.config, '_commit_hash', None) or revision)
    processor = SegformerImageProcessor.from_pretrained(model_id, revision=revision)
    return model_id, model, processor

def _normalize_label(name):
    return str(name).strip().lower().replace('-', '_').replace(' ', '_')


def _requires_road_roi(model, provenance):
    labels = {_normalize_label(name) for name in model.config.id2label.values()}
    return (bool(provenance.get('requires_road_roi'))
            or bool(getattr(model.config, 'requires_road_roi', False))
            or bool((getattr(model.config, 'task_metadata', None) or {}).get('requires_road_roi'))
            or bool(labels & {'flooded_road', 'road_flooded', 'non_flooded_road', 'road_non_flooded'}))


def _road_roi(path, valid):
    try:
        with Image.open(path) as image:
            roi = np.asarray(image)
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError('Road ROI must be an existing readable single-channel mask') from exc
    if roi.ndim != 2:
        raise ValueError('Road ROI must be single-channel')
    if roi.shape != valid.shape:
        raise ValueError('Road ROI shape mismatch')
    if not np.isfinite(roi).all():
        raise ValueError('Road ROI must contain finite binary values')
    values = set(np.unique(roi).tolist())
    if not (values <= {0, 1} or values <= {0, 255}):
        raise ValueError('Road ROI must be binary (0/1 or 0/255)')
    roi = roi > 0
    if not np.any(roi & valid):
        raise ValueError('Road ROI must intersect valid image data')
    return roi

def predict(entry, threshold):
    start = time.perf_counter()
    model_id, model, processor = load_model()
    from ml.vision.provenance import model_metadata
    provenance = getattr(model, '_sosora_provenance', None)
    if provenance is None:
        provenance = model_metadata(model_id, revision=getattr(model.config, '_commit_hash', None))
    provenance = dict(provenance)
    provenance['label_map'] = {str(k): str(v) for k, v in model.config.id2label.items()}
    provenance['requires_road_roi'] = _requires_road_roi(model, provenance)
    if provenance['requires_road_roi'] and not entry.get('road_roi_path'):
        raise ValueError('Flood-road inference requires road_roi_path')
    with rasterio.open(entry['path']) as src:
        rgb = np.moveaxis(src.read([1, 2, 3]), 0, -1)
        if rgb.dtype != np.uint8:
            raise ValueError('Expected uint8 RGB input; prepare radiometry explicitly')
        valid = src.dataset_mask() > 0
        width, height, crs, affine = src.width, src.height, src.crs, src.transform
    if entry.get('road_roi_path'):
        valid &= _road_roi(entry['road_roi_path'], valid)
    image = Image.fromarray(rgb)
    tile_size = getattr(model.config, 'sosora_tile_size', None)
    if tile_size:
        from ml.vision.tiled import tiled_probabilities
        probabilities = tiled_probabilities(model, processor, image, tile_size=int(tile_size))
        provenance['native_tile_size'] = int(tile_size)
    else:
        with torch.inference_mode():
            logits = model(**processor(images=image, return_tensors='pt')).logits
            logits = torch.nn.functional.interpolate(logits, size=(height, width), mode='bilinear', align_corners=False)
            probabilities = logits.softmax(dim=1)[0].numpy()
    classes = probabilities.argmax(axis=0)
    detections = []
    labels = {'road', 'water', 'river', 'bridge', 'road flooded', 'road non-flooded', 'flooded_road', 'non_flooded_road'}
    for label_id, name in model.config.id2label.items():
        normalized = _normalize_label(name)
        if normalized not in {_normalize_label(label) for label in labels}:
            continue
        label_id = int(label_id)
        mask = ((classes == label_id) & (probabilities[label_id] >= threshold) & valid).astype('uint8')
        for geometry, value in shapes(mask, mask=mask.astype(bool), transform=affine if crs else rasterio.Affine.identity()):
            if not value:
                continue
            # Pixel confidence for this connected polygon, including holes.
            from rasterio.features import geometry_mask
            component = geometry_mask([geometry], (height, width), affine if crs else rasterio.Affine.identity(), invert=True)
            score = float(probabilities[label_id][component & mask.astype(bool)].mean())
            if crs:
                geometry = transform_geom(crs, 'EPSG:4326', geometry)
            detections.append({'id': f'prediction_{len(detections):04d}', 'class': {'road_flooded': 'flooded_road', 'road_non_flooded': 'non_flooded_road'}.get(normalized, normalized), 'confidence': score, 'geometry': geometry, 'road_segment_ids': [], 'review_status': 'unverified'})
    return dict(image_id=entry['image_id'], model_provenance=provenance, model_version=model_id + '@' + (getattr(model.config, '_commit_hash', None) or 'local'), inference_mode='real', crs='EPSG:4326' if crs else 'PIXEL', image_width=width, image_height=height, source={k:v for k,v in entry.items() if k not in {'path', 'road_roi_path'}}, detections=detections, latency_ms=(time.perf_counter()-start)*1000, warnings=['Unverified model predictions; not authoritative road closures.', 'ADE20K baseline has no flooded-road class.'] if model_id == DEFAULT_MODEL else ['Unverified transfer predictions; validate target-domain performance.'])
