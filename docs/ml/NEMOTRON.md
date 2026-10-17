# Nemotron incident workflow

The API implements real OpenAI-compatible provider requests for `POST /ml/incident/parse`
and `POST /ml/incident/explain`. There is no mock fallback in production.
A real hosted Nemotron incident parse was verified through the local console on
October 17, 2026 using an explicitly fictional report. This establishes integration,
not extraction accuracy or production reliability. Mocked contract tests alone do not
establish provider availability. No Red Hat deployment has been verified.

Configure `LLM_PROVIDER=nvidia_api` with `NVIDIA_API_KEY`; its default API base is
`https://integrate.api.nvidia.com/v1`. `LLM_MODEL` overrides the default configured model.
For `LLM_PROVIDER=redhat_vllm`, both `LLM_API_KEY` and an explicit `LLM_BASE_URL`
are required; there is no fallback to NVIDIA. Configuration health does not establish
network reachability, model availability, quota, or provider authentication success.
Do not put secrets in URLs, reports, checked-in files, or logs.

For the local frozen-model demo, save provider settings in ignored `ml/.env`, then run:

```sh
ml/.venv312/bin/python scripts/ml/run_native_api.py
```

The launcher reads only allowlisted provider settings as data, never executes the file,
and binds to `127.0.0.1:8002`. It preserves the native checkpoint, metrics and image
manifest defaults. Restart after changing the file. Keys are not accepted by the page.
`/ml/llm-health` deliberately reports configuration only (`configured_unverified`),
not a background paid inference or a guarantee that the next request will succeed.

NVIDIA requests use streamed answer deltas, JSON mode and disabled thinking for the
configured Nemotron 3.5 Lightning model, with the model's recommended sampling.
The service validates the complete JSON with Pydantic and rejects truncated output,
unknown evidence references, oversized responses and requests exceeding 90 seconds.
It returns when the provider marks the answer complete rather than waiting for the
stream connection to close. Red Hat retains its existing non-streaming protocol.
These settings follow the [NVIDIA model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4)
and [NVIDIA structured JSON example](https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started-nemotron-3.5-lightning.html#structured-json-output).

`parse` accepts `{ "report": "..." }` and returns the existing incident schema.
`explain` accepts `incident` (the parsed incident object) and `road_evidence`, a nonempty
list of objects containing unique `evidence_id`, `observation`, `source`, and optional
numeric `confidence` between zero and one. Its `explanation` object contains prose,
known `evidence_ids`, explicit `uncertainty`, and `review_status: unverified`.
Evidence may describe vision observations but must not conflate water/road overlap
with a validated flooded-road prediction. Supply source provenance in `source`.

The system instruction forbids invented coordinates, official closures, and safe-route
claims. Strict schema validation and evidence-reference checking reject malformed
outputs and unknown citations. These checks cannot prove semantic factuality: a human
must review every response. Never use generated prose as a routing or closure authority.
Provider errors/timeouts and invalid outputs yield 502; missing configuration yields 503.

After approved credentials are present, run the opt-in real smoke command:

```sh
ml/.venv312/bin/python scripts/ml/incident_smoke.py --env-file ml/.env --report 'Water reported near a road; location not supplied.'
# Or: --explain-json /path/to/request.json
```

This command makes a hosted inference request and may consume provider quota. It fails
explicitly without configuration, prints only validated JSON on success, and does not
persist credentials. Do not claim provider success until this real check succeeds.
