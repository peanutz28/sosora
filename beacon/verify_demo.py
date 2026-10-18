#!/usr/bin/env python3
"""Verify simulated Beacon flows against an isolated real Command HTTP server.

Run from repo root: PYTHONPATH=backend:. ml/.venv312/bin/python beacon/verify_demo.py
Creates silence for the filename-based cached transcript; this does not test ASR.
"""
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import wave

import requests
import uvicorn

from app.factory import create_app
from app.routing import load_anchors, load_graph

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('beacon_client', ROOT / 'beacon/beacon.py')
beacon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beacon)


def main():
    os.environ['DEMO_MODE'] = 'true'
    os.environ.pop('ASR_BASE_URL', None)
    evidence = {'simulated': True, 'asr': 'filename-based cached transcript; silent test WAV, not speech recognition',
                'backend_mode': 'DEMO_MODE=true', 'cases': {}}
    with tempfile.TemporaryDirectory(prefix='beacon-verification-') as directory:
        temporary = Path(directory)
        app = create_app(load_graph(), load_anchors(), str(temporary / 'command.db'))
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        server_url = f'http://127.0.0.1:{sock.getsockname()[1]}'
        server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        while not server.started:
            if not thread.is_alive():
                raise RuntimeError('Command server failed')
            time.sleep(0.05)
        def seed():
            response = requests.post(server_url + '/api/radio/demo/seed', timeout=90)
            response.raise_for_status()
            assert all(i['reachable'] for i in response.json()['state']['incidents'])
        def outcome():
            response = requests.get(server_url + '/api/radio/status', timeout=90)
            response.raise_for_status()
            status = response.json()
            result = {'unreachable_ids': [i['id'] for i in status['incidents'] if not i['reachable']],
                      'segment_statuses': sorted({s['status'] for s in status['segment_statuses'].values()})}
            assert result['unreachable_ids'] == ['SOS-001', 'SOS-002', 'SOS-003', 'SOS-004', 'SOS-005']
            assert result['segment_statuses'] == ['blocked']
            return result
        try:
            seed()
            log_path = temporary / 'fake.log'
            with log_path.open('w') as log:
                process = subprocess.Popen([sys.executable, str(ROOT / 'beacon/beacon.py'), '--fake-sensor',
                    '--server', server_url, '--outbox', str(temporary / 'fake')], stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 60
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise RuntimeError(log_path.read_text())
                        receipts = list((temporary / 'fake/sent').glob('*.json'))
                        if any(json.loads(p.read_text())['payload']['water_level_cm'] >= 30 for p in receipts):
                            break
                        time.sleep(0.2)
                    else:
                        raise AssertionError('Fake sensor did not deliver threshold reading')
                finally:
                    process.send_signal(signal.SIGINT)
                    process.wait(timeout=200)
            evidence['cases']['fake_sensor'] = {**outcome(), 'log': log_path.read_text().splitlines()}
            seed()
            wav = temporary / 'demo_hero.wav'
            with wave.open(str(wav), 'wb') as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16000)
                audio.writeframes(b'\0\0' * 16000)
            replay = subprocess.run([sys.executable, str(ROOT / 'beacon/beacon.py'), '--replay', str(wav),
                '--server', server_url, '--outbox', str(temporary / 'replay')], capture_output=True, text=True, timeout=200)
            assert replay.returncode == 0, replay.stderr
            evidence['cases']['replay'] = {**outcome(), 'log': replay.stdout.splitlines()}
            seed()
            queue = beacon.Outbox(temporary / 'reconnect')
            item = queue.enqueue('voice', 'beacon-ww-bridge', wav=wav, simulated=True)
            queue.send_due('http://127.0.0.1:1')
            assert len(queue.pending()) == 1
            restarted = beacon.Outbox(temporary / 'reconnect')
            restarted.send_due(server_url, clock=lambda: time.time() + 100)
            restarted.send_due(server_url, clock=lambda: time.time() + 200)
            assert not restarted.pending()
            received = [e for e in app.state.engine.events if e['kind'] == 'radio_received']
            assert len(received) == 1
            evidence['cases']['reconnect'] = {**outcome(), 'radio_received_count': len(received),
                'client_id_preserved': json.loads((queue.sent / (item['client_id'] + '.json')).read_text())['client_id'] == item['client_id']}
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()
    destination = ROOT / 'beacon/evidence/demo_verification.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'PASS: {destination}')


if __name__ == '__main__':
    main()
