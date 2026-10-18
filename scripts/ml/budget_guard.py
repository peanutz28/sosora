"""Stop this task's instance after a conservative three-hour ceiling.
Run independently of training; never operates on other instances.
"""
import json
import subprocess
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
state = ROOT/'ml/artifacts/budget_guard.json'
if __name__ == '__main__':
    started = time.time()
    deadline = started + 3*3600
    state.write_text(json.dumps({'instance':'sosora-vision','started_unix':started,'deadline_unix':deadline,'authorized_total_usd':5,'catalog_compute_usd_per_hour':0.845421,'status':'armed'},indent=2))
    while time.time() < deadline:
        time.sleep(min(30,deadline-time.time()))
    for attempt in range(10):
        result = subprocess.run([str(ROOT/'ml/tools/brev'),'stop','sosora-vision'],capture_output=True,text=True,timeout=120)
        if result.returncode == 0:
            state.write_text(json.dumps({'instance':'sosora-vision','status':'stop_command_succeeded','stopped_unix':time.time(),'output':result.stdout},indent=2))
            break
        time.sleep(30)
    else:
        state.write_text(json.dumps({'instance':'sosora-vision','status':'STOP_FAILED_REQUIRES_ATTENTION'},indent=2))
