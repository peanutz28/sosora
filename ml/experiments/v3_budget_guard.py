"""Independent deadline/budget guard for Codex D's approved L4 only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
INSTANCE = 'sosora-vision'
INSTANCE_TYPE = 'g2-standard-4:nvidia-l4:1'


def snapshot():
    result = subprocess.run([str(ROOT/'ml/tools/brev'), 'ls', '--json'],
                            capture_output=True, text=True, timeout=35, check=True)
    rows = json.loads(result.stdout)['workspaces']
    if isinstance(rows, dict):
        rows = list(rows.values())
    row = next(item for item in rows if item['name'] == INSTANCE)
    if row.get('gpu') != 'L4' or row.get('instance_type') != INSTANCE_TYPE:
        raise ValueError('Protected instance mismatch; refusing to operate')
    return {'name': INSTANCE, 'gpu': 'L4', 'instance_type': INSTANCE_TYPE, 'status': row['status']}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--quote', type=Path, required=True)
    args = parser.parse_args()
    quote = json.loads(args.quote.read_text())
    if not quote.get('launch_authorized') or quote['authorized_total_usd'] != 5:
        raise ValueError('Missing explicit approved budget')
    if quote['instance_type'] != INSTANCE_TYPE:
        raise ValueError('Quote does not match the approved L4')
    started = time.time()
    hard_stop = datetime(2026, 10, 18, 10, 30, tzinfo=timezone.utc).timestamp()
    # Begin stop ten minutes early; reserve credit headroom for retained storage.
    trigger = min(hard_stop-600, started+(quote['authorized_total_usd']-0.5)/quote['compute_usd_per_hour']*3600)
    initial = snapshot()
    if initial['status'] != 'STOPPED':
        raise ValueError('Guard must arm before this task starts its stopped L4')
    state = {'status': 'armed', 'instance': INSTANCE, 'gpu': 'L4',
             'started_unix': started, 'stop_trigger_unix': trigger,
             'hard_stop_unix': hard_stop, 'authorized_total_usd': 5,
             'compute_usd_per_hour': quote['compute_usd_per_hour'], 'events': []}
    write(args.state, state)
    print('V3 L4-only guard armed', flush=True)
    while time.time() < trigger:
        if args.state.exists() and json.loads(args.state.read_text()).get('status') == 'disarmed_after_verified_stop':
            print('V3 guard disarmed after verified stop', flush=True)
            return
        time.sleep(min(20, trigger-time.time()))
    while time.time() < hard_stop:
        try:
            current = snapshot()
            state['events'].append({'at_utc': datetime.now(timezone.utc).isoformat(), **current})
            if current['status'] == 'STOPPED':
                state['status'] = 'verified_stopped'
                write(args.state, state)
                print('V3 L4 verified stopped', flush=True)
                return
            result = subprocess.run([str(ROOT/'ml/tools/brev'), 'stop', INSTANCE],
                                    capture_output=True, text=True, timeout=35)
            state['events'].append({'stop_returncode': result.returncode})
        except Exception as exc:
            state['events'].append({'failure_type': type(exc).__name__})
        state['status'] = 'stopping'
        write(args.state, state)
        time.sleep(min(10, max(0, hard_stop-time.time())))
    state['status'] = 'STOP_NOT_VERIFIED_REQUIRES_IMMEDIATE_ATTENTION'
    write(args.state, state)
    raise SystemExit('L4 stop was not verified before hard deadline')


if __name__ == '__main__':
    main()
