# NeMo Gym integration status — 2026-10-17

Source and instructions: [ml/nemo_gym/README.md](../../ml/nemo_gym/README.md).

Implemented and validated against the genuine NVIDIA NeMo Gym v0.6.0 resource-server core, commit `3045a793346a31291d7ea4ae6af3f94a35036ce5`. Official source files were downloaded and all 149 Git blob hashes checked. New code subclasses `SimpleResourcesServer`, `BaseRunRequest`, `BaseVerifyRequest`, and `BaseVerifyResponse` directly. There is no replacement or mocked Gym implementation.

25 tests pass, including session isolation, official response schemas, stale graph versions, closed-edge rejection, missing evidence/tools, malformed arguments, and provider-failure boundaries. Seven scripted HTTP smoke cases pass; their complete traces and upstream identity are in `ml/nemo_gym/evidence/integration_smoke.json`. These fixtures do not measure model performance.

Generated data is included under `ml/nemo_gym/data`: 28 train, 14 validation, 14 test scenarios, CC0-1.0, with source code and methodology. Node counts differ by split; prompt IDs are opaque so they do not reveal scenario class. Only the server can access the authoritative graph/labels through the catalog. The agent prompt receives an ID and six tool definitions. These are synthetic graph tasks, not real field accessibility labels. The files have not been pushed or published externally.

The actual agent runner requires `NVIDIA_API_KEY` or an explicitly configured Red Hat provider. It uses a custom chat-completions loop with the genuine Gym resource server and verifier, not the complete upstream CLI harness. Missing credentials prevent requests. No real language-agent rollout, baseline score, RL/SFT update, or model improvement is claimed. Bounty eligibility for prompt-only optimization remains unconfirmed.

The isolated resource runtime is currently `/private/tmp/sosora-gym-work/venv`, and official source is `/private/tmp/sosora-gym-work/official`. It uses Python 3.14.3 and is separate from the vision Python 3.12 environment. Recreate a persistent core runtime with `python3 ml/nemo_gym/bootstrap.py`; it downloads hash-verified upstream core and installs `requirements-core.lock`. The full upstream Gym CLI requires a separate full installation with more disk space. Disk was about 1.3 GB free after core installation; no model weights or GPU allocation were added by this work.

For the current runtime, from repository root:

```sh
PYTHONPATH="$PWD:/private/tmp/sosora-gym-work/official" \
  /private/tmp/sosora-gym-work/venv/bin/python -m pytest ml/nemo_gym/tests -q

PYTHONPATH="$PWD:/private/tmp/sosora-gym-work/official" \
  /private/tmp/sosora-gym-work/venv/bin/uvicorn ml.nemo_gym.app:local_app \
  --factory --host 127.0.0.1 --port 8012
```

Official references: [Gym release](https://github.com/NVIDIA-NeMo/Gym/tree/v0.6.0), [official multi-step example](https://github.com/NVIDIA-NeMo/Gym/tree/v0.6.0/resources_servers/example_multi_step), and [documentation](https://docs.nvidia.com/nemo/gym/).

The real server is running at http://127.0.0.1:8012/docs . A separate network smoke saved in `ml/nemo_gym/evidence/network_smoke.json` confirms HTTP 200 for session creation, incident retrieval, road status, and reachability. The existing vision service on port 8002 remained healthy.
