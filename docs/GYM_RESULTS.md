# NeMo Gym: hosted API versus Brev vLLM

All scenarios are simulated. Same frozen tasks, policies, custom chat-completions
runner and pinned official NeMo Gym tools/verifier; this is not the full Gym CLI.
No weights were updated and no RL was performed. Both policies run on validation
before either runs on test; test data does not tune the policy.

| Serving | Split | Policy | Pass / requested | Provider errors | Mean recorded request ms |
|---|---|---|---:|---:|---:|
| Hosted NVIDIA API | validation | baseline | 1/14 | 7 | 4536.8 |
| Hosted NVIDIA API | validation | evidence_first | 7/14 | 3 | 1633.6 |
| Hosted NVIDIA API | test | baseline | 1/14 | 5 | 1336.5 |
| Hosted NVIDIA API | test | evidence_first | 4/14 | 8 | 1425.2 |
| Brev vLLM | validation | baseline | 8/14 | 0 | 427.4 |
| Brev vLLM | validation | evidence_first | 2/14 | 0 | 532.1 |
| Brev vLLM | test | baseline | 7/14 | 0 | 403.4 |
| Brev vLLM | test | evidence_first | 4/14 | 0 | 520.6 |

Hosted results contain transport failures; they do not isolate policy quality.
Recorded request means include HTTP error responses but exclude timeouts that the
original runner did not append to its latency list. They are not latency means
over every attempt; error counts and raw traces must be considered alongside them.
Serving comparisons also change checkpoint precision and backend defaults. The vLLM
server disables thinking by default; the unmodified Gym runner has no per-request
thinking flag. Server structural grammar is disabled for native tool parsing; frozen
strict tool schemas are unchanged and HTTP tools/verifier validate arguments.
Do not attribute all score changes to transport or call this RL.

## Reproduce

```sh
# Export private LLM configuration and these existing runtime paths:
# GYM_PYTHON, GYM_OFFICIAL, GYM_OUTPUT (fresh directory).
bash scripts/vllm/run_gym.sh
python3 scripts/vllm/summarize_gym.py --new ml/nemo_gym/evidence/vllm_2026-10-17
```

New evidence: `ml/nemo_gym/evidence/vllm_2026-10-17`. Each run saves rollout traces, metrics and configuration.
Failed scenarios remain in the requested denominator; no selective retries.

## Frozen task hashes

- `ml/nemo_gym/data/validation.jsonl`: `95cc3e20a782cd11c73c1ce5211b5fbdf9df5f867844472ed472b6abde643650`
- `ml/nemo_gym/data/test.jsonl`: `2b86c0e594b586f733a03f23ae5e607dfaa02a5182e4a1111a921945a8587e3b`

## VLLM verifier failures

| Split | Policy | Verifier issue | Scenario count |
|---|---|---|---:|
| validation | baseline | `incorrect_reachability` | 2 |
| validation | baseline | `invalid_tool_arguments` | 3 |
| validation | baseline | `invented_graph_version` | 2 |
| validation | baseline | `missing_human_review` | 3 |
| validation | baseline | `missing_required_tools` | 2 |
| validation | baseline | `require_exactly_one_recommendation` | 2 |
| validation | baseline | `route_tool_before_current_status` | 2 |
| validation | baseline | `stale_graph_version` | 2 |
| validation | baseline | `unsupported_path` | 2 |
| validation | evidence_first | `invented_graph_version` | 1 |
| validation | evidence_first | `missing_required_tools` | 10 |
| validation | evidence_first | `require_exactly_one_recommendation` | 10 |
| validation | evidence_first | `route_tool_before_current_status` | 2 |
| validation | evidence_first | `stale_graph_version` | 2 |
| validation | evidence_first | `unsupported_path` | 1 |
| test | baseline | `incorrect_reachability` | 2 |
| test | baseline | `invalid_tool_arguments` | 1 |
| test | baseline | `invented_graph_version` | 2 |
| test | baseline | `missing_human_review` | 2 |
| test | baseline | `missing_required_tools` | 3 |
| test | baseline | `require_exactly_one_recommendation` | 2 |
| test | baseline | `route_tool_before_current_status` | 2 |
| test | baseline | `stale_graph_version` | 2 |
| test | baseline | `unsupported_path` | 4 |
| test | evidence_first | `incorrect_reachability` | 1 |
| test | evidence_first | `invalid_tool_arguments` | 3 |
| test | evidence_first | `invented_graph_version` | 2 |
| test | evidence_first | `missing_human_review` | 1 |
| test | evidence_first | `missing_required_tools` | 7 |
| test | evidence_first | `require_exactly_one_recommendation` | 7 |
| test | evidence_first | `route_tool_before_current_status` | 2 |
| test | evidence_first | `stale_graph_version` | 2 |

Counts can overlap within a scenario. A verifier failure is distinct from a provider error.
A lack of HTTP errors does not establish correct rescue recommendations.
These frozen runs do not justify claiming evidence_first is an improved model or policy.
The verified production hero flow uses its separate guarded agent loop.
