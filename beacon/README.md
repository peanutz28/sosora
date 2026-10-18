# SOSora Beacon: brief for Codex (owner: Ria)

The Beacon is the physical, on-camera part of SOSora: a Raspberry Pi at a flood-prone
crossing that **hears voice reports** (USB mic) and **measures water level** (ultrasonic
sensor), then **stores and forwards** them to SOSora Command whenever any link exists.
Demo location: the eastern Warren Wilson Road bridge over the Swannanoa River (registered as
`beacon-ww-bridge` in `backend/app/radio_api.py` -> `BEACONS`). Read `docs/CONTEXT.md` first.

## Hardware
- Raspberry Pi (any with GPIO + USB), USB microphone, push button (optional), HC-SR04
  ultrasonic distance sensor, 1 kOhm + 2 kOhm resistors.
- **HC-SR04 wiring (the ECHO pin is 5 V; the Pi's GPIO is 3.3 V, so use the divider):**
  VCC -> pin 2 (5 V), GND -> pin 6, TRIG -> GPIO23 (pin 16),
  ECHO -> 1 kOhm -> GPIO24 (pin 18), and GPIO24 -> 2 kOhm -> GND.
- Optional push-to-talk button: GPIO17 (pin 11) to GND, internal pull-up.
- Mount the sensor pointing down above a container. water_level_cm = mount_height_cm - distance_cm.

## Software to write (all in `beacon/`)
`beacon/beacon.py`, one process, Python 3, deps: `gpiozero`, `requests` (and `arecord` from alsa-utils).
1. **Voice**: press Enter (or the button) -> record 8 s WAV with
   `arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 8 out.wav` -> enqueue.
2. **Sensor**: every 2 s read distance (gpiozero `DistanceSensor(echo=24, trigger=23, max_distance=2)`),
   compute water level, enqueue a reading when it crosses the threshold or every 30 s.
3. **Store and forward (the offline story)**: every item gets a `client_id` (uuid) and is
   written to `beacon/outbox/*.json` (+ `.wav`) BEFORE sending. A sender loop retries with
   backoff and deletes/moves an item only after a 2xx. Print a clear status line:
   `QUEUED (no link) 3 items` / `SENT voice-... 201`. This is what we film.
4. **CLI flags**: `--server URL`, `--beacon-id beacon-ww-bridge`, `--mount-height-cm 60`,
   `--threshold-cm 30`, `--replay path.wav` (send a pre-recorded file, demo fallback),
   `--fake-sensor` (simulate rising water without hardware), `--offline` (queue only).

## API contract (SOSora Command backend, default http://<command-box>:8000)
- Voice: `POST /api/radio/audio` multipart form: `file` (WAV), `beacon_id=beacon-ww-bridge`,
  `source_type=beacon`. Response includes `transcript`, `parse`, `assessment`, `state`.
- Water level: `POST /api/beacon/beacon-ww-bridge/reading` JSON
  `{"water_level_cm": 42.0, "threshold_cm": 30, "measured_at": "<iso8601>"}`.
  Over threshold -> the agent blocks the bridge with source `beacon_sensor`.
- Text fallback: `POST /api/radio` JSON `{"message": "...", "source_type": "beacon", "lon": .., "lat": ..}`.
- Registry: `GET /api/beacons`.
- Demo fallback with no ASR server: a file named `demo_hero.wav` maps to the cached SIMULATED
  hero transcript (`backend/app/asr.py`). Record yourself saying the hero line and name it that.

## Speech to text
`backend/app/asr.py` calls any OpenAI-compatible `/audio/transcriptions` server at
`ASR_BASE_URL`. Preferred: an NVIDIA speech model (Parakeet / NVIDIA ASR NIM) served on our
Brev GPU. Ask organizers to confirm ASR does not count toward the 33B generative-LM cap.

## Acceptance (check these off in docs/CONTEXT.md)
- [x] `python beacon/beacon.py --fake-sensor --server http://localhost:8000` makes the bridge
      go `blocked` and 5 SOS pins go unreachable (after `POST /api/radio/demo/seed`).
- [x] `--replay demo_hero.wav` produces the same result through `/api/radio/audio`.
- [ ] Pull the network: items queue; restore it: they send once each (no duplicates).
- [ ] Real mic + real sensor work on the Pi.

## Video shots
Hand speaks into the mic -> Pi terminal "SENT" -> dashboard bridge turns red, pins flip.
Pour water into the container -> sensor line -> same. Unplug Wi-Fi -> "QUEUED" -> plug in -> "SENT".

## Running the client

Laptop demo needs Python 3 and `python -m pip install requests`; GPIO imports are lazy.
On the Pi, install `beacon/requirements.txt` and `alsa-utils`. The client uses the CLI
flags above; `config.example.json` is a reference, not an automatically loaded config.

Seed Command first, with the backend in `DEMO_MODE=true`:

```sh
curl -X POST http://localhost:8000/api/radio/demo/seed
python beacon/beacon.py --fake-sensor --server http://localhost:8000
```

Fake water starts at zero and rises to the mounting height. Terminal lines and persisted
records say `[SIMULATED]` / `simulated: true`. Keep Command in demo mode too: its current
reading endpoint derives source simulation labels from `DEMO_MODE`, not the posted flag.
The client sends readings on either threshold crossing and on the heartbeat; a falling
reading never requests that a road reopen. Ctrl-C retains unsent items.

Replay a recording with its original filename (the filename `demo_hero.wav` selects the
backend's labeled cached hero transcript when ASR is absent):

```sh
python beacon/beacon.py --replay /path/to/demo_hero.wav --offline
python beacon/beacon.py --flush --server http://localhost:8000
```

`--replay` copies and queues a new item, then retries until acknowledged. `--offline`
with replay queues and exits. `--flush` resumes existing items without recording, reading
GPIO, or enqueuing another copy. With `--fake-sensor --replay ...`, both flows run until
Ctrl-C. Default outbox is `beacon/outbox/`; use `--outbox PATH` for an isolated queue.
Acknowledged JSON receipts and WAVs are retained in `outbox/sent/`. Queue and recordings
are git-ignored. Only one process can own an outbox. Backoff survives restart.

For real hardware, omit `--fake-sensor`; Enter records eight seconds from `plughw:1,0`.
Use `--audio-device` to change the microphone, and `--button` to enable GPIO17.

**Delivery guarantee:** persistent at-least-once delivery, stable UUID `client_id` and
`Idempotency-Key` on retries, and no resend after a durable local acknowledgement.
The existing backend audio/reading endpoints do **not** implement idempotency. If Command
processes an upload but its response is lost (or the Beacon crashes before saving the
receipt), a retry can create duplicate backend events. Exactly-once acceptance remains
pending backend deduplication; ordinary disconnected-before-send recovery is verified.

## Verification

```sh
ml/.venv312/bin/python -m pytest beacon/tests -q
PYTHONPATH=backend:. ml/.venv312/bin/python beacon/verify_demo.py
```

The second command starts an isolated Command server and temporary database using the real
OSM graph. It exercises the fake-sensor CLI, replay CLI, and a failed connection followed
by restart/reconnect; results are saved in `beacon/evidence/demo_verification.json`.
Its generated silent WAV tests cached transcription only, not real speech recognition.
Real microphone, ultrasonic sensor, GPIO button, and physical Wi-Fi unplug remain Pi checks.

## Real USB microphone without a water sensor

Pi recording verified by Ria on 2026-10-18: Sizheng/JMTek USB MIC, ALSA card 3/device 0;
`vcgencmd get_throttled` returned `0x0`. Use the stable ALSA card name where available:

```sh
# On Pi (after copying the updated beacon.py from the Mac)
cd ~/beacon
source .venv/bin/activate
python beacon.py --voice-only --audio-device plughw:MIC,0 --server http://192.168.68.80:8000
```

Press Enter, speak for eight seconds, then watch QUEUED → SENT and the Command dashboard.
This mode starts no water sensor and emits no simulated water readings. Recordings are
real audio; describe exercise reports as simulated incidents. Stop older Beacon processes
first. Card numbers can change across boots; `arecord -l` identifies the current device.

### Local speech recognition on Command (Mac)

The optional CPU ASR sidecar serves Whisper `tiny.en` (published size 39M parameters),
using faster-whisper int8. Nemotron remains the sole reasoning/tool-calling model. This
is a smaller ASR alternative to the unserved 618M Parakeet, not an NVIDIA ASR claim.
Sources: https://github.com/openai/whisper and https://github.com/SYSTRAN/faster-whisper.
Download weights once while online; startup uses a local directory and will not download.

```sh
# Mac, repo root; one-time preparation
ml/.venv312/bin/python -m pip install -r beacon/requirements-asr.txt
ml/.venv312/bin/python -c "from faster_whisper.utils import download_model; download_model('tiny.en', output_dir='ml/artifacts/asr-tiny.en')"
# Keep running in its own terminal (localhost only)
ml/.venv312/bin/python -m uvicorn beacon.asr_server:app --host 127.0.0.1 --port 8003
```

Restart Command with its usual model-provider settings plus:
`ASR_BASE_URL=http://127.0.0.1:8003 ASR_MODEL=tiny.en`.
The existing `/api/radio/audio` transcribes the WAV, then runs the same radio agent and
broadcasts state updates. No transcript prompt supplies bridge names. Arbitrary live
recordings fail visibly if ASR is unavailable and remain queued on Pi; only explicitly
named `demo_hero.wav` can use the existing cached SIMULATED fallback.

For an already recorded clip, no client update is needed:

```sh
# Pi: this is actual audio transcription when the ASR server is running
cd ~/beacon
source .venv/bin/activate
python beacon.py --replay ~/mic-test.wav --server http://192.168.68.80:8000
```

For arbitrary microphone reports, run Command and the ML parser with `DEMO_MODE=false`
and the existing live Nemotron settings. `DEMO_MODE=true` only recognizes named cached
fixtures; it does not parse arbitrary speech. Seed the dashboard's simulated SOS incidents before a bridge demo. Example exercise line:
“Exercise report. Warren Wilson Road bridge has collapsed. Road impassable. Three families
are stranded on the far side.” Keep each eight-second report short. A replay uses real
speech recognition too; it is prerecorded audio, not a live microphone capture.
