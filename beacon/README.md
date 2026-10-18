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
- [ ] `python beacon/beacon.py --fake-sensor --server http://localhost:8000` makes the bridge
      go `blocked` and 5 SOS pins go unreachable (after `POST /api/radio/demo/seed`).
- [ ] `--replay demo_hero.wav` produces the same result through `/api/radio/audio`.
- [ ] Pull the network: items queue; restore it: they send once each (no duplicates).
- [ ] Real mic + real sensor work on the Pi.

## Video shots
Hand speaks into the mic -> Pi terminal "SENT" -> dashboard bridge turns red, pins flip.
Pour water into the container -> sensor line -> same. Unplug Wi-Fi -> "QUEUED" -> plug in -> "SENT".
