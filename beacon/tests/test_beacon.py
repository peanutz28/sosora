import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location('beacon_client', Path(__file__).parents[1] / 'beacon.py')
beacon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beacon)


class Command:
    def __init__(self, codes):
        self.codes = iter(codes)
        self.calls = []

    def post(self, url, **kwargs):
        if 'files' in kwargs:
            filename, stream, mime = kwargs['files']['file']
            kwargs['audio'] = (filename, stream.read(), mime)
        self.calls.append((url, kwargs))
        code = next(self.codes)
        if isinstance(code, Exception):
            raise code
        return SimpleNamespace(status_code=code)


def test_offline_restart_reconnect_sends_once(tmp_path):
    queue = beacon.Outbox(tmp_path)
    item = queue.enqueue('reading', 'beacon-ww-bridge', {'water_level_cm': 42, 'threshold_cm': 30})
    network = Command([ConnectionError('unplugged'), 201])
    queue.send_due('http://command', offline=True, session=network)
    assert not network.calls
    queue.send_due('http://command', session=network, clock=lambda: 100)
    assert len(queue.pending()) == 1
    assert json.loads(queue.pending()[0].read_text())['attempts'] == 1
    restarted = beacon.Outbox(tmp_path)
    restarted.send_due('http://command', session=network, clock=lambda: 101)
    assert len(network.calls) == 1  # persisted backoff
    restarted.send_due('http://command', session=network, clock=lambda: 103)
    restarted.send_due('http://command', session=network, clock=lambda: 200)
    assert len(network.calls) == 2 and not restarted.pending()
    assert {call[1]['headers']['Idempotency-Key'] for call in network.calls} == {item['client_id']}
    assert json.loads((restarted.sent / (item['client_id'] + '.json')).read_text())['http_status'] == 201


def test_replay_copies_audio_before_send_and_preserves_cached_filename(tmp_path):
    audio = tmp_path / 'demo_hero.wav'
    audio.write_bytes(b'RIFF-test')
    queue = beacon.Outbox(tmp_path / 'outbox')
    item = queue.enqueue('voice', 'beacon-ww-bridge', wav=audio, simulated=True)
    audio.unlink()
    command = Command([200])
    queue.send_due('http://command', session=command)
    url, sent = command.calls[0]
    assert url == 'http://command/api/radio/audio'
    assert sent['audio'] == ('demo_hero.wav', b'RIFF-test', 'audio/wav')
    assert sent['data']['beacon_id'] == 'beacon-ww-bridge'
    assert sent['data']['source_type'] == 'beacon'
    assert (queue.sent / item['wav']).exists()
    assert not queue.pending()


@pytest.mark.parametrize('code', [301, 400, 503])
def test_non_2xx_never_drops_data(tmp_path, code):
    queue = beacon.Outbox(tmp_path)
    queue.enqueue('reading', 'id', {})
    queue.send_due('http://command', session=Command([code]))
    assert len(queue.pending()) == 1
    assert not list(queue.sent.glob('*.json'))


def test_sensor_crossing_heartbeat_and_falling_never_claim_open(tmp_path):
    queue = beacon.Outbox(tmp_path)
    sensor = beacon.SensorSampler(queue, 'id', 60, 30, fake=True)
    sensor.sample(50, 0)
    sensor.sample(40, 2)
    sensor.sample(30, 4)
    sensor.sample(20, 6)
    sensor.sample(20, 34)
    sensor.sample(50, 36)
    rows = [json.loads(p.read_text()) for p in queue.pending()]
    assert len(rows) == 4
    assert sorted(row['payload']['water_level_cm'] for row in rows) == [10, 10, 30, 40]
    assert all(row['simulated'] and row['payload']['measured_at'].endswith('+00:00') for row in rows)
    assert all('open' not in row['payload'] for row in rows)


def test_cli_offline_replay_without_gpio_or_requests(tmp_path):
    wav = tmp_path / 'demo_hero.wav'
    wav.write_bytes(b'RIFF-test')
    beacon.main(['--offline', '--replay', str(wav), '--outbox', str(tmp_path / 'queue')])
    assert len(list((tmp_path / 'queue').glob('*.json'))) == 1


@pytest.mark.parametrize('args', [['--threshold-cm', 'nan'], ['--mount-height-cm', '-1'], ['--server', 'ftp://bad']])
def test_invalid_cli(args):
    with pytest.raises(SystemExit):
        beacon.arguments(args)


def test_crash_after_receipt_does_not_resend(tmp_path):
    queue = beacon.Outbox(tmp_path / 'queue')
    item = queue.enqueue('reading', 'id', {})
    # Model power loss after saving the receipt but before deleting pending JSON.
    beacon.atomic_json(queue.sent / (item['client_id'] + '.json'), {**item, 'http_status': 200})
    beacon.main(['--flush', '--offline', '--outbox', str(queue.path)])
    assert not queue.pending()


def test_slow_upload_does_not_prevent_durable_sensor_enqueue(tmp_path):
    queue = beacon.Outbox(tmp_path)
    queue.enqueue('reading', 'id', {})
    class CommandWithSensor:
        def post(self, *args, **kwargs):
            import threading
            worker = threading.Thread(target=lambda: queue.enqueue('reading', 'id', {'water_level_cm': 42}))
            worker.start()
            worker.join(timeout=1)
            assert not worker.is_alive(), 'Network sender must not hold the queue writer lock'
            return SimpleNamespace(status_code=200)
    queue.send_due('http://command', session=CommandWithSensor())
    assert len(queue.pending()) == 1


def test_voice_only_excludes_simulated_sensor():
    args = beacon.arguments(['--voice-only', '--audio-device', 'plughw:3,0'])
    assert args.voice_only and not args.fake_sensor
    with pytest.raises(SystemExit):
        beacon.arguments(['--voice-only', '--fake-sensor'])


def test_record_uses_selected_usb_mic_and_durably_queues(tmp_path, monkeypatch):
    queue = beacon.Outbox(tmp_path / 'outbox')
    def capture(command, **kwargs):
        assert command[:3] == ['arecord', '-D', 'plughw:3,0']
        Path(command[-1]).write_bytes(b'RIFF microphone recording')
    monkeypatch.setattr(beacon.subprocess, 'run', capture)
    beacon.record(queue, beacon.arguments(['--voice-only', '--audio-device', 'plughw:3,0']))
    row = json.loads(queue.pending()[0].read_text())
    assert not row['simulated'] and row['filename'] == 'voice.wav'
    assert (queue.path / row['wav']).read_bytes() == b'RIFF microphone recording'
