# Brev / vLLM execution evidence

Status: provisioning; no latency or vLLM accuracy result claimed yet.

## Provisioning

The authenticated Brev GPU catalog was queried on 2026-10-17 ET. Saved quote:
[`evidence/vllm_2026-10-17/gpu_quotes.json`](evidence/vllm_2026-10-17/gpu_quotes.json).
Selected `gpu-h100-sxm.1gpu-16vcpu-200gb`: one NVIDIA H100 80GB, 16 vCPUs,
200 GiB RAM, requested 200 GB disk. Quoted compute: $5.40/hour; disk:
$0.12264/GB-month. This is a quote, not an invoice. The instance is stoppable;
stopped disks continue to accrue storage charges. No instance URL or credential
is stored in this repository.

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

Pending: measured results, provider readiness, shutdown verification.
