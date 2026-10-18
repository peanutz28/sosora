> **Updated generalization check:** frozen, label-blind six-tile Germany evaluation reached F1 **0.466**, IoU **0.304**, versus saved initialization F1 **0.231**. The earlier Louisiana F1 **0.674** is a reused four-tile within-event result, not a pristine holdout. Swannanoa remains unmeasured transfer. See [FROZEN_EXTERNAL_EVALUATION.md](FROZEN_EXTERNAL_EVALUATION.md) for all counts, errors and provenance.

# Real native-road demo — 2026-10-17

The selected local model is `ml/artifacts/sn8_native_cpu_v2/model`, run `2c66a49a-fb5a-4d56-9d5d-7142d42f57b2`, checkpoint `sha256:3ab85783b140ec6ebfac7ad45cf78cb38e6b668c082b053d15ef3edcd20ee69b`.

## What works now

- Visual viewer: http://127.0.0.1:9030 (saved snapshot, not live training). `docs/ml/viewer/index.html` is also openable directly. Validation images, true road labels, model overlays, errors and real curves are displayed. Held-out test images/results are excluded from the development viewer.
- Native flood API: http://127.0.0.1:8002/docs . The existing ADE20K service on 8001 was left untouched; it predates these updates. New service exposes seven allowlisted imagery registrations and requires independent road ROIs.
- Live network smoke: `ml/artifacts/demo_flood_native_live/` contains a genuine WGS84 flooded-road polygon, prediction JSON, overlay, API responses and verified metric association. Single CPU request was about 2.10 seconds, not a benchmark.
- Helene transfer: `ml/artifacts/demo_helene_native/` contains real Swannanoa recovery inference: 13 flooded-road and 6 non-flooded-road polygons. These are unverified zero-shot predictions. No Helene ground truth or accuracy exists; positives may be false alarms.

## Controlled experiment and measured results

53 native 256px training crops and 11 validation crops preserve road detail and original spatial split assignments. Crop preparation retained 188,070 sampled supervised training pixels versus 7,961 after old full-tile downsampling; overlapping crops are not independent observations. No mask expansion or fabricated labels was used. Original masks derive from four-pixel buffered official reference centerlines. Unlabeled pixels remain 255/ignored.

Two CPU-only presets ran sequentially, using two threads, batch size four and a 180-second training budget per run. Frozen encoder: 6 epochs, 39.6 seconds, best crop-validation F1 0.483. Full adaptation: 10 epochs, 147.7 seconds, best crop-validation F1 0.614 at epoch 9. Best weights were restored. No held-out test was evaluated during selection. Protocol and selection are saved under `docs/ml/evidence/native_cpu_*.json`.

The selected checkpoint and saved initialization control were then evaluated on identical native-resolution support, with no test threshold tuning:

| Four held-out tiles, 61,304 labeled road pixels | F1 | IoU | Precision | Recall |
|---|---:|---:|---:|---:|
| Random binary head on pretrained backbone/decoder | 0.18577 | 0.10239 | 0.16270 | 0.21646 |
| Fine-tuned native crop model | 0.67418 | 0.50850 | 0.55441 | 0.85995 |
| Predict every labeled road flooded | 0.43367 | 0.27687 | 0.27687 | 1.00000 |

The control is not a pretrained general-purpose flood detector. ADE20K has no flooded-road class and is a separate scene-segmentation demo, not a comparable flood-accuracy baseline. Do not compare the old pilot's 0.047 F1 directly with 0.674: image scale and labeled support changed. The valid measured comparison is the new baseline versus tuned model above.

Full validation-tile F1 is 0.52955; crop-validation F1 is 0.61423. These measure different sample support and are labeled separately in the viewer. Test results and imagery were seen during the earlier pilot diagnosis and informed preprocessing/error analysis. The two new configurations and selected epoch were chosen without new native-test outputs, but this reused four-tile set is not a pristine holdout or external benchmark. A new untouched spatial area/event is required for a stronger generalization claim. All data is one event with tiny geographic samples and known residual registration uncertainty. No deployment or road-safety accuracy is established.

Evidence: `docs/ml/evidence/native_cpu_v2/` and `ml/artifacts/sn8_native_cpu_v2_evaluated/`. Experiment outputs and the earlier pilot are preserved. Native evaluation uses the original 1300px masks, native 256px windows, and identical supports for all controls.

## Imagery provenance

Training, validation, quantitative test and ADE demo imagery are SpaceNet 8 Louisiana East, Hurricane Ida 2021—not Helene. Exact tile capture dates are unverified. Original post-event URLs are in image manifests and prediction source metadata; the dataset is CC BY-SA 4.0.

Swannanoa source is NC Helene Orthoimagery 2025, downloaded at EPSG:4326 bbox [-82.323,35.603,-82.313,35.613], 512×512. Service description says spring 2025 recovery imagery, leaf-off, no unusual flooding; not immediate September 2024 storm imagery. Exact tile date is unverified. Export resampling does not preserve the source's six-inch resolution. Road ROI comes independently from NCDOT June 2026 state-maintained centerlines, three-metre buffer in UTM17N; local/private roads may be absent and temporal mismatch remains. See `HELENE_ROADS.md` and saved query provenance. No flood labels were supplied as an inference ROI.

## Reproduce and integrate

See `TEAMMATE_INTEGRATION.md`. Crop preparation: `python -m scripts.ml.prepare_road_crops`. Experiment runner has explicit CPU, time, batch and native-tile controls; output must be new or empty. Native evaluator defaults to validation; final test requires `--split test`. Do not tune against the reported test results. Both the model and masks remain local; model redistribution terms and hackathon CV eligibility still need confirmation.

## Language and bounty status

Nemotron parse and evidence-bound explain endpoints are implemented and provider-contract tested. No API key is configured in this environment; no real provider inference is claimed. Set the appropriate secret in the service's environment, then run `scripts/ml/incident_smoke.py` for an actual call. No credential values should enter chat. No Red Hat server or benchmark exists.

Original SOSora chat independently integrated real official NeMo Gym v0.6.0 resource-server code under `ml/nemo_gym/`; it reports 25 tests, seven scripted verifier traces and network HTTP smoke. This is genuine Gym protocol integration, not real LLM rollouts or measured model improvement. Its independent service is on localhost8012; see `NEMO_GYM.md`.

No GPU restarts, paid resources, pushes, deployments, model/data publication, or teammate frontend/backend edits occurred during this work.
