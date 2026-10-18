"""Exercise real SOSora inference and save reviewable prediction artifacts.

Run from repository root: ml/.venv312/bin/python scripts/ml/demo_smoke.py --help
No model downloads, training, service starts, or checkpoint changes are performed.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / 'data/manifests/images.json'


def geojson(prediction):
    """Export georeferenced detections; refuse to label pixel coordinates as WGS84."""
    if prediction['crs'] != 'EPSG:4326':
        raise ValueError('GeoJSON export requires EPSG:4326 predictions')
    return {'type': 'FeatureCollection',
            'image_id': prediction['image_id'],
            'model_provenance': prediction.get('model_provenance'),
            'warnings': prediction.get('warnings', []),
            'features': [{'type': 'Feature', 'geometry': row['geometry'],
                          'properties': {key: value for key, value in row.items() if key != 'geometry'}}
                         for row in prediction['detections']]}


def overlay(prediction, source_path, output_path):
    """Rasterize WGS84 result polygons back onto their original georeferenced RGB."""
    import numpy as np
    from PIL import Image
    import rasterio
    from rasterio.features import rasterize
    from rasterio.warp import transform_geom

    with rasterio.open(source_path) as src:
        if src.crs is None:
            raise ValueError('Overlay source requires a georeferenced raster')
        rgb = np.moveaxis(src.read([1, 2, 3]), 0, -1)
        if rgb.dtype != np.uint8:
            raise ValueError('Overlay requires prepared uint8 RGB imagery')
        if (src.width, src.height) != (prediction['image_width'], prediction['image_height']):
            raise ValueError('Source dimensions disagree with prediction')
        if prediction['crs'] != 'EPSG:4326':
            raise ValueError('Overlay requires EPSG:4326 predictions')
        pixels = rgb.astype(np.float32)
        colors = {'flooded_road': (255, 48, 64), 'non_flooded_road': (40, 220, 100),
                  'road': (255, 210, 40), 'water': (30, 160, 255),
                  'river': (30, 160, 255), 'bridge': (200, 100, 240)}
        for row in prediction['detections']:
            geometry = transform_geom('EPSG:4326', src.crs, row['geometry'])
            mask = rasterize([(geometry, 1)], out_shape=(src.height, src.width),
                             transform=src.transform, fill=0, dtype='uint8').astype(bool)
            color = np.array(colors.get(row['class'], (240, 140, 50)), dtype=np.float32)
            pixels[mask] = pixels[mask] * .55 + color * .45
    Image.fromarray(np.clip(pixels, 0, 255).astype('uint8')).save(output_path, quality=92)


def checked_json(response):
    response.raise_for_status()
    return response.json()


def run_smoke(client, image_id, output, manifest, threshold=.65):
    """Client may be TestClient or httpx.Client; requests always use the real API."""
    output = Path(output)
    if output.exists():
        raise ValueError('Output must be a new directory; existing evidence is never overwritten')
    rows = json.loads(Path(manifest).read_text())
    local = next((row for row in rows if row['image_id'] == image_id), None)
    if local is None:
        raise ValueError('Image ID is absent from local source manifest')
    source_path = Path(local['path'])
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    if not source_path.is_file():
        raise ValueError('Registered source image is not available locally')
    health = checked_json(client.get('/health'))
    images = checked_json(client.get('/ml/images'))
    if not any(row['image_id'] == image_id for row in images):
        raise ValueError('Image ID is not allowlisted by the API')
    info = checked_json(client.get('/ml/model-info'))
    prediction = checked_json(client.post('/ml/predict', json={'image_id': image_id, 'threshold': threshold}))
    if prediction.get('inference_mode') != 'real':
        raise ValueError('Smoke runner requires real inference')
    if prediction.get('image_id') != image_id:
        raise ValueError('API returned a different image ID')
    metrics = checked_json(client.get('/ml/metrics'))
    features = geojson(prediction)
    output.mkdir(parents=True, exist_ok=False)
    # Retain raw responses even if rendering fails, to make failures diagnosable.
    for name, value in [('health', health), ('images', images), ('model_info', info),
                        ('prediction', prediction), ('metrics', metrics), ('detections', features)]:
        (output / (name + ('.geojson' if name == 'detections' else '.json'))).write_text(json.dumps(value, indent=2))
    overlay(prediction, source_path, output / 'overlay.jpg')
    summary = {'status': 'passed', 'image_id': image_id, 'threshold': threshold,
               'inference_mode': prediction['inference_mode'],
               'model_provenance': prediction.get('model_provenance'),
               'detections': len(prediction['detections']),
               'metrics_apply_to_served_model': metrics.get('metrics_apply_to_served_model', False),
               'warnings': prediction.get('warnings', []),
               'overlay_colors': {'flooded_road': 'red', 'non_flooded_road': 'green',
                                  'road': 'yellow', 'water_or_river': 'blue', 'bridge': 'purple'},
               'review_status': 'unverified',
               'interpretation': 'Segmentation predictions are not authoritative road closures.'}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--output', required=True, help='New evidence directory; must not exist')
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST,
                        help='Local source manifest matching API image registrations')
    parser.add_argument('--threshold', type=float, default=.65)
    parser.add_argument('--model', help='Local checkpoint or cached model ID; in-process mode only')
    parser.add_argument('--metrics-path', help='Evaluation directory; in-process mode only')
    parser.add_argument('--url', help='Existing API URL; does not start or reconfigure its service')
    args = parser.parse_args(argv)
    if not 0 <= args.threshold <= 1:
        parser.error('--threshold must be between 0 and 1')
    if args.url and (args.model or args.metrics_path):
        parser.error('--model/--metrics-path configure only in-process mode')
    if args.url:
        import httpx
        with httpx.Client(base_url=args.url.rstrip('/'), timeout=300) as client:
            summary = run_smoke(client, args.image_id, args.output, args.manifest, args.threshold)
    else:
        os.environ.setdefault('HF_HOME', str(ROOT / 'ml/.cache/huggingface'))
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['ML_IMAGE_MANIFEST'] = str(args.manifest.resolve())
        if args.model:
            os.environ['VISION_MODEL'] = args.model
        else:
            os.environ.pop('VISION_MODEL', None)
            os.environ.pop('VISION_REVISION', None)
        if args.metrics_path:
            os.environ['ML_METRICS_PATH'] = args.metrics_path
        sys.path.insert(0, str(ROOT))
        from fastapi.testclient import TestClient
        from ml.inference.app import app
        with TestClient(app) as client:
            summary = run_smoke(client, args.image_id, args.output, args.manifest, args.threshold)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
