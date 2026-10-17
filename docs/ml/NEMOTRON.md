# Nemotron incident workflow

The API uses a real OpenAI-compatible provider for `POST /ml/incident/parse`.
`POST /ml/incident/explain` renders a deterministic evidence brief without a provider call.
Neither endpoint uses a mock fallback.
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
`explain` accepts an optional legacy `incident` field (unused) and one to thirty `road_evidence` records with unique
`evidence_id`, `observation`, `source`, optional numeric `confidence`, and optional
`prediction_class` (`flooded_road` or `non_flooded_road`). A missing class is counted as
unclassified, never inferred from prose. It returns exact counts in `evidence_summary`,
a fixed explanation and all supplied IDs. Counts cover only supplied region records,
not unique roads or the full image. The console supplies at most the first twelve regions.

The brief does not synthesize observation text, compare models, infer disagreement,
associate an image with an incident, or establish passability, closures or safe routes.
It returns `inference_mode: deterministic`, null provider/model, and unverified status.
It works without provider credentials. Incident parsing still requires human review:
strict JSON validates shape, not factuality. Provider failure yields 502; missing parse
configuration yields 503. Duplicate IDs or invalid evidence classes yield 422.

After approved credentials are present, run the opt-in real smoke command:

```sh
ml/.venv312/bin/python scripts/ml/incident_smoke.py --env-file ml/.env --report 'Water reported near a road; location not supplied.'
# Or: --explain-json /path/to/request.json
```

The --report command makes a hosted inference request and may consume provider quota.
The --explain-json command renders the deterministic brief without a hosted request. It fails
explicitly without configuration, prints only validated JSON on success, and does not
persist credentials. Do not claim provider success until this real check succeeds.

## Observed live brief limitation

The browser evidence-brief request also completed with schema-valid output citing only
supplied evidence IDs. Its prose nevertheless miscounted region records and interpreted
different region classes as disagreement between multiple models. Schema and citation
validation do not establish semantic correctness. Keep briefs unverified, inspect their
claims against the supplied records, and do not pitch this smoke as factuality validation.

The observed live brief errors motivated replacing generated evidence prose with exact
structured counts and a fixed template. The earlier hosted brief is historical evidence
of connectivity only; current briefs are explicitly deterministic.
