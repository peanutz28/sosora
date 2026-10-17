# Nemotron incident workflow

The API implements real OpenAI-compatible provider requests for `POST /ml/incident/parse`
and `POST /ml/incident/explain`. There is no mock fallback in production.
No actual Nemotron call has been verified in this environment: credentials are absent.
Mocked contract tests establish request/response handling, not provider availability.

Configure `LLM_PROVIDER=nvidia_api` with `NVIDIA_API_KEY`; its default API base is
`https://integrate.api.nvidia.com/v1`. `LLM_MODEL` overrides the default configured model.
For `LLM_PROVIDER=redhat_vllm`, both `LLM_API_KEY` and an explicit `LLM_BASE_URL`
are required; there is no fallback to NVIDIA. Configuration health does not establish
network reachability, model availability, quota, or provider authentication success.
Do not put secrets in URLs, reports, checked-in files, or logs.

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
ml/.venv312/bin/python scripts/ml/incident_smoke.py --report 'Water reported near a road; location not supplied.'
# Or: --explain-json /path/to/request.json
```

This command makes a hosted inference request and may consume provider quota. It fails
explicitly without configuration, prints only validated JSON on success, and does not
persist credentials. Do not claim provider success until this real check succeeds.
