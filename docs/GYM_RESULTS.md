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

## Follow-up: nullable argument compatibility (offline, no new model score)

Added opt-in `--argument-adapter nullable-null-v1` to the custom Gym runner.
Default remains `none`, preserving the original experiment. For scalar schemas
that explicitly permit null and forbid strings, it converts the exact strings
`"None"` or `"null"` to JSON null. It does not fill missing fields, coerce graph
version strings to integers, change statuses or routes, or relax the verifier.
Raw/effective arguments and individual edits are retained in `argument_audit`;
metrics/config explicitly label adapter-enabled runs as system compatibility work.
The saved parsed responses do not establish whether generation or serving created
the original mismatch; this is a boundary compatibility fix, not a proven vLLM bug fix.

Offline replay of the frozen R2 **validation calls** changes 10/14 accepted traces
to 14/14, editing exactly four null values through the unchanged official verifier.
Historical tool outputs remain historical: this replay checks call validity and is
**not** a fresh model evaluation or a replacement test result. The one-shot test
score remains **10/14 vs baseline 6/14**. No test rerun, GPU restart or new model
calls occurred. Fresh size-17 simulated cases use a fake provider and real Gym
HTTP tools/verifier to test both adapter modes and continued rejection of unsafe
recommendations. These are deterministic regression checks, not model performance.

Evidence: `ml/nemo_gym/evidence/null_adapter_2026-10-18/`. Reproduce the offline check:

```sh
# Official NeMo Gym and repository root must be on PYTHONPATH.
python scripts/vllm/replay_null_adapter.py --output /path/to/fresh/replay
python -m pytest ml/nemo_gym/tests -q
```

A new live system comparison needs fresh simulated evaluation cases, the adapter
applied equally to both policies, and a separately reported protocol. Neither
benchmark reasoning improvement nor a new 14/14 test result has been measured.

## Repeated four-way ablation — Oct 18

Frozen in commit **625bda8 before evaluation**. This compares exactly the original
baseline prompt/descriptions, grounded_v2 descriptions alone, grounded_v2 system
prompt alone, and grounded_v2 with both. The existing execution loop is unchanged:
a temporary config root selects each frozen JSON through its existing file loader;
the raw runner label is `grounded_v2` for every arm, while `ablation_run.json` records
the actual arm. Only prompt/tool-description contents differ. Parameter schemas,
verifier, task bytes, model checkpoint, sampling and serving settings are identical.
The optional nullable argument adapter is explicitly **off** for every run.

Three complete runs per policy per split: all 12 validation runs finished before
all 12 test runs. Arm order rotates by repetition, sequentially; no selective retries,
policy revisions or selection after test. The test split was evaluated previously,
including the earlier grounded_v2 experiment: **this is a spent benchmark, not a
fresh blinded holdout**. Model prefix caching stayed enabled. All scenarios are
simulated; repeated identical cases are not 42 independent emergency scenarios.

| Split | Policy | Passes in three runs /14 | Mean /14 | Range /14 | Mean % | Provider errors |
|---|---|---|---:|---|---:|---|
| validation | baseline | 5, 5, 8 | 6.00 | 5–8 | 42.9% | 0, 0, 0 |
| validation | tool_descriptions_only | 10, 10, 10 | 10.00 | 10–10 | 71.4% | 0, 0, 0 |
| validation | system_prompt_only | 10, 9, 10 | 9.67 | 9–10 | 69.0% | 0, 0, 0 |
| validation | grounded_v2 | 10, 10, 10 | 10.00 | 10–10 | 71.4% | 0, 0, 0 |
| test | baseline | 6, 7, 8 | 7.00 | 6–8 | 50.0% | 0, 0, 0 |
| test | tool_descriptions_only | 8, 10, 9 | 9.00 | 8–10 | 64.3% | 0, 0, 0 |
| test | system_prompt_only | 10, 10, 10 | 10.00 | 10–10 | 71.4% | 0, 0, 0 |
| test | grounded_v2 | 10, 10, 10 | 10.00 | 10–10 | 71.4% | 0, 0, 0 |

All **336 scenario attempts** completed, with **zero provider errors**. Test mean
improves from 7/14 (50.0%) baseline to 10/14 (71.4%) with prompt-only or both:
**+21.4 percentage points**. Descriptions alone average 9/14 (64.3%). Combining
both changes shows no further test gain over prompt-only in these three runs.
This is evidence of configuration-sensitive tool behavior on this small benchmark,
not a weight-training/RL result or broad rescue accuracy claim. The conservative
all-human-review policy remains unpenalized for unnecessary operator workload.
The full policy still fails the two tool-failure and two missing-location cases;
the separate null-compatibility replay is not included in these scores.

Evidence: `ml/nemo_gym/evidence/ablation_reliability_2026-10-18/`. It includes
frozen policy files/hashes, original source hashes, the test-opening marker,
24 raw trace/metrics/config directories, session log and family/verifier counts.
Every run requests the same 14 cases with temperature 1.0, max_tokens 1024,
parallel_tool_calls=false, 12 turns and a 60-second HTTP timeout. Same H100,
Lightning BF16 revision `a9904d24bcc1d289a1950fa9d2b978c47cf903b9` and upstream
vLLM v0.27.1; this is not a verified Red Hat distribution.

Reproduce with private LLM environment exported and official pinned NeMo Gym
on PYTHONPATH (fresh output directory):

```sh
python scripts/vllm/run_ablation.py --prepare --output /path/to/fresh/ablation
python scripts/vllm/run_ablation.py --output /path/to/fresh/ablation
python scripts/vllm/summarize_ablation.py --evidence /path/to/fresh/ablation
```

The companion 20-beacon/10-ambiguous live reliability measurements and timing
scope are reported in `docs/VLLM_RESULTS.md`, separately from Gym scores.
