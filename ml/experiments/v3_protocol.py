"""Immutable V3 split identities and committed-selection/final-access safeguards."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SHA256 = '6d406a00b2247d369fce27caa9d96c3236ba3652136d7a32c1ebbd9aa9b03ebd'
PROTOCOL_SHA256 = 'd557eb517e128b3d1a7a3d921850fbbc0d3fa0091ad046436fc42d156cf49ade'
FINAL_IDS_SHA256 = 'd18eab0a9ff977400cfbc96158a2d28da0928f166236185ec7a5e09d81030ffc'
SELECTION_DEADLINE = datetime(2026, 10, 18, 9, 30, tzinfo=timezone.utc)
FINAL_DEADLINE = datetime(2026, 10, 18, 10, 25, tzinfo=timezone.utc)
FREEZE_DEADLINE = datetime(2026, 10, 18, 11, 0, tzinfo=timezone.utc)
FROZEN_SOURCES = ('scripts/ml/run_v3_final.py', 'scripts/ml/prepare_v3_experiment.py',
    'ml/vision/evaluate.py', 'ml/vision/tiled.py', 'ml/experiments/train_comparator.py',
    'ml/experiments/v3_models.py')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def preflight(root=ROOT):
    folder = root/'ml/artifacts/v3_experiment'
    protocol = json.loads((folder/'protocol.json').read_text())
    seal = json.loads((folder/'final_seal.json').read_text())
    readiness = json.loads((folder/'readiness.json').read_text())
    if protocol.get('protocol_sha256') != PROTOCOL_SHA256 or canonical({k:v for k,v in protocol.items() if k!='protocol_sha256'}) != PROTOCOL_SHA256:
        raise ValueError('Frozen V3 protocol mismatch')
    if canonical(protocol['final_ids']) != FINAL_IDS_SHA256 or len(protocol['final_ids']) != 38:
        raise ValueError('Sealed final IDs changed')
    if seal['protocol_sha256'] != PROTOCOL_SHA256 or seal['final_ids_sha256'] != FINAL_IDS_SHA256 or seal['final_count'] != 38:
        raise ValueError('Final seal mismatch')
    manifest = folder/'reviewed_crop_manifest.json'
    if sha256(manifest) != MANIFEST_SHA256 or readiness.get('approved_manifest_sha256') != MANIFEST_SHA256 or readiness.get('status') != 'manual_quality_review_completed':
        raise ValueError('Reviewed manifest/quality approval mismatch')
    rows = json.loads(manifest.read_text())
    if any(row['split'] not in {'train','validation'} or row['source_image_id'] in protocol['final_ids'] for row in rows):
        raise ValueError('Final/test row in development manifest')
    if len({row['source_image_id'] for row in rows if row['split']=='validation'}) != 19:
        raise ValueError('Development tile membership changed')
    return protocol


def committed_selection(path, root=ROOT):
    """Called before downloading/opening final pixels or annotations."""
    if datetime.now(timezone.utc) >= FINAL_DEADLINE:
        raise ValueError('Final evaluation deadline reached; drop unfinished work')
    path = Path(path).resolve()
    relative = path.relative_to(root.resolve()).as_posix()
    branch = subprocess.run(['git','symbolic-ref','--short','HEAD'], cwd=root,
                            capture_output=True,text=True,check=True).stdout.strip()
    if branch != 'integration':
        raise ValueError('Selection must be committed to integration')
    saved = subprocess.run(['git','show','HEAD:'+relative],cwd=root,capture_output=True)
    if saved.returncode or saved.stdout != path.read_bytes():
        raise ValueError('selection.json must be committed unchanged before final access')
    commit = subprocess.run(['git','log','-1','--format=%H %ct','--',relative],cwd=root,
                            capture_output=True,text=True,check=True).stdout.strip().split()
    if len(commit)!=2 or int(commit[1]) > SELECTION_DEADLINE.timestamp():
        raise ValueError('Selection was not committed before the selection deadline')
    selection = json.loads(saved.stdout)
    if selection.get('manifest_sha256') != MANIFEST_SHA256 or selection.get('protocol_sha256') != PROTOCOL_SHA256 or selection.get('final_ids_sha256') != FINAL_IDS_SHA256:
        raise ValueError('Selection does not bind the frozen protocol')
    sources=selection.get('frozen_source_sha256',{})
    if set(sources)!=set(FROZEN_SOURCES):
        raise ValueError('Selection must freeze preparation, inference, metrics and architecture code')
    for name,expected in sources.items():
        committed=subprocess.run(['git','show','HEAD:'+name],cwd=root,capture_output=True)
        if committed.returncode or hashlib.sha256(committed.stdout).hexdigest()!=expected or sha256(root/name)!=expected:
            raise ValueError('Frozen evaluation method changed: '+name)
    checkpoint = root/selection['checkpoint']
    if sha256(checkpoint) != selection['checkpoint_sha256']:
        raise ValueError('Selected checkpoint changed')
    if selection.get('decision') != 'binary argmax, fixed threshold 0.5' or selection.get('tile_size') != 256 or selection.get('stride') != 256:
        raise ValueError('Selected inference settings changed')
    if selection.get('architecture') not in {'segformer','unet'} or not math.isfinite(selection.get('learning_rate',float('nan'))) or selection['learning_rate']<=0:
        raise ValueError('Missing chosen architecture/learning rate')
    run_path=root/selection['winner_run_json']
    if sha256(run_path)!=selection['winner_run_json_sha256']:
        raise ValueError('Development evidence changed')
    run=json.loads(run_path.read_text())
    epoch=selection['selected_epoch']
    if not 1<=epoch<=20 or epoch!=run['selected_epoch'] or selection['checkpoint_sha256']!=run['checkpoint_sha256']:
        raise ValueError('Selected checkpoint/epoch does not match saved development evidence')
    if run['settings']['architecture']!=selection['architecture'] or run['settings']['learning_rate']!=selection['learning_rate']:
        raise ValueError('Chosen config does not match saved run')
    recorded=next((row for row in run['history'] if row['epoch']==epoch and row['complete']),None)
    if not recorded or recorded!=selection['dev_metrics'] or recorded['f1'] is None:
        raise ValueError('Missing complete selected development metrics')
    denominator=2*recorded['tp']+recorded['fp']+recorded['fn']
    if not denominator or recorded['f1']!=2*recorded['tp']/denominator:
        raise ValueError('Saved development F1/counts disagree')
    from ml.vision.provenance import checkpoint_identity
    if checkpoint_identity(root/'ml/artifacts/sn8_native_cpu_v2/model')!=selection['v2_checkpoint_id']:
        raise ValueError('Current v2 checkpoint differs from the frozen selection')
    if checkpoint_identity(root/'ml/artifacts/sn8_native_cpu_v2/baseline_model')!=selection['initialization_checkpoint_id']:
        raise ValueError('Saved initialization/preprocessor changed')
    return selection, {'selection_commit':commit[0], 'selection_sha256':sha256(path)}


def validate_final_rows(rows, final_ids):
    if [row['source_image_id'] for row in rows] != final_ids or len(rows)!=38:
        raise ValueError('Final evaluation requires all sealed tiles in frozen order')
    if any(row.get('split')!='test' or row.get('crop_pixel_bounds') for row in rows):
        raise ValueError('Final evaluation requires complete original tiles')


def begin_attempt(path, request):
    """Completed final stages are immutable; only logged failed identical attempts retry."""
    fingerprint = canonical(request)
    previous = json.loads(path.read_text()) if path.exists() else None
    if previous:
        if previous['request_sha256'] != fingerprint:
            raise ValueError('Refusing a changed final command/configuration')
        if previous['status'] != 'failed':
            raise ValueError('Final stage already running/completed; no second evaluation')
    state = {'status':'running','request':request,'request_sha256':fingerprint,
             'started_at_utc':datetime.now(timezone.utc).isoformat(),
             'attempt':previous['attempt']+1 if previous else 1,
             'previous_failure':previous if previous else None}
    path.parent.mkdir(parents=True,exist_ok=True)
    if previous:
        path.write_text(json.dumps(state,indent=2)+'\n')
    else:
        with path.open('x') as stream:
            stream.write(json.dumps(state,indent=2)+'\n')
    return state


def finish_attempt(path, state, error=None):
    state.update(status='failed' if error else 'complete',finished_at_utc=datetime.now(timezone.utc).isoformat())
    if error:
        state['failure']={'type':type(error).__name__,'message':str(error)}
    path.write_text(json.dumps(state,indent=2)+'\n')
