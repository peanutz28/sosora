"""Offline model identities shared by training, API metadata and inference."""
import hashlib
import json
from pathlib import Path

DEFAULT_MODEL = 'nvidia/segformer-b0-finetuned-ade-512-512'
DEFAULT_REVISION = '489d5cd81a0b59fab9b7ea758d3548ebe99677da'
FLOOD_TASK = 'flood_state_on_road_corridors'
ADE_TASK = 'ade20k_scene_segmentation'


def checkpoint_identity(path):
    """Hash config, preprocessing and weight content, excluding mutable run metadata."""
    path = Path(path)
    config = path / 'config.json'
    weights = sorted(set(path.glob('*.safetensors')) | set(path.glob('pytorch_model*.bin')))
    if not config.is_file() or not weights:
        return None
    digest = hashlib.sha256()
    files = [config]
    if (path / 'preprocessor_config.json').is_file():
        files.append(path / 'preprocessor_config.json')
    for file in files + weights:
        digest.update(file.name.encode())
        digest.update(b'\0')
        with file.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        digest.update(b'\0')
    return 'sha256:' + digest.hexdigest()


def _read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def model_metadata(model_id, revision=None):
    """Inspect local files only; unknown or legacy identity cannot establish a match."""
    model_id = str(model_id)
    path = Path(model_id)
    if path.is_dir():
        config = _read_json(path / 'config.json')
        metadata = _read_json(path / 'run_metadata.json')
        raw_labels = config.get('id2label', {})
        labels = {str(k): str(v) for k, v in raw_labels.items()} if isinstance(raw_labels, dict) else {}
        flooded = any(v.lower().replace(' ', '_').replace('-', '_') in {'flooded_road', 'road_flooded'} for v in labels.values())
        fingerprint = checkpoint_identity(path)
        verified = bool(fingerprint and metadata.get('checkpoint_id') == fingerprint and
                        all(metadata.get(k) for k in ('model_id', 'run_id', 'task')))
        return {
            'model_id': metadata.get('model_id', model_id) if verified else model_id,
            'checkpoint_id': fingerprint,
            'run_id': metadata.get('run_id') if verified else None,
            'task': metadata.get('task') if verified else (FLOOD_TASK if flooded else 'unknown'),
            'requires_road_roi': bool(flooded or config.get('requires_road_roi') or metadata.get('requires_road_roi') or metadata.get('task') == FLOOD_TASK),
            'label_map': labels,
            'native_tile_size': config.get('sosora_tile_size'),
            'identity_status': 'verified' if verified else 'legacy_unverified',
        }
    if model_id == DEFAULT_MODEL:
        revision = revision or DEFAULT_REVISION
        pinned = len(revision) == 40 and all(c in '0123456789abcdef' for c in revision.lower())
        return {'model_id': model_id, 'checkpoint_id': model_id + '@' + revision,
                'run_id': None, 'task': ADE_TASK, 'requires_road_roi': False,
                'label_map': {}, 'identity_status': 'verified' if pinned else 'unverified_revision'}
    return {'model_id': model_id, 'checkpoint_id': model_id + '@' + revision if revision else None,
            'run_id': None, 'task': 'unknown', 'requires_road_roi': True,
            'label_map': {}, 'identity_status': 'unverified'}
