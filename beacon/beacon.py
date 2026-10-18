#!/usr/bin/env python3
"""SOSora Beacon: durable, at-least-once voice and sensor store-and-forward."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from urllib.parse import quote
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Outbox:
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.sent = self.path / 'sent'
        self.sent.mkdir(exist_ok=True)
        self.lock = threading.RLock()

    def pending(self):
        rows = []
        for path in self.path.glob('*.json'):
            try:
                rows.append((path.stat().st_mtime_ns, path.name, path))
            except FileNotFoundError:  # Sender may acknowledge during a queue count.
                continue
        return [row[2] for row in sorted(rows)]

    def enqueue(self, kind, beacon_id, payload=None, wav=None, simulated=False):
        with self.lock:
            client_id = f'{kind}-{uuid4()}'
            item = dict(client_id=client_id, kind=kind, beacon_id=beacon_id,
                        created_at=now(), simulated=simulated, payload=payload,
                        attempts=0, next_attempt=0)
            if wav is not None:
                source = Path(wav)
                item['filename'] = source.name  # Keep demo_hero.wav for cached ASR.
                item['wav'] = client_id + '.wav'
                destination = self.path / item['wav']
                with source.open('rb') as incoming, destination.open('xb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                if destination.stat().st_size == 0 or destination.stat().st_size > 20_000_000:
                    destination.unlink()
                    raise ValueError('WAV must be 1 byte to 20 MB')
            atomic_json(self.path / f'{client_id}.json', item)
            label = ' [SIMULATED]' if simulated else ''
            print(f'QUEUED {client_id}{label} {len(self.pending())} items', flush=True)
            return item

    def send_due(self, server, offline=False, session=None, clock=time.time):
        """One bounded pass. Persist backoff; only an HTTP 2xx acknowledges an item."""
        if offline:
            if self.pending():
                print(f'QUEUED (no link) {len(self.pending())} items [offline]', flush=True)
            return
        if session is None:
            import requests
            session = requests
        for path in self.pending():
            try:
                item = json.loads(path.read_text())
                if item['next_attempt'] > clock():
                    continue
                headers = {'Idempotency-Key': item['client_id']}
                if item['kind'] == 'voice':
                    with (self.path / item['wav']).open('rb') as audio:
                        response = session.post(server + '/api/radio/audio',
                            files={'file': (item['filename'], audio, 'audio/wav')},
                            data={'beacon_id': item['beacon_id'], 'source_type': 'beacon',
                                  'client_id': item['client_id'], 'simulated': str(item['simulated']).lower()},
                            headers=headers, timeout=(5, 180), allow_redirects=False)
                else:
                    response = session.post(server + '/api/beacon/' + quote(item['beacon_id'], safe='') + '/reading',
                        json={**item['payload'], 'client_id': item['client_id'], 'simulated': item['simulated']},
                        headers=headers, timeout=(5, 180), allow_redirects=False)
                if not 200 <= response.status_code < 300:
                    raise RuntimeError(f'HTTP {response.status_code}')
                item['acknowledged_at'] = now()
                item['http_status'] = response.status_code
                # Archive the acknowledgement before removing the pending record.
                atomic_json(self.sent / path.name, item)
                path.unlink()
                if item.get('wav'):
                    os.replace(self.path / item['wav'], self.sent / item['wav'])
                print(f"SENT {item['client_id']} {response.status_code}", flush=True)
            except Exception as exc:
                # A crash between saving the receipt and deleting pending must not resend.
                if (self.sent / path.name).exists():
                    path.unlink(missing_ok=True)
                    continue
                try:
                    item = json.loads(path.read_text())
                    item['attempts'] += 1
                    item['next_attempt'] = clock() + min(60, 2 ** min(item['attempts'], 6))
                    atomic_json(path, item)
                except (OSError, ValueError, KeyError):
                    pass
                print(f'QUEUED (no link) {len(self.pending())} items ({type(exc).__name__})', flush=True)

class SensorSampler:
    def __init__(self, outbox, beacon_id, mount_height, threshold, fake=False):
        self.outbox, self.beacon_id = outbox, beacon_id
        self.mount_height, self.threshold, self.fake = mount_height, threshold, fake
        self.previous = None
        self.last_queued = None

    def sample(self, distance_cm, monotonic=None):
        tick = time.monotonic() if monotonic is None else monotonic
        if not math.isfinite(distance_cm) or distance_cm < 0:
            raise ValueError('Invalid distance')
        water = max(0.0, self.mount_height - distance_cm)
        over = water >= self.threshold
        if self.previous is None or over != self.previous or tick - self.last_queued >= 30:
            self.outbox.enqueue('reading', self.beacon_id,
                dict(water_level_cm=round(water, 2), threshold_cm=self.threshold, measured_at=now()),
                simulated=self.fake)
            self.last_queued = tick
        self.previous = over
        print(f"SENSOR{' [SIMULATED]' if self.fake else ''} water={water:.1f} cm threshold={self.threshold:.1f} cm", flush=True)


def record(outbox, args):
    with tempfile.TemporaryDirectory(prefix='sosora-voice-') as directory:
        wav = Path(directory) / 'voice.wav'
        subprocess.run(['arecord', '-D', args.audio_device, '-f', 'S16_LE', '-r', '16000',
                        '-c', '1', '-d', '8', str(wav)], check=True, timeout=15)
        outbox.enqueue('voice', args.beacon_id, wav=wav)


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', default='http://localhost:8000')
    parser.add_argument('--beacon-id', default='beacon-ww-bridge')
    parser.add_argument('--mount-height-cm', type=float, default=60)
    parser.add_argument('--threshold-cm', type=float, default=30)
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--fake-sensor', action='store_true')
    parser.add_argument('--flush', action='store_true', help='Send existing outbox and exit; no sensor or recording')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--outbox', type=Path, default=Path(__file__).resolve().parent / 'outbox')
    parser.add_argument('--audio-device', default='plughw:1,0')
    parser.add_argument('--button', action='store_true', help='Enable GPIO17 push-to-talk')
    args = parser.parse_args(argv)
    if not (0 < args.threshold_cm <= args.mount_height_cm <= 2000):
        parser.error('Require 0 < threshold <= mount height <= 2000 cm')
    if not args.server.startswith(('http://', 'https://')):
        parser.error('--server must be an HTTP(S) URL')
    args.server = args.server.rstrip('/')
    return args


def main(argv=None):
    args = arguments(argv)
    outbox = Outbox(args.outbox)
    if not args.offline:
        try:
            import requests  # Fail clearly before starting background threads.
        except ImportError:
            raise SystemExit('Install requests: python -m pip install requests')
    # Only one sender may own this disk queue (Linux Pi and macOS development).
    import fcntl
    with (outbox.path / '.lock').open('w') as owner:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another Beacon process owns this outbox')
        # Recover acknowledged-but-not-yet-removed pending records after a crash.
        for path in outbox.pending():
            if (outbox.sent / path.name).exists():
                receipt = json.loads((outbox.sent / path.name).read_text())
                if receipt.get('wav') and (outbox.path / receipt['wav']).exists():
                    os.replace(outbox.path / receipt['wav'], outbox.sent / receipt['wav'])
                path.unlink()
        if args.replay:
            outbox.enqueue('voice', args.beacon_id, wav=args.replay,
                           simulated=args.replay.name.startswith('demo_'))
            if args.offline and not args.fake_sensor:
                outbox.send_due(args.server, offline=True)
                return
        if args.flush and args.offline:
            outbox.send_due(args.server, offline=True)
            return
        stop = threading.Event()
        failures = []
        def sensor_loop():
            sensor = None
            try:
                if not args.fake_sensor:
                    from gpiozero import DistanceSensor
                    sensor = DistanceSensor(echo=24, trigger=23, max_distance=2)
                sampler = SensorSampler(outbox, args.beacon_id, args.mount_height_cm,
                                        args.threshold_cm, args.fake_sensor)
                level = 0.0
                while not stop.is_set():
                    distance = max(0, args.mount_height_cm - level) if args.fake_sensor else sensor.distance * 100
                    sampler.sample(distance)
                    level = min(args.mount_height_cm, level + 5)
                    stop.wait(2)
            except Exception as exc:
                failures.append(type(exc).__name__)
                print(f'SENSOR unavailable ({type(exc).__name__}); queued data retained', flush=True)
                stop.set()
            finally:
                if sensor is not None:
                    sensor.close()
        sensor_thread = None
        if not (args.replay or args.flush) or args.fake_sensor:
            sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
            sensor_thread.start()
        def sender_loop():
            while not stop.is_set():
                outbox.send_due(args.server, args.offline)
                stop.wait(1 if not args.offline else 10)
        sender = threading.Thread(target=sender_loop, daemon=True)
        sender.start()
        button = None
        try:
            if args.button:
                from gpiozero import Button
                button = Button(17, pull_up=True, bounce_time=0.1)
                button.when_pressed = lambda: record(outbox, args)
            print('Beacon ready. Enter records 8 seconds; Ctrl-C stops. Pending items survive restart.', flush=True)
            while not stop.wait(0.2):
                if (args.replay or args.flush) and not args.fake_sensor and not outbox.pending():
                    break
                if not (args.replay or args.flush) and sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.readline()
                    try:
                        record(outbox, args)
                    except (OSError, subprocess.SubprocessError) as exc:
                        print(f'RECORD failed ({type(exc).__name__}); try --replay', flush=True)
        except KeyboardInterrupt:
            print('Stopping; unsent items remain in outbox.', flush=True)
        finally:
            stop.set()
            if button is not None:
                button.close()
            # Allow the bounded request to finish before releasing the outbox lock.
            sender.join()
            if sensor_thread is not None:
                sensor_thread.join()
        if failures:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
