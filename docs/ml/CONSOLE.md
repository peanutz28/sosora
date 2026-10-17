# SOSora interactive local demo

Open http://127.0.0.1:9030 . The existing static training viewer has been upgraded to a live ML console. The original detailed snapshot is preserved at `/training.html`; `build_training_viewer.py` now writes that snapshot without overwriting the interactive homepage.

## What is interactive

- Three georeferenced scenes: NOAA Chimney Rock October 7 2024, NC Swannanoa spring 2025 recovery, and a SpaceNet 8 Louisiana validation tile from Hurricane Ida 2021.
- Live `POST /ml/predict` through a fixed same-origin localhost proxy to the existing trained model on port 8002. Initial overlays are explicitly labeled saved real results; completed requests switch to live status with actual latency.
- Pan, zoom, source-versus-prediction comparison, road geometry layer, opacity, per-polygon inspection, and actual GeoJSON export. Class probabilities are not safety scores.
- Louisiana defaults to known-label versus prediction comparison. Saved error view uses green correct flood, amber false alarm, purple missed flood, with a persistent legend and snapshot status. This is validation data; no new external test images are displayed or used for tuning.
- Evidence view shows the frozen Germany evaluation, actual confusion counts and saved training curves. Reused Louisiana results remain clearly distinguished.
- Incident desk calls the existing real Nemotron parse/explain endpoints. Missing credentials are shown as unavailable; no fabricated model response or incident coordinates.

This is an ML demo and integration surface. No rescue routes, road-graph matching, official closures, hardware gateway, or authoritative damage labels were invented. Frontend/backend/shared contract files were not modified. Trained models and frozen evaluation evidence were not changed.

## Run

Keep the existing native service on port 8002 running with its documented model/manifest/evaluation settings. Then, from repository root:

```sh
ml/.venv312/bin/python scripts/ml/console_server.py --port 9030
```

The command prepares browser assets from the existing local GeoTIFFs and independent road masks, reprojected into a common Web Mercator display grid. It starts a loopback-only static server with an allowlisted proxy. It does not start a GPU, train, fetch new imagery, or publish anything. To prepare assets without serving:

```sh
ml/.venv312/bin/python scripts/ml/console_server.py --prepare-only
```

The main files are `docs/ml/viewer/index.html`, `console.css`, `console.js`, `console-data.json`, and `assets/`. Sources, capture dates, caveats and checkpoint identity remain accessible in the UI. Source rasters and masks stay in their existing artifact locations.

## Verification

Browser-tested image selection, real inference (30 Chimney Rock polygons at the frozen 0.5 threshold), candidate inspection, persistent validation/error legends, source metadata, evidence table, missing-provider behavior and GeoJSON download. Browser-exported GeoJSON was parsed and checked for 30 real, unverified features. Desktop 1440px and mobile 390px layouts were checked with no horizontal document overflow or broken visible images. Proxy error behavior was tested when the native service exited; it returned 503 and preserved the last successful overlay. Native service was restored with the unchanged model, manifest and evaluation configuration. Connection status refreshes every 20 seconds.

No provider secret is requested or stored by the page. Nemotron inference remains dependent on configuring the provider in the ML service environment. No live language-model response is claimed by this console until one actually succeeds.
