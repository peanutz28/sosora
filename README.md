# SOSora

When roads disappear and signals fail, rescue can't stop.

Hackathon demo for the NVIDIA × Red Hat Small Models Hack. The map is a labeled simulation on real western North Carolina road geography. It is not a dispatch system, and a graph path is not a statement that a road is safe.

## Run

```bash
cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
```

Open http://127.0.0.1:3000. Press `→` to advance the scenario and `R` to reset it.

The road graph is cached under `backend/data/` from OpenStreetMap on 17 October 2026. Rebuild it, after refreshing `backend/data/osm_raw.json`, with:

```bash
backend/.venv/bin/python backend/scripts/build_graph.py
```

## What is real

- The drive network is OpenStreetMap, routed with NetworkX.
- Closures remove those edges. The next path is computed again. If none exists, the status is unreachable and no line is drawn.
- SOS reports are stored in SQLite. The same `client_id` does not create a second incident.
- Imagery is Esri World Imagery Wayback. The swipe labels the mosaic release dates (19 September 2024 and 30 January 2025). Those are not a co-registered before/after pair.

## What is simulated

- Rescue 4, the objective, the SOS text, and the damage polygon are fixtures.
- The damage polygon is not a model score. Confidence is omitted on purpose.
- The interpretation panel is a local template while `DEMO_MODE=true`.
- Published Helene figures in the sidebar are case context, not live telemetry.

## Model service

Your teammate owns `ml/` and the service on port 8001. This app does not modify that tree. Contracts are in `contracts/README.md`.

```bash
DEMO_MODE=true
ML_SERVICE_BASE_URL=http://127.0.0.1:8001
NEXT_PUBLIC_APP_API_URL=http://127.0.0.1:8000
```

## Tests

```bash
cd backend && .venv/bin/pytest
```
