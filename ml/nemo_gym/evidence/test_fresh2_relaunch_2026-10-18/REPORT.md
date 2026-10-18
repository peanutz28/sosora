# Fresh exam 2 results


| Policy | Complete runs | Passes /42 | Mean /42 | Range /42 | Provider errors |
|---|---:|---|---:|---|---:|
| baseline | 3/3 | 15, 11, 13 | 13.00 | 11–15 | 1 |
| grounded_v2 | 3/3 | 30, 30, 30 | 30.00 | 30–30 | 0 |
| grounded_v2_nullable | 3/3 | 41, 40, 42 | 41.00 | 40–42 | 0 |

Per-family counts are passes / evaluated attempts across three runs (planned 18 each):

| Family | Baseline | grounded_v2 | grounded_v2 + nullable adapter |
|---|---|---|---|
| alternate_route | 10/18 (4, 4, 2) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| bridge_closed | 11/18 (4, 2, 5) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| conflicting_evidence | 3/18 (1, 1, 1) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| isolated | 4/18 (2, 1, 1) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| missing_location | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 18/18 (6, 6, 6) |
| tool_failure | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 15/18 (5, 4, 6) |
| two_roads_closed | 11/18 (4, 3, 4) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |

Adapter repairs (field edits / tool calls / scenarios): baseline: 0 / 0 / 0, grounded_v2: 0 / 0 / 0, grounded_v2_nullable: 36 / 36 / 36


Adapter versus grounded_v2 mean difference: **+11.00 passes /42
(+26.19 percentage points)**. Adapter repairs: **36
scalar arguments**, across **36 tool calls** and
**36 repeated scenario attempts**. Raw/effective arguments
and each field edit were retained and checked against the unchanged adapter.
`adapter_repairs.json` lists exact repairs and family/spelling counts. Repairs are
system compatibility behavior, not improved model generation or prompt-only gains.

All 36 repairs converted `graph_version: "None"` to JSON null: 18 in missing-location
cases and 18 in tool-failure cases. Missing-location passes rose from 0/18 to 18/18;
tool-failure passes rose from 0/18 to 15/18. The other five families stayed 18/18 in
both grounded arms. The three remaining adapter failures submitted `needs_location`
for known-location incidents with unavailable road status, where the correct answer
was `unknown`. The adapter preserved those wrong decisions. Their original and
repaired arguments are retained in `adapter_failure_diagnosis.json`. This result
supports a bounded encoding-compatibility benefit, not a fix for reasoning errors.

Baseline repetition 3 had one `RemoteProtocolError`; its case remains a failed
attempt in the 42-case denominator and was not retried. The two grounded arms had
no provider errors. The server request-success counter delta was 2,227, matching
the runner's recorded response-call count; post-run queues were empty and GPU
utilization was 0%, with the same model left resident for filming.

The full 54-test suite passed (51 before sealing, plus reporting/admission tests).
The new `launch_fresh_exam2.sh` admission wrapper was added and tested after the
initial launch error; the authorized relaunch itself used a fail-fast shell gate.
The frozen evaluator, adapter and verifier were not edited during the experiment.
Raw runner configs use the generic policy label `grounded_v2` because frozen
per-arm JSON is selected via the existing config-root loader. `exam_run.json` and
its policy SHA256 identify the actual arm.

### Initial infrastructure failure and authorized relaunch

The initial launch's configured local tunnel was down. Readiness raised connection
refused; a shell launch error allowed the evaluator to proceed anyway. All 378
attempts ended in ConnectError, with zero requests reaching the model and zero
repairs. Each initial arm's raw pass counts were 0,0,0 /42 (mean 0, range 0–0), all
families 0/18 and 126 provider errors per arm. These are infrastructure failures,
not evidence of model quality. No record was discarded or overwritten.

The user explicitly authorized **one complete relaunch, retaining failures** as an
exception to the original no-retries instruction. Commit **68f5b1a** records that
authorization with byte-identical seal and arms before the relaunch. Its shell
failed closed on readiness. There were 756 recorded scenario attempts in total:
378 initial connection failures plus the separately reported 378 live attempts.
No selective retry, policy selection or tuning occurred. The performance table
above describes the authorized live relaunch, not a pooled or selected-best result.

### Evidence and limits

Live evidence: `ml/nemo_gym/evidence/test_fresh2_relaunch_2026-10-18/`.
Initial failure: `ml/nemo_gym/evidence/test_fresh2_2026-10-18/`. Seals, opening markers,
raw rollouts/configs/metrics, serving audit, complete per-family results, repair
ledger, offline official-verifier rescoring and post-run GPU-idle checks are retained.
The offline scoring command is the first command in Reproduce above.

This is the same seven deterministic synthetic families at larger graph sizes,
not a novel task distribution or real-road field validation. The 42 cases are now
spent. Repeated attempts are not independent emergencies. The custom loop uses
pinned genuine NeMo Gym resource-server tools/verifier, not the full Gym CLI.
These results do not establish the origin of stringified nulls in generation versus
serving conversion, or establish a general benefit on unseen families.
