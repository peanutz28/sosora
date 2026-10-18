# NeMo Gym: hosted API versus Brev vLLM

All scenarios are simulated. Same frozen tasks, policies, custom chat-completions
runner and pinned official NeMo Gym tools/verifier; this is not the full Gym CLI.
No weights were updated and no RL was performed. Both policies run on validation
before either runs on test; test data does not tune the policy. The Oct 18
follow-up below develops one new policy using validation only.

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

## Oct 18: validation-developed grounded_v2 (frozen before test)

One new policy, three validation revisions. Only system prompt and tool descriptions changed. Runner configuration plumbing selects that file; model weights, tool schemas, sampling, execution loop, task rows and verifier stay fixed. Lightning BF16 ran on the same Brev H100 80 GB, quoted **$5.40/hour** before restart; retained disk costs $0.12264/GB-month. No RL or fine-tuning was performed. All cases are simulated.

| Split | Policy/revision | Pass / requested | Provider errors |
|---|---|---:|---:|
| validation | baseline (fresh) | 5/14 | 0 |
| validation | grounded_v2 R1 | 4/14 | 0 |
| validation | grounded_v2 R2, selected | 10/14 | 0 |
| validation | grounded_v2 R3 | 10/14 | 0 |
| test | baseline, one invocation | 6/14 | 0 |
| test | frozen grounded_v2 R2, one invocation | 10/14 | 0 |

Fresh paired test improvement: **4/14 cases, +28.6 percentage points** (42.9% to 71.4%). The previous baseline test was 7/14; report the fresh paired comparison, not a mixture of runs. Sampling remains temperature 1.0, max_tokens 1024, no parallel tool calls, 12 turns and 60-second request timeout; results vary between runs. This small, previously used test split does not establish broad generalization. No test retries or policy changes followed test inspection.

### Diagnosis and policy selection

Validation baseline fails on argument formatting, unsupported paths, version/tool order after status failures, and missing-location handling. Earlier evidence_first often failed to submit a valid final recommendation. R1 expanded these instructions but scored worse (4/14). R2 uses a concise decision tree, positive complete submission examples, exact observed versions and candidate paths, no stale-route inference, and explicit final tool submission. It sends every assessment to human review: conservative, but unnecessary review is not penalized by this verifier and operator workload was not measured. R3 added explicit native XML null syntax without improving reward; select earlier, simpler R2.

Final validation family/verifier breakdown (counts overlap):

| Family | Fresh baseline | Selected R2 | R2 verifier issues |
|---|---:|---:|---|
| bridge_closed | 1/2 | 2/2 | none |
| two_roads_closed | 2/2 | 2/2 | none |
| alternate_route | 1/2 | 2/2 | none |
| isolated | 0/2 | 2/2 | none |
| tool_failure | 0/2 | 0/2 | invalid_tool_arguments: 2, missing_required_tools: 2, require_exactly_one_recommendation: 2 |
| conflicting_evidence | 1/2 | 2/2 | none |
| missing_location | 0/2 | 0/2 | invalid_tool_arguments: 2, missing_required_tools: 2, require_exactly_one_recommendation: 2 |

All four R2 validation failures submit the string `"None"` for graph_version instead of JSON null. That makes the final recommendation invalid; missing-required-tool and exactly-one-valid-recommendation issues follow. R3 still failed these families. Saved parser-source excerpts are diagnostic only: the exact raw-generation versus conversion origin is not established. No parser, schema or verifier fixes were made to improve the score.

### One-shot test breakdown

| Family | Baseline | grounded_v2 |
|---|---:|---:|
| bridge_closed | 1/2 | 2/2 |
| two_roads_closed | 2/2 | 2/2 |
| alternate_route | 2/2 | 2/2 |
| isolated | 1/2 | 2/2 |
| tool_failure | 0/2 | 0/2 |
| conflicting_evidence | 0/2 | 2/2 |
| missing_location | 0/2 | 0/2 |

Paired outcomes: 6 both pass, 4 policy-only pass, 0 baseline-only pass, 4 both fail. Detailed overlapping verifier counts and raw failures remain in `test_family_analysis.json` and each rollout file.

### Evidence and reproduction

Root: `ml/nemo_gym/evidence/grounded_v2_2026-10-18/`. `experiment_plan.json` precedes selection; `selection.json` and all validation snapshots were committed in **269abc4 before test**. `test_invocation_ledger.json` records the two allowed invocations. Frozen tasks/verifier/serving hashes are in `selection.json` (task hashes unchanged from the table above). Each run saves its prompt, metrics and complete tool trajectory. Regression tests: **26 passed**, including a fake provider against real Gym tools/verifier and baseline configuration-preservation checks.

```sh
# With private LLM env exported and official NeMo Gym on PYTHONPATH:
python -m ml.nemo_gym.evaluate_agent --split test --policy baseline --limit 14 --max-turns 12 --max-seconds 14400 --output /path/to/fresh/baseline
python -m ml.nemo_gym.evaluate_agent --split test --policy grounded_v2 --limit 14 --max-turns 12 --max-seconds 14400 --output /path/to/fresh/grounded_v2
```

These commands document reproduction; the saved experiment invoked each exactly once. This uses the custom chat-completions runner with pinned official NeMo Gym resource-server tools and verifier, not the full Gym CLI. The provider label `redhat_vllm` is historical configuration; the container is upstream vLLM, not a verified Red Hat distribution. GPU shutdown verification is saved separately; disk remains billable.
