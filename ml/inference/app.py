import json
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ml.inference.schemas import PredictRequest, Prediction
from ml.vision.provenance import DEFAULT_MODEL, FLOOD_TASK, model_metadata, checkpoint_identity

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title='SOSora ML', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('ML_CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(','), allow_methods=['GET','POST'], allow_headers=['Content-Type'])

def images():
    path = Path(os.getenv('ML_IMAGE_MANIFEST', ROOT / 'data/manifests/images.json'))
    rows = json.loads(path.read_text()) if path.exists() else []
    for row in rows:
        row['path'] = str(ROOT / row['path'])
        if row.get('road_roi_path'):
            row['road_roi_path'] = str(ROOT / row['road_roi_path'])
    return rows

@app.get('/health')
def health():
    module = sys.modules.get('ml.vision.predict')
    loader = getattr(module, 'load_model', None)
    loaded = bool(loader and loader.cache_info().currsize)
    return {'status': 'ok', 'service': 'sosora-ml', 'vision_loaded': loaded, 'note': 'Liveness only; model loads on first prediction.'}

def served_metadata():
    module = sys.modules.get('ml.vision.predict')
    loader = getattr(module, 'load_model', None)
    if loader and loader.cache_info().currsize:
        _, model, _ = module.load_model()
        captured = getattr(model, '_sosora_provenance', None)
        if captured is not None:
            return {**captured, 'metadata_scope': 'loaded_model'}
    return {**model_metadata(os.getenv('VISION_MODEL', DEFAULT_MODEL), os.getenv('VISION_REVISION')),
            'metadata_scope': 'configured_model_not_loaded'}


def evaluation_metadata(path):
    identity = dict(model_id=None, checkpoint_id=None, run_id=None, task=None, identity_status='unverified')
    try:
        recorded = json.loads((path / 'run_metadata.json').read_text())
        identity.update({key: recorded.get(key) for key in identity if key != 'identity_status'})
        metric_identity = json.loads((path / 'final_metrics.json').read_text()).get('provenance', {})
        metric_matches = all(identity.get(k) and identity.get(k) == metric_identity.get(k)
                             for k in ('model_id', 'checkpoint_id', 'run_id', 'task'))
        actual = checkpoint_identity(path / 'model')
        if metric_matches and actual and identity['checkpoint_id'] == actual and all(identity.get(k) for k in ('model_id', 'run_id', 'task')):
            identity['identity_status'] = 'verified'
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return identity


@app.get('/ml/model-info')
def model_info():
    result = metrics()
    served = result['served_model']
    return {**served, 'served_model': served, 'inference_mode': 'real', 'status': 'configured',
            'metadata_scope': served.get('metadata_scope', 'configured_model_not_loaded'),
            'flooded_road_capable': served.get('task') == FLOOD_TASK,
            'metrics_status': result['status'],
            'metrics_apply_to_served_model': result['metrics_apply_to_served_model'],
            'evaluated_model': result['evaluated_model'], 'contract': '/openapi.json'}

@app.get('/ml/images')
def list_images():
    return [{k:v for k,v in row.items() if k not in {'path', 'road_roi_path'}} for row in images()]

@app.post('/ml/predict', response_model=Prediction)
def predict(request: PredictRequest):
    entry = next((r for r in images() if r['image_id'] == request.image_id), None)
    if entry is None:
        raise HTTPException(404, 'Unknown image_id; see /ml/images')
    if not Path(entry['path']).is_file():
        raise HTTPException(503, 'Registered image not downloaded')
    from ml.vision.predict import predict as run
    try:
        return run(entry, request.threshold)
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Vision resource unavailable; inspect server logs') from exc

@app.get('/ml/metrics')
def metrics():
    path = Path(os.getenv('ML_METRICS_PATH', ROOT / 'ml/artifacts/sn8_pilot_run'))
    served = served_metadata()
    evaluated = evaluation_metadata(path)
    final_path = path / 'final_metrics.json'
    final = json.loads(final_path.read_text()) if final_path.is_file() else None
    available = final is not None and final.get('status') != 'not_evaluated'
    baseline_path = path / 'baseline_metrics.json'
    baseline = json.loads(baseline_path.read_text()) if baseline_path.is_file() else None
    applies = (available and served.get('identity_status') == 'verified'
               and evaluated.get('identity_status') == 'verified'
               and all(served.get(k) == evaluated.get(k) and served.get(k)
                       for k in ('model_id', 'checkpoint_id', 'run_id', 'task')))
    provenance = dict(served_model=served, evaluated_model=evaluated,
                      metrics_apply_to_served_model=bool(applies))
    if available:
        return {**provenance, 'status': 'pilot_evaluated',
                'baseline': baseline,
                'fine_tuned': final,
                'evaluation': final.get('evaluation'),
                'limitations': (final.get('evaluation') or {}).get('caveats', [
                                'Four held-out tiles from same event; not representative deployment accuracy',
                                'Baseline is a pretrained backbone with a random binary head',
                                'Legacy evaluation only on labeled road corridors at 256px; residual registration errors possible']) + [
                                'Metrics apply to served predictions only when verified checkpoint, run, model and task identities match']}
    return {**provenance, 'status': 'not_evaluated', 'baseline': baseline, 'fine_tuned': None,
            'reason': (final or {}).get('reason', 'No held-out evaluation completed')}

@app.get('/ml/llm-health')
def llm_health():
    from ml.inference.incident import llm_configuration
    config = llm_configuration()
    return {**config, 'status': 'configured_unverified' if config['configured'] else 'not_configured'}

from ml.inference.incident import router
app.include_router(router)
