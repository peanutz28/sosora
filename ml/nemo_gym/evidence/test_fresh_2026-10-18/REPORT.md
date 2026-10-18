# Fresh sealed Gym exam

## Fresh held-out exam — Oct 18

**All nine planned runs finished at 04:49:20 AM ET, before the 6:30 AM ET hard deadline.**
The protected H100 remains RUNNING/HEALTHY, with zero running/waiting requests and
0% GPU utilization measured afterward, ready and left resident for 7 AM filming.

### Seal and unchanged inputs

Commit **5b80c79**, made before any model call opened `test_fresh`, contains the
42-case data file, its SHA256, the three frozen policy JSON files, the pre-run
integrity tests and `seal.json` with `test_fresh_opened_by_model_run=false` and
`model_calls_on_test_fresh=0`. That immutable marker describes the sealing time;
`opened.json` records the later actual opening and commit reference. No policy
was edited afterward. There was no selection, retry, weight update or RL.

New file: `ml/nemo_gym/data/test_fresh.jsonl`. Node counts **13–18**, all seven
families at each size: **42 unique simulated cases**, six per family. SHA256:
`37162bed13593d17438f7352173be649b486adff7c78328c4ff2206268cfd0e8`.

The train, validation and original test JSONL bytes regenerated with exactly their
prior SHA256 hashes; both before/after values are in `seal.json`. The only schema/
runner support changes add the new split name; the verifier scoring function is
byte-for-byte unchanged. All **49 regression tests passed before the seal**.
The existing runner selects frozen per-arm JSON through its config-root loader;
its raw generic policy label is `grounded_v2`, while each `exam_run.json` identifies
the actual arm.

### Results

| Policy | Complete runs | Passes /42 | Mean /42 | Range /42 | Provider errors |
|---|---:|---|---:|---|---:|
| baseline | 3/3 | 16, 12, 17 | 15.00 | 12–17 | 0 |
| system_prompt_only | 3/3 | 30, 29, 30 | 29.67 | 29–30 | 0 |
| grounded_v2 | 3/3 | 30, 30, 30 | 30.00 | 30–30 | 0 |

Per-family counts are passes / evaluated attempts across three runs (planned 18 each):

| Family | Baseline | System prompt only | grounded_v2 |
|---|---|---|---|
| alternate_route | 14/18 (4, 5, 5) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| bridge_closed | 11/18 (5, 2, 4) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| conflicting_evidence | 5/18 (1, 1, 3) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| isolated | 3/18 (1, 1, 1) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| missing_location | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| tool_failure | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| two_roads_closed | 12/18 (5, 3, 4) | 17/18 (6, 5, 6) | 18/18 (6, 6, 6) |

All **378 planned scenario attempts** completed in **nine full runs**, with
**2,182 recorded model calls** and **zero provider errors**. Rates averaged
**35.71% baseline**, **70.63% prompt-only**, and **71.43% both**.
The both-versus-baseline mean difference is **+35.71 percentage points**.
Both adds only one passed attempt across 126 repeated attempts compared with
prompt-only, so this does not establish a substantial extra benefit from combining
the descriptions with that prompt. Every individual run is reported above;
nothing was chosen or rerun after inspecting scores.

### Remaining failures and limits

`grounded_v2` still fails all missing-location and tool-failure cases: **12/42 per
run, 36 failed attempts across three runs**. Every one submitted the string
`"None"` for graph_version instead of JSON null. The origin in model generation
versus serving conversion remains unresolved. Adapter stays **off**; schemas and
verifier are unchanged. The prior optional encoding-repair replay is not included.
Prompt-only also failed one two-roads-closed attempt. Overlapping verifier counts
and individual failure records are saved alongside the raw traces.

This new split had not been live-model evaluated before its commit. The old test
split was used previously. These are new IDs and larger topologies from the same
seven deterministic synthetic families, not a wholly new task distribution.
Two size-17 missing-location/tool-failure topologies appeared previously in
fake-provider unit checks, after the policy was already frozen; those checks used
no live model. This caveat is recorded in the seal. These 42 cases are now **spent**
and must not be treated as a new unseen holdout for later tuning. Repetitions reuse
the same cases, with prefix caching enabled; 378 attempts are not 378 independent
emergencies. The conservative all-human-review instruction is not penalized for
operator workload. These scores do not measure real-road field accuracy or fix
the separate guarded-versus-model-only ambiguity weakness.

### Protocol and evidence

Order: baseline → prompt → both; prompt → both → baseline; both → baseline → prompt.
Same Lightning BF16 checkpoint/container and ablation inference settings:
temperature 1.0, max_tokens 1024, parallel_tool_calls=false, 12 turns, HTTP timeout
60 seconds, nullable adapter off. The global run budget was capped by the deadline.
The runner enforced a 6:25 AM ET evaluation cutoff, reserving five minutes for
reporting/commit before 6:30; it was not reached. No serving settings changed.

Evidence root: `ml/nemo_gym/evidence/test_fresh_2026-10-18/`. Includes the committed
seal/policies, original/new hashes, opening marker, nine raw trace/config/metric
folders, logs, complete family/issue counts, deadline completion record, failure
diagnosis and filming-idle checks. This remains the custom chat-completions runner
using pinned official NeMo Gym resource-server tools/verifier, not the full Gym CLI.
The provider label `redhat_vllm` is not proof of a Red Hat-distributed container.

Recorded launch (the script refuses reopening an existing exam):

```sh
python scripts/vllm/run_fresh_exam.py --output ml/nemo_gym/evidence/test_fresh_2026-10-18 --seal-commit 5b80c79
# Offline reporting/audit; no model calls:
python scripts/vllm/summarize_fresh_exam.py --evidence ml/nemo_gym/evidence/test_fresh_2026-10-18
python scripts/vllm/check_fresh_exam.py
```
