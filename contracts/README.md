# SOSora contracts

The dashboard talks only to the FastAPI app. The FastAPI app is the only process that calls the model service.

## Application

- `GET /health`
- `GET /api/scenarios`
- `POST /api/scenarios/reset`
- `POST /api/scenarios/advance`
- `POST /api/scenarios/goto` with `{ "step": number }` replays the deterministic scenario to that step
- `GET /api/state`
- `GET /api/incidents`
- `POST /api/incidents`
- `GET /api/roads`
- `POST /api/routes/calculate`
- `POST /api/roads/closures`
- `POST /api/imagery/analyze`
- `GET /api/events`
- `POST /api/review`
- `GET /api/ml/status`
- `WS /ws/events`

`POST /api/incidents` is idempotent on `client_id`. A repeat returns the original incident and `duplicate: true`.

Route results use graph length in meters. They are not travel times. `status` is `ok`, `unreachable`, or `snap_failed`. An unreachable result has an empty geometry. The service does not invent a path.

## Model service

Expected on `ML_SERVICE_BASE_URL` (default `http://127.0.0.1:8002`).

- `GET /health`
- `GET /ml/model-info`
- `GET /ml/images`
- `POST /ml/predict`
- `GET /ml/metrics`
- `POST /ml/incident/parse`
- `POST /ml/incident/explain`
- `GET /ml/llm-health`

Predict requests use `image_id` and `threshold`. Geographic detections use EPSG:4326 polygons in `[longitude, latitude]`. Pixel-space coordinates are kept off the map.

With `DEMO_MODE=true` (the default) the scenario uses a local fixture and says so. It does not call the model service. Set `DEMO_MODE=false` to try the live service. If that service does not answer, routing still runs and the panel says the model is unavailable.

Do not edit `ml/`. That tree belongs to the model work.

## Radio, Beacon and agent (added Oct 17, 23:15)

- `POST /api/radio/demo/seed` -> resets and seeds 9 SIMULATED SOS incidents on real roads.
  Returns `hero_message`, `open_report`, `beacon_position`.
- `POST /api/radio` `{message, source_type: responder_radio|beacon|resident, unit?, lon?, lat?}`
  -> `{radio_id, parse, assessment, statuses, state}`. Runs Lightning parse + tool-calling agent.
- `POST /api/radio/confirm` `{radio_id, lon, lat}` -> operator resolves an ambiguous location.
- `POST /api/radio/audio` multipart `file, source_type, beacon_id?, unit?` -> speech to text, then as `/api/radio`.
- `POST /api/beacon/{beacon_id}/reading` `{water_level_cm, threshold_cm?, measured_at?}`.
- `GET /api/radio/status`, `GET /api/beacons`.
- WebSocket `/ws/events` adds `{"type":"agent_event"}` (tool calls/results) and
  `{"type":"radio_event"}` (radio_received, radio_parsed, voice_transcribed, sensor_reading,
  radio_location_confirmed).
