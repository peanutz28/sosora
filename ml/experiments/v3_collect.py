"""Retrieve every development run, then immediately stop only Codex D's L4."""
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import tarfile
import time
from ml.experiments.v3_budget_guard import INSTANCE, snapshot, write
from ml.experiments.v3_protocol import ROOT, FREEZE_DEADLINE, sha256

OBSERVER='''#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/sosora-v3-d"
while [ ! -f sweep_exit_code ]; do sleep 10; done
.venv/bin/python - <<'PY'
from importlib import metadata
import json,shutil
from pathlib import Path
root=Path('ml/artifacts/v3_runs_20261018')
versions={name:metadata.version(name) for name in ('torch','transformers','numpy','pillow')}
(root/'environment.json').write_text(json.dumps(versions,indent=2)+'\\n')
shutil.copyfile('sweep.log',root/'sweep.log')
shutil.copyfile('sweep_exit_code',root/'sweep_exit_code.txt')
PY
tar -czf v3_results.tar.gz ml/artifacts/v3_runs_20261018
python3 - <<'PY'
import hashlib,json
from pathlib import Path
path=Path('v3_results.tar.gz')
print('V3_COLLECTION_JSON='+json.dumps({'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'archive_bytes':path.stat().st_size,'sweep_exit_code':int(Path('sweep_exit_code').read_text())}),flush=True)
PY
'''


def main():
    if datetime.now(timezone.utc)>=FREEZE_DEADLINE:
        raise ValueError('Dated V3 feature freeze reached')
    private=ROOT/'ml/artifacts/v3_experiment';evidence=ROOT/'docs/ml/evidence/v3_2026-10-18'
    observer=Path('/private/tmp/sosora-v3-collect-observer.sh');observer.write_text(OBSERVER)
    archive=Path('/private/tmp/sosora-v3-results.tar.gz')
    receipt=None;failure=None
    try:
        initial=snapshot()
        if initial['status']!='RUNNING':raise ValueError('Approved L4 is not running')
        result=subprocess.run([str(ROOT/'ml/tools/brev'),'exec',INSTANCE,'@'+str(observer)],
                              capture_output=True,text=True,timeout=1800)
        (private/'collection_private.log').write_text(result.stdout+'\n'+result.stderr)
        records=[line.split('V3_COLLECTION_JSON=',1)[1] for line in result.stdout.splitlines() if 'V3_COLLECTION_JSON=' in line]
        if result.returncode or not records:raise ValueError('Remote collection failed; raw log retained privately')
        receipt=json.loads(records[-1])
        result=subprocess.run([str(ROOT/'ml/tools/brev'),'copy',INSTANCE+':/home/ubuntu/sosora-v3-d/v3_results.tar.gz',str(archive)],
                              capture_output=True,text=True,timeout=300)
        (private/'download_private.log').write_text(result.stdout+'\n'+result.stderr)
        if result.returncode or sha256(archive)!=receipt['archive_sha256']:
            raise ValueError('Development archive retrieval/integrity failed')
        receipt['retrieved_at_utc']=datetime.now(timezone.utc).isoformat()
        write(evidence/'collection.json',receipt)
    except BaseException as exc:
        failure=exc
    finally:
        stopped={'stop_requested_at_utc':datetime.now(timezone.utc).isoformat(),'instance_alias':INSTANCE,'gpu':'L4','events':[]}
        for attempt in range(8):
            try:
                current=snapshot();stopped['events'].append(current)
                if current['status']=='STOPPED':
                    stopped['verified_stopped_at_utc']=datetime.now(timezone.utc).isoformat();break
                result=subprocess.run([str(ROOT/'ml/tools/brev'),'stop',INSTANCE],capture_output=True,text=True,timeout=45)
                (private/f'stop_attempt_{attempt+1}_private.log').write_text(result.stdout+'\n'+result.stderr)
                stopped['events'].append({'stop_returncode':result.returncode})
            except Exception as exc:
                stopped['events'].append({'failure_type':type(exc).__name__})
            time.sleep(10)
        stopped['verified_stopped']='verified_stopped_at_utc' in stopped
        write(evidence/'gpu_stop.json',stopped)
        if stopped['verified_stopped']:
            guard_path=private/'v3_runtime_guard.json';guard=json.loads(guard_path.read_text())
            guard.update(status='disarmed_after_verified_stop',verified_stopped_at_utc=stopped['verified_stopped_at_utc'])
            write(guard_path,guard)
        print(json.dumps(stopped),flush=True)
        if not stopped['verified_stopped']:
            raise RuntimeError('L4 stop not verified; independent guard remains armed')
    if failure:raise failure
    with tarfile.open(archive,'r:gz') as stream:
        for entry in stream.getmembers():
            if not entry.name.startswith('ml/artifacts/v3_runs_20261018') or entry.issym() or entry.islnk():
                raise ValueError('Unexpected results archive member')
        stream.extractall(ROOT,filter='data')
    if receipt['sweep_exit_code']:
        raise ValueError('Sweep failed; all retrieved failures retained, no final access')
    print('All development evidence retrieved and L4 stopped',flush=True)


if __name__=='__main__':main()
