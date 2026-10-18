# SOSora

**Flood-response imagery and incident review — NVIDIA × Red Hat hackathon project.**

SOSora explores how responders could review possible flooded road regions alongside structured reports from people requesting help. Our working prototype combines a georeferenced image viewer, a fine-tuned vision model, an evidence-linked incident desk, and a separate synthetic tool-use environment. It exposes source dates, model identity, uncertainty and failure cases so a person can inspect the evidence.

**Current delivery:** a local ML console and FastAPI service, a completed small supervised vision pilot, a frozen cross-event evaluation, real hosted Nemotron incident parsing, and tested NeMo Gym resource-server integration. This is an exploratory prototype: it does not determine road closures, passability, safe routes or rescue decisions. Repository visibility remains private; this document is a submission draft, not evidence that the project has been submitted or that a sponsor track has accepted it.

## Working prototype

| Component | Implemented behavior and boundary |
|---|---|
| Interactive console | Real imagery; pan/zoom; reference-versus-prediction comparison; road overlays; polygon inspection; GeoJSON export; saved versus live status; evidence and training views. |
| Native vision API | FastAPI/Pydantic, PyTorch/Transformers SegFormer, Rasterio/Shapely geospatial processing. `POST /ml/predict` uses registered imagery and an **independent road ROI**, runs native 256px windows, and returns georeferenced candidate polygons with provenance. It classifies flood state inside road corridors; it is not a full-scene road extractor. |
| Incident parsing | `POST /ml/incident/parse` calls hosted NVIDIA Nemotron through an OpenAI-compatible API, then validates structured JSON. A fictional report was verified through the browser. Human review is still required. |
| Evidence brief | `POST /ml/incident/explain` now computes deterministic counts and cites supplied region IDs, without an LLM call. It covers only supplied records, not unique roads or the full image, and does not connect an incident to a road or infer route safety. |
| NeMo Gym | A separate official-core resource server, synthetic road-graph scenarios, verifier and bounded custom chat-completions runner. Protocol integration is tested; real agent rollouts and learning are not yet demonstrated. |

The local console uses HTML/CSS/JavaScript and a loopback Python server on **9030**, with an allowlisted same-origin proxy to the ML API on **8002**. The separate Gym service uses **8012**. This checkout contains `ml/`, `scripts/ml/`, `data/` and `docs/ml/`; an integrated teammate frontend/backend, hardware gateway, live emergency feed and production deployment have not been verified here. The console is the demonstrated integration surface.

## Vision experiment: what was actually trained

The selected native-v2 pilot starts from `nvidia/segformer-b0-finetuned-ade-512-512`, pinned to revision `489d5cd81a0b59fab9b7ea758d3548ebe99677da`. Its ADE20K backbone/decoder is pretrained; the task-specific two-class head is randomly initialized. The saved initialization control is **not a pretrained flood detector**. Full adaptation trains all **3,714,658 parameters**, including backbone, decoder and binary head.

| Protocol | Completed pilot |
|---|---|
| Data | SpaceNet 8 Louisiana East, Hurricane Ida 2021: 8 training, 2 validation and 4 reused evaluation tiles, with spatial acquisition-group splits. |
| Supervision | Official road centerlines buffered by four source pixels; non-flooded/flooded classes; unlabeled/conflicting pixels ignored as 255. Post-event RGB is warped to the pre-event label grid; residual alignment error remains. |
| Native crops | 53 training / 11 validation crops, each 256×256. Overlapping label-centred crops are correlated, not independent samples. |
| Optimization | CPU, two threads, batch 4, seed 42, AdamW. Two preset candidates: frozen backbone, learning rate 0.0002, 6 epochs; full adaptation, learning rate 0.00005, 10 epochs. Each had a 180-second training budget after setup, checked between batches. |
| Selection | Highest completed crop-validation F1; full adaptation selected epoch 9, F1 **0.61423**, with best weights restored. Full validation-tile F1 is **0.52955**, a different evaluation support. Full adaptation took 147.7 seconds. |
| Identity | Run `2c66a49a-fb5a-4d56-9d5d-7142d42f57b2`; checkpoint SHA256 `3ab85783b140ec6ebfac7ad45cf78cb38e6b668c082b053d15ef3edcd20ee69b`. Native inference uses 256px windows/stride and fixed binary argmax (flood threshold 0.5). |

An earlier downsampled pilot is retained for diagnosis. Its scores must not be compared directly with the native-crop results because image scale and labeled support changed. See the [training protocol](docs/ml/evidence/native_cpu_protocol.json), [run metadata](docs/ml/evidence/native_cpu_v2/run_metadata.json) and [pilot methodology](docs/ml/evidence/sn8_pilot/methodology.json).

### Results on identical support

Each row compares the same saved initialization, selected tuned checkpoint and constant all-flood control on the same labeled road pixels. F1/IoU are positive-class pixel metrics, not road-level safety measures.

| Evaluation | Control/model | F1 | IoU | Precision | Recall |
|---|---|---:|---:|---:|---:|
| Reused Louisiana: 4 tiles, 61,304 road pixels | Initialization | 0.18577 | 0.10239 | 0.16270 | 0.21646 |
| Same support | Tuned | **0.67418** | **0.50850** | 0.55441 | 0.85995 |
| Same support | All flood | 0.43367 | 0.27687 | 0.27687 | 1.00000 |
| Frozen Germany: 6 tiles, 72,961 road pixels | Initialization | 0.23083 | 0.13047 | 0.15633 | 0.44103 |
| Same support | Tuned | **0.46626** | **0.30401** | 0.40188 | 0.55521 |
| Same support | All flood | 0.07709 | 0.04009 | 0.04009 | 1.00000 |

**Louisiana is not a pristine holdout.** Earlier outputs/images informed diagnosis; the native candidates were selected without consulting new native-test outputs, but the four evaluation tiles had already been used. Germany is a small label-blind cross-event convenience sample, not the official competition benchmark: six tile IDs were frozen before new label interpretation, with no replacements, retraining, threshold adjustment or checkpoint reselection afterward.

Germany contained only 2,925 flooded labeled pixels and two flood-positive tiles. Tuned counts were **TP 1,624 / FP 2,417 / FN 1,301 / TN 67,619**. All false positives occurred on one dry tile; another tile's 726 positive pixels were entirely missed. Aggregate improvement therefore does not establish consistent reliability. The fine-tuning page also exposes a validation image where the all-flood control beats the tuned model. [Complete external evidence and failure accounting](docs/ml/FROZEN_EXTERNAL_EVALUATION.md), [raw evaluation](docs/ml/evidence/frozen_external/evaluation.json), [native results](docs/ml/RESULTS_NATIVE_CPU.md).

## Imagery, provenance and limits

| Source | Actual use |
|---|---|
| SpaceNet 8 Louisiana / Germany | 2021 flood-event training/evaluation, **not Helene**. Dataset license is CC BY-SA 4.0; exact tile capture dates remain unverified. |
| NOAA NGS Chimney Rock | October 7, 2024 response mosaic. Unchanged model produced 27 flooded-road and 3 non-flooded-road candidate polygons at threshold 0.5. All are unverified; no Helene ground truth or accuracy score exists. |
| NC Helene Orthoimagery, Swannanoa | **Spring 2025 recovery** imagery, not immediate September 2024 conditions. Source metadata reports no unusual flooding and cautions against detailed pixel-value analysis. Resampled exploratory transfer only. |
| NCDOT roads | Independent June 2026 road centerlines for NC demo ROIs. Temporal mismatch and missing local/private roads limit coverage; inference ROI does not use flood labels. |

Clouds, haze, shadows, registration error, buffered-label width and sparse road-only supervision can create false alarms and misses. Probability is not a calibrated safety score. Narrow road support excludes off-road errors; tiles and pixels are correlated. No current conditions, official closures, validated Helene damage assessment or operational safety is established.

[Source registry](docs/ml/SOURCES.md), [pitch/source distinctions and NOAA redistribution caveat](docs/ml/PITCH_PROVENANCE.md), [Helene road provenance](docs/ml/HELENE_ROADS.md). Preserve attribution and inspect selected NOAA layer terms before redistributing imagery. Model weights, source rasters and generated viewer imagery remain local ignored artifacts; cloning this private repository does **not** provide them. Model redistribution terms remain to be reviewed.

## Language, tools and infrastructure status

- **Nemotron:** real hosted parsing was verified using `nvidia/nemotron-3.5-lightning-30b-a3b` with streaming, JSON mode and thinking disabled; a 90-second overall deadline and strict schema validation bound requests. Earlier non-streaming calls timed out. The fictional browser smoke proves connectivity, not extraction accuracy. A generated brief showed semantic errors, so the current evidence brief uses deterministic counts instead. [Setup/behavior](docs/ml/NEMOTRON.md), [sanitized live smoke](docs/ml/evidence/nemotron_live_smoke_20261017.json), [deterministic brief evidence](docs/ml/evidence/deterministic_brief_smoke_20261017.json).
- **NeMo Gym:** genuine v0.6.0 core at `3045a793346a31291d7ea4ae6af3f94a35036ce5`, with all 149 upstream Git blobs verified; 25 tests, seven scripted protocol cases and separate HTTP smoke passed. Included synthetic CC0 scenarios contain 28/14/14 train/validation/test rows. The custom runner uses the real verifier, but no real LLM rollout, baseline agent score, RL/SFT update or model improvement has been measured; this is not a claim of running the complete upstream CLI harness. [Gym instructions](ml/nemo_gym/README.md), [integration evidence](ml/nemo_gym/evidence/integration_smoke.json), [network evidence](ml/nemo_gym/evidence/network_smoke.json).
- **Red Hat / vLLM:** a configurable authenticated OpenAI-compatible provider path exists; no actual Red Hat deployment, served vLLM model or benchmark is verified.
- **Brev:** no paid GPU was started for the documented work. CLI help succeeded on retry, but supported Chrome inspection stalled and ended with `Transport closed`. Current instance state, 48GB availability, hourly quote, credits and storage charges remain unverified. Historical rates are not a current quote or spending authorization.

## Run the local demonstration

Run from repository root. The validated vision environment is Python 3.12; dependencies are pinned in [ml/requirements.txt](ml/requirements.txt). An initial environment can be created with:

```sh
python3.12 -m venv ml/.venv312
ml/.venv312/bin/python -m pip install -r ml/requirements.txt
```

**Prerequisite:** restore or reproduce the local checkpoint, registered source rasters and independent road masks described in the [integration guide](docs/ml/TEAMMATE_INTEGRATION.md). These are not bundled downloads. Installation alone does not recreate the prepared demo. Source preparation/training instructions and manifests are retained in `scripts/ml/`, `data/manifests/` and the evidence documents; there is no one-command fresh-clone reproduction claim.

In separate terminals:

```sh
ml/.venv312/bin/python scripts/ml/run_native_api.py
```

```sh
ml/.venv312/bin/python scripts/ml/console_server.py --port 9030
```

Open **http://127.0.0.1:9030**; API docs: **http://127.0.0.1:8002/docs**. The aligned four-panel comparison is at `/fine-tuning.html`; detailed historical snapshot at `/training.html`. Console asset preparation may take roughly a minute and performs inference only. Startup does not train, provision a GPU or publish a site. Current process uptime is not guaranteed.

For incident parsing, configure private provider settings in ignored `ml/.env` as documented in [NEMOTRON.md](docs/ml/NEMOTRON.md), then restart the API. The launcher reads only allowlisted values without shell execution or printing credentials. Do not commit keys. Missing configuration returns unavailable; there is no fabricated provider fallback. Hosted calls may consume provider quota.

```sh
PYTHONDONTWRITEBYTECODE=1 ml/.venv312/bin/python -m pytest ml/tests -q
```

Last verified ML suite: **94 passed**, including the V3 preparation/comparator tests. The historical demo suite had 85 tests. Gym's 25 tests run in its separate official-core environment; see its README. Browser QA covered live imagery inference, actual GeoJSON download, reference/error views, fictional incident parsing, and desktop/mobile layout. These checks do not validate operational accuracy. [Console guide](docs/ml/CONSOLE.md), [comparison checks](docs/ml/evidence/fine_tuning_comparison_check.json).

## Prepared next experiment — no new training result

V3 preparation is complete locally; its experimental source, tests and sanitized summary are included in this branch. Raw preparation data remains local. The reviewed set contains **80 training / 19 development tiles**, producing **544 / 99 native crops**. Thirty-eight geographically separated final IDs remain sealed; no final masks or post-event imagery were prepared. Shared reference CSVs already existed locally, so sealing means this pipeline skips final records before interpreting their flood attributes, not that the global annotations have never existed on the machine.

Actual footprints verify at least 1,000m split separation; historical tile IDs are excluded. Preparation uses **1,259.2 MiB**, below the approved 2 GiB cap. Six tiles lacked usable supervision, five failed a bright/cloud screen, and fourteen alignment-flagged pairs were visually reviewed and conservatively quarantined without claiming registration correction. Unflagged samples can still contain errors. The final 38 tiles occupy two geographic blocks within known events, not 38 independent sites or unseen events.

A four-level random-initialized U-Net (1,962,642 parameters) and SegFormer comparator runner are implemented locally. Only short CPU throughput checks ran; **no V3 checkpoint, score or improvement exists**. At batch 4 and 20 epochs, observed timings project approximately 52–153 minutes for U-Net and 73–75 minutes for SegFormer training alone, plus validation/loading and thermal margin. These are estimates, not guaranteed completion times. Full training remains held pending the compute decision. The runner binds full training to the reviewed manifest hash and rejects final/test data.

See the [V3 protocol and preparation plan](docs/ml/V3_EXPERIMENT_PLAN.md), [sanitized preparation receipt](docs/ml/evidence/v3_preparation_summary.json), [comparator usage](ml/experiments/README.md) and [preparation source](scripts/ml/prepare_v3_experiment.py).

## Remaining plan, in priority order

1. Decide local CPU versus a verified GPU quote and explicit spending/runtime cap. Do not provision from an unverified historical rate; account for persistent storage and confirmed shutdown controls.
2. Review the prepared V3 protocol and training budgets, train the supervised comparators, and choose settings/checkpoints using development data only. Document initialization/capacity differences and justify learning rates rather than assuming equal optimization.
3. Freeze the complete selected protocol, then open and evaluate the sealed final set once, retaining failures and controls. Do not tune on the historical frozen Germany result or the new final result.
4. Integrate verified ML contracts into the teammate dashboard/backend; improve cloud/alignment and road-coverage handling. Expand independent evaluation before any operational claim.
5. Run bounded real Gym agent baselines and evaluate tool-use behavior before claiming optimization. Keep vLLM/Red Hat deployment secondary to a stable vision endpoint and credible vision evidence.
6. Prepare the pitch and reproducible public artifacts only after approval, provenance/licensing review and secret checks. Confirm organizer track/bounty eligibility, model terms and submission requirements. Repository publication and event submission remain separate actions requiring authorization.
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
