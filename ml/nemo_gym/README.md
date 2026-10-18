# SOSora rescue accessibility — NeMo Gym resource server

This is a real `SimpleResourcesServer` subclass and `BaseVerifyRequest` / `BaseVerifyResponse` implementation against NVIDIA NeMo Gym v0.6.0, pinned to commit `3045a793346a31291d7ea4ae6af3f94a35036ce5`. It has no local imitation of those classes and no fallback if Gym is absent. Version 0.6.0 predates the hackathon's two-week source cutoff; v0.7.0 does not. Dependency eligibility and bounty weight-update requirements still need organizer confirmation.

Implemented endpoints: `/seed_session`, `/get_incident`, `/get_road_status`, `/calculate_candidate_routes`, `/check_reachability`, `/get_damage_evidence`, `/submit_recommendation`, and the official inherited `/verify`, `/aggregate_metrics`, `/reverify_mode`.

Seven scenario families cover a newly closed bridge, two closures, multiple possible paths, isolation, a status-tool failure, conflicting visual evidence, and missing location. Graphs are explicitly synthetic and do not make real rescue or road-safety decisions. Only open edges can appear in submitted candidate paths. Initial routes are stale. Tool failures require `unknown`, not `unreachable`. Missing locations require `needs_location`. Conflicting visual evidence requires human review, without overriding official closures. Every submission remains unverified.

## Current evidence

- 25 tests pass, including actual official Gym class/schema/middleware/HTTP integration.
- `evidence/integration_smoke.json` records seven scripted tool traces processed by the genuine `/verify` route. This is protocol validation, not an agent benchmark.
- No language model has been called, no agent score or model improvement has been measured, and no RL or weight update has been performed.
- No extra generative model selected. Intended Nemotron role remains 30B total parameters within the shared 33B budget.

## Setup

Keep this separate from the Python 3.12 vision environment. Python >=3.13.14 is required by the pinned upstream; tested here with Python 3.14.3. From repository root:

```sh
python3 ml/nemo_gym/bootstrap.py
```

Bootstrap downloads only official core source, verifies each file's Git blob hash, and installs the pinned core dependencies. This is a resource-server-only runtime; it does not install every optional package required by Gym's complete CLI/agent orchestration. It does not install model weights or require a GPU. Allow approximately 600 MB disk space. The upstream full installation recommends at least 5 GB free.

```sh
PYTHONPATH="$PWD:$PWD/ml/artifacts/nemo_gym_runtime/official" \
  ml/artifacts/nemo_gym_runtime/venv/bin/python -m pytest ml/nemo_gym/tests -q

PYTHONPATH="$PWD:$PWD/ml/artifacts/nemo_gym_runtime/official" \
  ml/artifacts/nemo_gym_runtime/venv/bin/python -m ml.nemo_gym.smoke

PYTHONPATH="$PWD:$PWD/ml/artifacts/nemo_gym_runtime/official" \
  ml/artifacts/nemo_gym_runtime/venv/bin/uvicorn ml.nemo_gym.app:local_app \
  --factory --host 127.0.0.1 --port 8012
```

Use a cookie jar across tool calls. Seed with an ID from `data/train.jsonl`; no graph/answer is exposed in the model prompt. Session state is scoped to the rollout cookie; verifier recomputes the result from the server's authoritative scenario catalog and supplied call trace. Do not deploy this simulation server publicly: it uses Gym's development session middleware and synthetic data.

## Data

`python -m ml.nemo_gym.scenarios ml/nemo_gym/data` regenerates 28 training, 14 validation, and 14 test rows with identical hashes. Methodology and SHA-256 hashes are in `data/methodology.json`. Synthetic graph topology sizes are separated between splits; scenario families are shared. All nodes and observations are invented, no real locations or private reports. Data is released under CC0-1.0 by this project. Files are included in Git-ready source; they are not yet published to a public repository.

## Actual agent evaluation when credentials are available

`evaluate_agent.py` implements a custom chat-completions agent using the real Gym resource server and verifier. It is not the upstream full Gym CLI harness. Configure the same `LLM_PROVIDER`, `LLM_MODEL`, and secret environment variables used by SOSora; keys are never stored in outputs. Default model is `nvidia/nemotron-3.5-lightning-30b-a3b`. Red Hat requires an explicit base URL and key. No provider is verified merely by configuration.

```sh
PYTHONPATH="$PWD:$PWD/ml/artifacts/nemo_gym_runtime/official" \
  ml/artifacts/nemo_gym_runtime/venv/bin/python -m ml.nemo_gym.evaluate_agent \
  --split validation --policy baseline --limit 3 --max-seconds 180 \
  --output ml/artifacts/gym_validation_baseline
```

Run `--policy evidence_first` on validation to compare the published tool-policy prompt. Lock the chosen policy before opening test rollouts. Use new output directories, preserve logs, and do not report prompt improvement as weight updates or RL. Missing credentials stop execution before any model call. Bounty eligibility for prompt-only changes is unresolved. For full Gym CLI integration or RL, follow the official upstream installation and agent tutorials; that integration has not been executed here.

Official references: https://docs.nvidia.com/nemo/gym/ and https://github.com/NVIDIA-NeMo/Gym/tree/v0.6.0/resources_servers/example_multi_step .
