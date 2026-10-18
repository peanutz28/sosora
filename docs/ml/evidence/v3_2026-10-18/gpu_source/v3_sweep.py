"""Bounded development-only sweep; records every attempted run and never accesses final data."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from ml.experiments.v3_protocol import ROOT, MANIFEST_SHA256, PROTOCOL_SHA256, preflight, sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',choices=['cpu','cuda'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    os.chdir(ROOT)
    preflight()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Refusing to overwrite sweep evidence')
    args.output.mkdir(parents=True,exist_ok=True)
    deadline=datetime(2026,10,18,9,0,tzinfo=timezone.utc).timestamp()
    candidates=[('segformer',5e-5),('segformer',2e-4)]
    if args.device=='cuda':candidates += [('unet',1e-4),('unet',1e-3)]
    plan={'created_at_utc':datetime.now(timezone.utc).isoformat(),'manifest_sha256':MANIFEST_SHA256,
        'protocol_sha256':PROTOCOL_SHA256,'device':args.device,'candidates':[
            {'architecture':arch,'learning_rate':rate,'seed':42,'epochs':20,'batch_size':4,'max_steps':2720}
            for arch,rate in candidates],
        'selection':'Highest finite complete development-crop micro F1; earliest epoch on exact ties; candidate order breaks remaining ties. No final labels or threshold tuning.',
        'learning_rate_rationale':'Two rates per architecture chosen before training: pretrained SegFormer lower rates; randomly initialized U-Net wider/higher range. Capacities and initialization differ; this is a bounded sweep, not equal optimization.',
        'inference_decision':'binary argmax, fixed threshold 0.5','maximum_epoch_count':20,
        'runner_source_sha256':sha256(Path(__file__).with_name('train_comparator.py'))}
    (args.output/'sweep_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    attempts=[]
    def run(architecture,rate,name,benchmark=False):
        remaining=deadline-time.time()
        if remaining<180:raise ValueError('Development budget expired before next run')
        folder=args.output/name
        command=[sys.executable,'-m','ml.experiments.train_comparator',
            '--manifest','ml/artifacts/v3_experiment/reviewed_crop_manifest.json',
            '--output',str(folder),'--architecture',architecture,'--device',args.device,
            '--learning-rate',str(rate),'--epochs','20','--batch-size','4','--seed','42',
            '--max-steps','13' if benchmark else '2720','--max-seconds',str(min(180 if benchmark else 2400,remaining-60))]
        if benchmark:command+=['--benchmark','--warmup','3']
        record={'name':name,'architecture':architecture,'learning_rate':rate,'benchmark':benchmark,
            'command':command,'started_at_utc':datetime.now(timezone.utc).isoformat()}
        attempts.append(record)
        (args.output/'attempts.json').write_text(json.dumps(attempts,indent=2)+'\n')
        with (args.output/(name+'.log')).open('w') as log:
            try:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=min(remaining,2600))
                record['returncode']=result.returncode
            except Exception as exc:
                record['failure']={'type':type(exc).__name__,'message':str(exc)}
                record['returncode']=-1
        record['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        if (folder/'run.json').exists():
            summary=json.loads((folder/'run.json').read_text())
            record['run_sha256']=sha256(folder/'run.json')
            record['selected_epoch']=summary['selected_epoch']
            record['checkpoint_sha256']=summary['checkpoint_sha256']
            if not benchmark:
                complete=[row for row in summary['history'] if row['complete'] and row['f1'] is not None]
                record['best_dev_f1']=max((row['f1'] for row in complete),default=None)
        (args.output/'attempts.json').write_text(json.dumps(attempts,indent=2)+'\n')
        print(json.dumps(record),flush=True)
        return record
    for architecture in dict.fromkeys(arch for arch,rate in candidates):
        check=run(architecture,candidates[0][1],architecture+'_benchmark',True)
        if check['returncode']!=0:raise ValueError('Architecture benchmark failed; no long sweep')
    for index,(architecture,rate) in enumerate(candidates):
        run(architecture,rate,f'{index+1:02d}_{architecture}_lr{rate:g}')
    eligible=[item for item in attempts if not item['benchmark'] and item['returncode']==0 and item.get('best_dev_f1') is not None and item.get('checkpoint_sha256')]
    if not eligible:raise ValueError('No eligible fully recorded development checkpoint')
    winner=max(eligible,key=lambda item:item['best_dev_f1'])
    (args.output/'development_winner.json').write_text(json.dumps(winner,indent=2)+'\n')
    print('DEVELOPMENT_WINNER '+json.dumps(winner),flush=True)


if __name__=='__main__':main()
