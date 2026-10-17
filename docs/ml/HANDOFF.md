# SOSora ML handoff

The interactive ML console runs at **http://127.0.0.1:9030** with the native inference API on **http://127.0.0.1:8002/docs**. Choose an actual image, run the model, inspect candidate road highlights, compare known validation labels, and export unverified GeoJSON. The detailed saved training view is at `/training.html`. This is the ML integration surface, separate from the teammate's routing application.

See [console setup](CONSOLE.md), [teammate API instructions](TEAMMATE_INTEGRATION.md), [source and pitch provenance](PITCH_PROVENANCE.md), and [repository publication scope](REPOSITORY_SCOPE.md).

## Verified results

- Native SegFormer-B0 training completed on local CPU. The selected epoch is 9 from 10; selection used validation only, with best-checkpoint restoration.
- A frozen, label-blind six-tile **Germany** cross-event check reached F1 **0.4663**, IoU **0.3040**, precision **0.4019**, recall **0.5552**. Its saved initialization control reached F1 **0.2308**. Substantial false alarms and missed floods remain. [Full evaluation](FROZEN_EXTERNAL_EVALUATION.md).
- The earlier Louisiana F1 **0.6742** is a reused four-tile within-event result; prior test results/images informed diagnosis. It is not a pristine holdout or deployment estimate.
- Real georeferenced predictions work for NOAA Chimney Rock **October 7, 2024**, NC Swannanoa **spring 2025 recovery**, and Louisiana/Ida validation imagery. Neither Helene sample has flood ground truth or measured accuracy. NCOneMap discourages detailed pixel-value analysis on its processed 2025 service.
- 72 core ML tests passed before this publication review. Official NeMo Gym resource-server integration separately passed 25 tests and scripted/network protocol smoke tests; no real language-agent rollouts or model improvement are claimed.

## API and provenance

Image IDs are allowlisted in `data/manifests/native_demo.json`; requests never accept paths or URLs. Prediction polygons are longitude/latitude in EPSG:4326 when georeferencing exists, otherwise declared pixel coordinates. Class 0 is non-flooded road, class 1 flooded road; neither establishes passability, closure or safety. Probabilities are uncalibrated. Road graph association and routing remain the teammate's responsibility.

Flood checkpoints require an independent single-channel binary road ROI on the exact image grid. Missing, malformed or empty ROIs fail explicitly before model inference. Flood ground-truth masks must not be used as inference ROIs. Unknown training/evaluation pixels remain 255 and ignored.

Model, checkpoint fingerprint, run and task identities are explicit. Metrics attach to the served model only when verified identities agree. They do not establish accuracy on every input image or region. Legacy evidence stays unverified. Changing environment variables does not replace an already loaded model: restart the service deliberately.

## Language integration

`POST /ml/incident/parse` uses a real OpenAI-compatible provider transport with strict validation. `/ml/incident/explain` now uses a deterministic template and exact structured region counts, without a provider request; its output stays unverified. Missing configuration returns 503; invalid upstream output or provider errors return 502. A real hosted Nemotron parse through the browser was verified on October 17, 2026 with a fictional report. This single integration smoke is not an accuracy benchmark; see [sanitized evidence](evidence/nemotron_live_smoke_20261017.json).

For NVIDIA use `LLM_PROVIDER=nvidia_api` and a secret `NVIDIA_API_KEY`. For Red Hat use `LLM_PROVIDER=redhat_vllm`, explicit `LLM_BASE_URL`, `LLM_MODEL`, and required secret `LLM_API_KEY`. Secrets belong only in the local environment or ignored `ml/.env`, never chat, logs or Git. [Nemotron workflow](NEMOTRON.md).

The configured Nemotron model has 30B total parameters (3B active); no additional generative model is selected. Vision is separate. Red Hat hosting/benchmarking is not verified. [Gym setup and limits](NEMO_GYM.md).

## Local execution and reproduction

Python 3.12 and pinned vision dependencies are recorded in `ml/requirements-lock.txt`. [Run commands](TEAMMATE_INTEGRATION.md) assume the local imagery, masks and checkpoints already exist. Training refuses nonempty output directories and supports CPU/thread/time limits, validation selection, native crops and a test-skipping mode. Evaluation defaults to validation; final test use is explicit. Do not tune against the frozen Germany results.

Downloaded rasters, weights, caches, virtual environments, credentials and generated viewer assets are deliberately excluded from Git. A fresh clone is source/reproducibility material, not a bundled trained-model deployment; recreate or privately supply these local resources and run `console_server.py --prepare-only` before serving. No model/data publication or shared-contract, frontend or backend edits are part of this branch.

## Remaining gates

- Actual Gym language-agent rollouts remain unverified; the successful hosted incident parse does not establish Gym performance.
- Red Hat requires a compatible real server, access and measured request evidence.
- Organizer confirmation is needed for CV-track eligibility, bounty improvement criteria and parameter-count rules.
- Model redistribution and imagery licensing must be cleared before public release.
- Infrastructure was previously stopped; no GPU operation, training or paid action is initiated by the console.
