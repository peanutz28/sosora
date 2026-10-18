"""Stop only Codex F's instance at the feasibility deadline (earlier than 9 ET)."""
import datetime
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/evidence/lora_f_2026-10-18'
NAME = 'sosora-lora-f'
IDENTITY = '7va41egen'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    deadline = datetime.datetime(2026, 10, 18, 8, 57, tzinfo=datetime.timezone.utc).timestamp()
    (OUT / 'guard_armed.json').write_text(json.dumps({'instance': NAME, 'id': IDENTITY, 'stop_at_utc': '2026-10-18T08:57:00Z', 'hard_stop_et': '2026-10-18T09:00:00-04:00'}))
    while time.time() < deadline:
        time.sleep(min(15, deadline - time.time()))
    while True:
        try:
            listing = subprocess.run([str(ROOT/'ml/tools/brev'), 'ls', '--json'], capture_output=True, text=True, timeout=30, check=True)
            rows = [r for r in json.loads(listing.stdout)['workspaces'] if r['name'] == NAME]
            if not rows:
                (OUT/'guard_stopped.json').write_text(json.dumps({'name': NAME, 'id': IDENTITY, 'status': 'deleted_absent_from_catalog'}))
                return
            row = rows[0]
            assert row['id'] == IDENTITY and row['gpu'] == 'H100'
            if row['status'] == 'STOPPED':
                (OUT/'guard_stopped.json').write_text(json.dumps(row, indent=2))
                return
            subprocess.run([str(ROOT/'ml/tools/brev'), 'stop', NAME], capture_output=True, timeout=40)
        except Exception as exc:
            (OUT/'guard_error.txt').write_text(type(exc).__name__)
        time.sleep(10)

if __name__ == '__main__':
    main()
