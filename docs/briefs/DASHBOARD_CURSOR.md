# Dashboard brief for Cursor (owner: Jia)

Read `docs/CONTEXT.md` first. Work in `frontend/` only. Backend runs on :8000
(`cd backend && uvicorn app.main:app --port 8000`, DEMO_MODE=true needs no API keys).

## Goal
The command dashboard is where the hero moment happens on camera: a radio report arrives,
a real bridge turns red, and SOS pins north of the river flip to "cut off". It must look
like mission control at 2 AM in a command vehicle, not a startup landing page.

## Look ("night operations")
- Base `#0A0E14`, panels `#111821`, satellite map desaturated + darkened.
- Status colors only when they mean something: blocked `#FF3B30`, contested/unverified
  `#FFB020`, open/reachable `#2DD4BF`. Live AI activity (radio waveform, agent trace,
  incoming messages) electric cyan `#22D3EE`. Everything else grayscale.
- Type: IBM Plex Sans (UI), IBM Plex Mono (times, ids, coordinates).
- Signature animations: cyan waveform when a radio message arrives; red shockwave ripple from
  the bridge when it closes; counter "5 families cut off" ticking up.

## Data you already get (WebSocket `/ws/events` and `GET /api/state`)
- `{"type":"state","state":{...}}`: `state.incidents[]` has `id, lon, lat, message,
  people_affected, medical, reachable (bool, after a radio report), route`.
  `state.closures` = closed road features (the blocked bridge appears here automatically).
- `{"type":"agent_event","event":{kind:"agent_tool_call"|"agent_tool_result"|"agent_error", tool, arguments|result}}`
  -> the **agent trace panel** (one row per tool call: tool name, short args, short result).
- `{"type":"radio_event","event":{kind:"radio_received"|"radio_parsed"|"voice_transcribed"|"sensor_reading"|"radio_location_confirmed", message, ...}}`
  -> the **radio ticker**.
- `GET /api/radio/status`: per-segment status (`blocked|contested|unverified|open_official`)
  with sources, the latest agent assessment, and reachability per incident.

## Build, in this order (check each off in docs/CONTEXT.md)
1. **Demo controls** (small, hideable for the video): buttons that call
   `POST /api/radio/demo/seed`; "Beacon voice report" = `POST /api/radio`
   `{"message": <hero_message from seed>, "source_type":"beacon", lon, lat from beacon_position}`;
   "Responder radio (no location)" = same without lon/lat; "DOT says open" = `open_report`;
   "Water sensor spike" = `POST /api/beacon/beacon-ww-bridge/reading {"water_level_cm":45}`.
2. **SOS pins** colored by `reachable` (teal) vs not (red), with a count "N cut off".
3. **Radio ticker**: newest radio_event at top, cyan waveform animation on arrival.
4. **Agent trace panel**: stream agent_event rows live. This is how judges *see* tool calling.
5. **Needs-review card**: when the assessment says `needs_human_review` and find_segments
   returned several candidates, show them on the map with a "Confirm this bridge" button ->
   `POST /api/radio/confirm {"radio_id", "lon", "lat"}` using the candidate centroid.
6. **Provenance popover** on a blocked road: list of sources (type, time, text).
7. Polish, then the resident SOS app (only if 1-6 are done).

## Rules
- Label simulated data "SIMULATED" in small text. Never show a phone with signal bars.
- Don't edit `backend/` or `ml/`; if you need a field, write it in Open issues in CONTEXT.md.
