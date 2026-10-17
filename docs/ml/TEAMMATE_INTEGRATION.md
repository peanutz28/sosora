> **Updated generalization check:** frozen, label-blind six-tile Germany evaluation reached F1 **0.466**, IoU **0.304**, versus saved initialization F1 **0.231**. The earlier Louisiana F1 **0.674** is a reused four-tile within-event result, not a pristine holdout. Swannanoa remains unmeasured transfer. See [FROZEN_EXTERNAL_EVALUATION.md](FROZEN_EXTERNAL_EVALUATION.md) for all counts, errors and provenance.

# Current working native demo

Open http://127.0.0.1:9030 for the interactive ML console: select actual imagery, run the local model, inspect candidate road highlights and compare known labels. The detailed saved training view is at `/training.html`; rebuild that view with `ml/.venv312/bin/python scripts/ml/build_training_viewer.py`. This ML console is separate from the teammate routing app. See `CONSOLE.md` for the server command and `REPOSITORY_SCOPE.md` for excluded local resources.

The native flood service is running on **127.0.0.1:8002**. The older ADE service on8001 was preserved. Use `sn8_road_validation_10400100684A4B00_1_17_85` for validation visualization or `helene_swannanoa_roads_spring2025` for explicitly unmeasured Swannanoa transfer. Discover all allowlisted IDs via `/ml/images`.

```sh
curl --fail http://127.0.0.1:8002/ml/predict -H 'Content-Type: application/json' \
  -d '{"image_id":"helene_swannanoa_roads_spring2025","threshold":0.5}'
```

To recreate the native service after stopping it (from repository root; choose an unused port if8002 is occupied):

```sh
PYTHONDONTWRITEBYTECODE=1 HF_HOME=ml/.cache/huggingface HF_HUB_OFFLINE=1 \
OMP_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 \
VISION_MODEL=ml/artifacts/sn8_native_cpu_v2/model \
ML_METRICS_PATH=ml/artifacts/sn8_native_cpu_v2_evaluated \
ML_IMAGE_MANIFEST=data/manifests/native_demo.json \
ml/.venv312/bin/uvicorn ml.inference.app:app --host 127.0.0.1 --port 8002
```

Restart the process after configuring language-provider secrets; no live Nemotron call has run yet. Endpoints `/ml/incident/parse`, `/ml/incident/explain`, `/ml/llm-health` are available in the new service. See `NEMOTRON.md`.

Measured test F1 is0.674 versus0.186 for the same initialized binary model before training, on four tiny same-event road-corridor tiles. This is not Helene accuracy. Model positives on spring2025 recovery imagery can be false alarms. See `RESULTS_NATIVE_CPU.md` for protocol, evidence and limitations.

# SOSora ML integration

The FastAPI service accepts an allowlisted image ID and returns real segmentation polygons. Frontend and backend owners can consume this interface without changing ML source files. Predictions require human review and do not establish road closure, safety, accessibility, or routing decisions.

## Start an isolated local service

Run from the repository root. Port 8011 is an example for a new service; check that it is free first. Leave any existing service alone.

```sh
HF_HOME="$PWD/ml/.cache/huggingface" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
VISION_MODEL=nvidia/segformer-b0-finetuned-ade-512-512 \
VISION_REVISION=489d5cd81a0b59fab9b7ea758d3548ebe99677da \
ML_IMAGE_MANIFEST="$PWD/data/manifests/images.json" \
ML_METRICS_PATH="$PWD/ml/artifacts/sn8_pilot_run" \
ml/.venv312/bin/python -m uvicorn ml.inference.app:app --host 127.0.0.1 --port 8011
```

This uses already cached weights. Model loading happens on the first prediction; `/health` checks liveness only. A missing cached model should fail rather than trigger downloads in offline mode. For a trained flood checkpoint, replace `VISION_MODEL` with its absolute local model directory and use the matching manifest and evaluation directory. The checkpoint requires an independently produced road ROI per registered image. Never use flood ground-truth masks as inference ROIs or tune thresholds from held-out test results.

## Inspect and predict

```sh
curl --fail http://127.0.0.1:8011/health
curl --fail http://127.0.0.1:8011/ml/images
curl --fail http://127.0.0.1:8011/ml/model-info
curl --fail http://127.0.0.1:8011/ml/metrics
```

Copy an `image_id` from `/ml/images`, then send it in the JSON request:

```sh
curl --fail http://127.0.0.1:8011/ml/predict \
  -H 'Content-Type: application/json' \
  -d '{"image_id":"REPLACE_WITH_ALLOWLISTED_IMAGE_ID","threshold":0.65}'
```

The server never accepts arbitrary file paths in prediction requests. Unknown IDs return 404; invalid request thresholds return 422; unavailable imagery, model resources, or mandatory road ROIs return 503. See `/openapi.json` for the live contract.

## Save a complete local demo

The runner contacts all five routes, requires `inference_mode=real`, and saves raw responses, WGS84 `detections.geojson`, a source-aligned `overlay.jpg`, and `summary.json`. It refuses an existing output directory. Replace the image ID and output path for each run.

```sh
ml/.venv312/bin/python scripts/ml/demo_smoke.py \
  --image-id REPLACE_WITH_ALLOWLISTED_IMAGE_ID \
  --output /tmp/sosora-new-demo
```

The default uses the repository cache at `ml/.cache/huggingface` (an explicit `HF_HOME` overrides it) and runs the API in its own process through TestClient using the cached ADE20K baseline; it does not start or alter an existing service. To call an existing service instead, add `--url http://127.0.0.1:8011`. In URL mode the local `--manifest` must match that server's registrations so the runner can render the actual source raster. To run a flood checkpoint in process, use `--model /absolute/path/to/model --metrics-path /absolute/path/to/run --manifest /absolute/path/to/images.json`. Configuration is established before importing the API. The runner never trains or starts GPU instances.

## Fields and display rules

- `image_id`, `image_width`, and `image_height` identify the registered source image.
- `crs=EPSG:4326` means polygon coordinates are longitude/latitude. Pixel-coordinate predictions cannot be exported by this runner as georeferenced GeoJSON.
- Each detection has `class`, polygon `geometry`, mean selected-pixel `confidence`, and `review_status=unverified`. Confidence is model probability, not calibrated safety certainty. Empty `road_segment_ids` mean no road-network association has been made.
- ADE20K classes such as `road`, `water`, `river`, and `bridge` describe scene semantics; water near a road does not establish a flooded road.
- The binary flood task describes flood state **within road corridors**. Class 0 is `non_flooded_road`; class 1 is `flooded_road`. Class 0 does not mean generic background or verified passability. Pixels outside the independent road ROI are excluded.
- `model_provenance` records model, checkpoint, run, task, label map, ROI requirement, and identity verification. `/ml/model-info` distinguishes configured metadata from a loaded model's captured metadata.
- `/ml/metrics` preserves `baseline` and `fine_tuned` results while identifying the evaluated and served models. Show evaluation accuracy as applying to current predictions only when `metrics_apply_to_served_model=true`. Legacy evaluation evidence lacks verified provenance and remains explicitly unassociated. The random binary head baseline is not ADE20K scene-segmentation accuracy.
- Overlay colors: red flooded road, green non-flooded road, yellow road, blue water/river, purple bridge. All overlays remain unverified predictions.

Keep frontend/backend implementation with their owners. Coordinate shared API contract changes before integrating; no backend, frontend, or shared contract edits are required by this handoff. Use validation data for model selection and freeze the test split for final reporting; do not feed test observations back into training decisions.
