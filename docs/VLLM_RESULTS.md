# Brev / vLLM execution evidence

Status: authenticated serving verified; five final hero runs passed; Gym rerun in progress.

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

Pending: final Gym results, surge results, shutdown verification.
