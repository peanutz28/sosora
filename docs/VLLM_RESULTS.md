# Brev / vLLM execution evidence

Status: complete. Five final hero runs passed, all Gym/throughput requests recorded, and H100 shutdown verified.

## Provisioning

The authenticated Brev GPU catalog was queried on 2026-10-17 ET. Saved quote:
[`evidence/vllm_2026-10-17/gpu_quotes.json`](evidence/vllm_2026-10-17/gpu_quotes.json).
Selected `gpu-h100-sxm.1gpu-16vcpu-200gb`: one NVIDIA H100 80GB, 16 vCPUs,
200 GiB RAM, requested 200 GB disk. Quoted compute: $5.40/hour; disk:
$0.12264/GB-month. This is a quote, not an invoice. The instance is stoppable;
stopped disks continue to accrue storage charges. No instance URL or credential
is stored in this repository.

Observed root disk: 120 GB block device / 116G filesystem, despite the 200 GB
request. The model cache therefore uses the VM's 99G `/dev/shm` tmpfs. This
consumes host RAM and is lost on stop; restarting requires downloading weights
again. This is a temporary hackathon serving setup, not durable deployment.

## Serving recipe

Exact deployment command and flags: [`../scripts/vllm/serve_brev.sh`](../scripts/vllm/serve_brev.sh).
Uses the official upstream `vllm/vllm-openai:v0.27.1` image and NVIDIA's BF16
checkpoint. It does **not** establish use of a Red Hat-distributed image or bounty
eligibility. `redhat_vllm` is SOSora's configured provider adapter name.

Sources: [NVIDIA BF16 model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16),
[vLLM reasoning configuration](https://github.com/vllm-project/vllm/blob/main/docs/features/reasoning_outputs.md),
[Brev instance creation](https://docs.nvidia.com/brev/cli/instance-creation).
The model card's single-H100 BF16 recipe supplies the Mamba flags and parsers.
The experiment limits context to 16,384 and concurrency to 32, disables thinking
by default, enables API-token authentication, and preserves the served alias
`nvidia/nemotron-3.5-lightning-30b-a3b`. No second generative model is loaded.
The model's bundled chat template is used; no custom template is substituted.
Final server configuration additionally sets `VLLM_ENFORCE_STRICT_TOOL_CALLING=false`.
This selects native model tool markup rather than server-side structural grammar;
backend Pydantic argument checks, code-enforced trust, and Gym's HTTP tools/verifier
still validate results. Frozen request tool schemas remain unchanged.
See [vLLM strict tool calling](https://docs.vllm.ai/en/latest/features/tool_calling/).

## Integration fixes found by live execution

- SOSora's vLLM adapter now uses native `tool_choice=auto` with `qwen3_coder`;
  the hosted adapter retains `required`. The native probe returned a valid
  `find_segments` call in 1,219 ms (`native_tool_probe.json`). The initial
  forced-decoding hero attempt was interrupted before any completed run; it is
  recorded in `aborted_required_hero.json` and is not an accuracy measurement.
- With native decoding, the first five complete hero runs applied the correct
  closure and computed five isolated incidents, but the final LLM request failed.
  They remain in `hero_before_context_fix.json`, with all five counted as failures.
  Full route geometry made the model context too large for the configured window.
  Model-facing reachability results now contain incident status, length, and edge
  count; complete geometry and edge IDs stay in backend state and tool events.
  A regression test checks both views. The final five-run benchmark follows this fix.

## Hero methodology

`benchmark_hero.py` posts to the real `/api/radio` route through FastAPI TestClient,
with a real HTTP ML parser and real agent inference at the vLLM endpoint.
Each run resets and seeds the same simulated incidents on real OSM roads.
It records total request time and wraps the real agent completion method only
to measure each model turn. Graph work is included in total time. Seed and initial
graph loading are outside the timed request. This is application latency, not
browser rendering latency. Five runs, preserving failures; no selective retries.
Success requires a live parse, five affected incidents and five actually
unreachable incidents, and no agent error/fallback event.

```sh
# Set secret runtime configuration outside Git; do not paste credentials into logs.
PYTHONPATH="$PWD/backend:$PWD" ml/.venv312/bin/python \
  scripts/vllm/benchmark_hero.py --runs 5 \
  --output docs/evidence/vllm_2026-10-17/hero.json
```

## Final hero measurements

| Run | Total seconds | Agent turn seconds (1–6) | Correctly isolated |
|---|---:|---|---:|
| 1 | 13.044 | 1.921, 0.547, 0.563, 1.643, 0.430, 1.546 | 5/9 |
| 2 | 13.538 | 0.670, 0.540, 0.559, 1.038, 0.399, 1.611 | 5/9 |
| 3 | 12.298 | 0.637, 0.539, 0.559, 1.051, 0.397, 1.538 | 5/9 |
| 4 | 10.513 | 0.623, 0.536, 0.584, 1.076, 0.402, 1.440 | 5/9 |
| 5 | 12.817 | 0.628, 0.615, 0.549, 1.052, 0.483, 1.395 | 5/9 |

All five final runs passed. Mean total: **12.442 seconds**. Mean agent call: **0.852 seconds** across 30 calls (range 0.397–1.921 seconds).
Full traces: [`hero_final_native.json`](evidence/vllm_2026-10-17/hero_final_native.json).
The earlier five successful native-auto runs before changing server structural-grammar behavior are retained in `hero.json`.
Inputs/incidents are simulated; inference, OSM search, closures and reachability are real.
All final runs used live parses, six real agent calls, and no fallback assessment.

Final strict-native probe: missing token HTTP 401; correct token HTTP 200; valid tool call in 1,108 ms.
Brev access stayed private; requests used an SSH tunnel and model token.

Local verification: 30 backend tests and 25 Gym integration tests passed; commands and results are in `local_checks.json`.

The first validation-only Gym infrastructure attempt used structural grammar
for the frozen `strict: true` tools. It was stopped after slow recommendation
calls and a provider timeout, before opening test. Partial traces remain at
`ml/nemo_gym/evidence/vllm_strict_diagnostic_2026-10-17/`; they are not the final
comparison. The final run uses native parsing, with no change to the runner,
tasks, policies, tool schemas, or verifier.

## Gym comparison

All 56 final scenarios completed, with 343 model calls and zero provider errors.
Validation: baseline 8/14; evidence_first 2/14. Test: baseline 7/14;
evidence_first 4/14. The frozen evidence-first prompt did not improve on baseline.
These are simulated-task verifier scores, not real rescue safety accuracy.
No weights changed and no RL was performed. Full hosted-versus-vLLM tables,
latency caveats, failure counts and commands are in [`GYM_RESULTS.md`](GYM_RESULTS.md).
Frozen source hashes and server settings are in
`ml/nemo_gym/evidence/vllm_2026-10-17/protocol.json`.

## Parse throughput surge

100 requests per batch to the real `/ml/radio/parse`, seven repeated simulated
fixture texts, no response cache. Sequential ran first with prefix caching enabled;
concurrent requests therefore benefit from warm prefixes. Latencies include queue
time after each request starts, but sequential requests wait outside that timer.
This measures throughput and HTTP/parse completion, not semantic extraction accuracy.

| Client concurrency | Successful / attempted | Elapsed seconds | Messages/s | p50 seconds | p95 seconds |
|---:|---:|---:|---:|---:|---:|
| 1 | 100/100 | 84.766 | 1.180 | 0.777 | 1.149 |
| 100 | 100/100 | 20.609 | 4.852 | 16.981 | 19.801 |

The server schedules at most 32 sequences at once; client concurrency 100 includes
the model queue. Higher throughput comes with higher per-request burst latency.
All attempt latencies and statuses: [`surge.json`](evidence/vllm_2026-10-17/surge.json).

```sh
PYTHONPATH="$PWD" ml/.venv312/bin/python scripts/vllm/benchmark_surge.py \
  --output docs/evidence/vllm_2026-10-17/surge.json
```

## Shutdown

Brev reported the H100 **STOPPED** at 2026-10-17 23:51:19 EDT, before
the brief's 2026-10-18 10:00 AM ET cutoff. The temporary local ML API exited.
The disk is retained and continues to incur storage charges; no invoice total
was measured. The RAM-backed model cache is lost on stop.
Evidence: [`shutdown.json`](evidence/vllm_2026-10-17/shutdown.json).

## Resume and stop (local workstation)

The generated `.env.vllm` is local, ignored, and mode 0600. It contains the model
API token and loopback tunnel configuration. Source it without printing it.
The remote token file persists on the stopped VM; no token needs to be committed.

```sh
ml/tools/brev start sosora-lightning-vllm
ml/tools/brev exec sosora-lightning-vllm @scripts/vllm/serve_brev.sh
# Keep the tunnel in its own terminal:
ml/tools/brev port-forward sosora-lightning-vllm -p 18080:8000
# In the application terminal:
set -a
source .env.vllm
set +a
ml/.venv312/bin/python -m uvicorn ml.inference.app:app --host 127.0.0.1 --port 18002
# Run the application/benchmarks from another terminal with the same private env.
# Stop the cloud VM as soon as it is idle:
ml/tools/brev stop sosora-lightning-vllm
```

The deployment script recreates the temporary model-cache directory before
starting the retained container. Wait for `/health` and a successful authenticated
probe before the demo. Stopping compute retains the disk and its storage charge.
