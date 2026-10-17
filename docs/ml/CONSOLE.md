# SOSora interactive local demo

Open http://127.0.0.1:9030 . The existing static training viewer has been upgraded to a live ML console. The original detailed snapshot is preserved at `/training.html`; `build_training_viewer.py` now writes that snapshot without overwriting the interactive homepage.

## Fine-tuning demonstration

Open http://127.0.0.1:9030/fine-tuning.html (also linked from Training and Evidence). Two selectable validation tiles each show the original image, reference flood labels, saved initialization prediction and tuned prediction on an identical native pixel grid. Class colors, opacity and the independent-road-ROI outline are shared. Both saved checkpoints are re-run only for inference; generated confusion counts must exactly reproduce the saved validation evaluation. No training or frozen-Germany inference/tuning runs.

The baseline is a pretrained SegFormer encoder/decoder plus a random two-class head, not a pretrained flood detector. The page explains all-weight adaptation, sample counts, checkpoint selection, per-image versus two-tile validation metrics, the constant all-flood control, and both major frozen Germany failures. The positive validation image alone scores worse than the all-flood control; that comparison remains visible. Generated assets stay under ignored `assets/finetuning/`.

Regenerate separately with `ml/.venv312/bin/python -m scripts.ml.build_finetuning_demo`. Console startup also prepares this comparison; the CPU inference preparation can take roughly a minute on this machine. Original `training.html` remains available.

## What is interactive

- Three georeferenced scenes: NOAA Chimney Rock October 7 2024, NC Swannanoa spring 2025 recovery, and a SpaceNet 8 Louisiana validation tile from Hurricane Ida 2021.
- Live `POST /ml/predict` through a fixed same-origin localhost proxy to the existing trained model on port 8002. Initial overlays are explicitly labeled saved real results; completed requests switch to live status with actual latency.
- Pan, zoom, source-versus-prediction comparison, road geometry layer, opacity, per-polygon inspection, and actual GeoJSON export. Class probabilities are not safety scores.
- Louisiana defaults to known-label versus prediction comparison. Saved error view uses green correct flood, amber false alarm, purple missed flood, with a persistent legend and snapshot status. This is validation data; no new external test images are displayed or used for tuning.
- Evidence view shows the frozen Germany evaluation, actual confusion counts and saved training curves. Reused Louisiana results remain clearly distinguished.
- Incident desk uses real Nemotron parsing and deterministic evidence briefs with exact supplied-record counts. Missing credentials are shown as unavailable; no fabricated model response or incident coordinates.

This is an ML demo and integration surface. No rescue routes, road-graph matching, official closures, hardware gateway, or authoritative damage labels were invented. Frontend/backend/shared contract files were not modified. Trained models and frozen evaluation evidence were not changed.

## Run

From repository root, start the native API in one terminal. It reads optional provider
settings from ignored `ml/.env` without printing them, and keeps the documented frozen
model/manifest/evaluation defaults:

```sh
ml/.venv312/bin/python scripts/ml/run_native_api.py
```

Start the console in another terminal:

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

No provider secret is requested or stored by the page. A real hosted Nemotron parse
was subsequently verified through the incident desk with a fictional report on
October 17, 2026. Configuration status alone does not verify provider availability;
every generated incident and brief still requires human review. See `NEMOTRON.md`
for private setup, bounded streaming behavior and the opt-in real smoke command.
