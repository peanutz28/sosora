"""Freeze the highest recorded complete development score, without final data access."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from ml.experiments.v3_protocol import (ROOT,MANIFEST_SHA256,PROTOCOL_SHA256,
    FINAL_IDS_SHA256,SELECTION_DEADLINE,FROZEN_SOURCES,preflight,sha256)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runs',type=Path,required=True);args=parser.parse_args()
    preflight()
    if datetime.now(timezone.utc)>=SELECTION_DEADLINE:raise ValueError('Selection deadline expired')
    evidence=ROOT/'docs/ml/evidence/v3_2026-10-18';output=evidence/'selection.json'
    if output.exists():raise ValueError('Selection already frozen; no re-selection')
    attempts=json.loads((args.runs/'attempts.json').read_text())
    eligible=[]
    for attempt in attempts:
        if attempt.get('benchmark') or attempt['returncode']!=0 or attempt.get('best_dev_f1') is None:continue
        run_path=args.runs/attempt['name']/'run.json';run=json.loads(run_path.read_text())
        checkpoint=args.runs/attempt['name']/'best.pt'
        if run['manifest_sha256']!=MANIFEST_SHA256 or sha256(checkpoint)!=run['checkpoint_sha256']:
            raise ValueError('Recorded development identity mismatch')
        score=next(row for row in run['history'] if row['epoch']==run['selected_epoch'] and row['complete'])
        if score['f1']!=attempt['best_dev_f1']:raise ValueError('Selected development score mismatch')
        eligible.append((score['f1'],attempt,run,checkpoint))
    if not eligible:raise ValueError('No valid development checkpoint')
    _,attempt,run,checkpoint=max(eligible,key=lambda item:item[0])
    copied=[]
    for source in sorted(args.runs.rglob('*')):
        if source.is_file() and source.suffix in {'.json','.log'}:
            target=evidence/'runs'/source.relative_to(args.runs);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(source.read_bytes());copied.append(str(target.relative_to(ROOT)))
    reference=json.loads((evidence/'v2_dev.json').read_text())
    from ml.vision.provenance import checkpoint_identity
    dev=next(row for row in run['history'] if row['epoch']==run['selected_epoch'])
    run_path=evidence/'runs'/attempt['name']/'run.json'
    selection={'selected_at_utc':datetime.now(timezone.utc).isoformat(),'selection_scope':'Reviewed development crops only; no final data opened',
        'manifest_sha256':MANIFEST_SHA256,'protocol_sha256':PROTOCOL_SHA256,'final_ids_sha256':FINAL_IDS_SHA256,
        'architecture':run['settings']['architecture'],'learning_rate':run['settings']['learning_rate'],
        'selected_epoch':run['selected_epoch'],'parameters':run['parameters'],'seed':run['settings']['seed'],
        'dev_metrics':dev,'v2_dev_metrics':reference['metrics'],'v2_checkpoint_id':reference['checkpoint_id'],
        'checkpoint':str(checkpoint.resolve().relative_to(ROOT)),'checkpoint_sha256':sha256(checkpoint),
        'winner_run_json':str(run_path.relative_to(ROOT)),'winner_run_json_sha256':sha256(run_path),
        'runner_source_sha256':run['runner_source_sha256'],'decision':'binary argmax, fixed threshold 0.5',
        'frozen_source_sha256':{name:sha256(ROOT/name) for name in FROZEN_SOURCES},
        'initialization_checkpoint_id':checkpoint_identity(ROOT/'ml/artifacts/sn8_native_cpu_v2/baseline_model'),
        'tile_size':256,'stride':256,'all_attempts_evidence':copied,
        'tie_rule':'Highest complete dev micro F1; candidate order breaks exact ties; runner keeps earliest strictly best epoch.',
        'initialization':'Random width16 four-level U-Net' if run['settings']['architecture']=='unet' else 'Saved pretrained ADE-derived binary initialization',
        'caveat':'Development score pools correlated label-centered crops from19 tiles. No threshold, final imagery, or final labels informed this choice.'}
    output.write_text(json.dumps(selection,indent=2)+'\n')
    print(json.dumps({'selection_file':str(output.relative_to(ROOT)),'architecture':selection['architecture'],
        'learning_rate':selection['learning_rate'],'selected_epoch':selection['selected_epoch'],
        'dev_f1':dev['f1'],'checkpoint_sha256':selection['checkpoint_sha256']}))


if __name__=='__main__':main()
