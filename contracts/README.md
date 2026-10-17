# SOSora contracts

The dashboard talks only to the FastAPI app. The FastAPI app is the only process that calls the model service.

## Application

- `GET /health`
- `GET /api/scenarios`
- `POST /api/scenarios/reset`
- `POST /api/scenarios/advance`
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

Expected on `ML_SERVICE_BASE_URL` (default `http://127.0.0.1:8001`).

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
