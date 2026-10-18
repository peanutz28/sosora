# Fresh exam 2: argument repair isolation

Original seal: b4b4cc6, before any request was sent to the model for test_fresh2.
User-authorized complete relaunch seal: 68f5b1a. The original seal and policy JSONs
are copied byte for byte; no data, policy, adapter, scoring or serving change.
See relaunch_authorization.json and the separately retained failed launch at
../test_fresh2_2026-10-18/launch_failure.json.

42 cases: seven existing synthetic families at each node count 19–24. Original
train, validation, test and test_fresh bytes retain their recorded SHA256 hashes.
Same deterministic task families are a distribution limitation; larger graphs are
not proof of field generalization. Three repetitions reuse the same cases.

Arms: baseline, grounded_v2, grounded_v2_nullable. The last two use identical
policy bytes. Only the last enables the unchanged audited nullable-null-v1 adapter.
Its sole permitted repair is decoding a string None/null to JSON null for an
unambiguous nullable scalar schema excluding strings. The runner retains raw and
effective arguments and every field edit. No path, location, reachability decision,
missing field, non-null value or malformed JSON is repaired.

Order:
1. baseline, grounded_v2, grounded_v2_nullable
2. grounded_v2, grounded_v2_nullable, baseline
3. grounded_v2_nullable, baseline, grounded_v2

Settings: temperature 1.0; max_tokens 1024; parallel_tool_calls=false; max 12 turns;
HTTP timeout 60 seconds; same served Lightning BF16 checkpoint, vLLM container and
flags, with prefix cache retained. No random seed is added, matching the previous
fresh exam. The custom agent loop uses pinned genuine NeMo Gym resource-server
tools and verifier, not the full Gym CLI. Provider label redhat_vllm is not a claim
about Red Hat image distribution.

No policy selection, tuning, selective retries, per-call retries or failed-run
replacement inside the authorized relaunch. Preserve partial/error runs if they
occur. Generation cutoff 08:35 ET, reserving five minutes before the user's 08:40
filming deadline. Leave serving compute resident and stop exam traffic; do not
stop the filming GPU instance.

Offline scoring command is first in docs/GYM_RESULTS.md's Reproduce section. It
rescores every saved trajectory with the original official /verify endpoint,
checks the seal/ordering and recorded adapter edits, then rebuilds tables. Counts
reported separately: repaired scalar fields, tool calls containing at least one
repair, and scenarios containing at least one repair. Aggregate per-family counts
are out of 18 repeated attempts (six cases times three); they are not 18 independent
scenarios. Report each run, mean/range and errors, even if the adapter hurts.

Recorded authorized launch (after successful fail-fast readiness; already opened,
so it cannot be rerun in place):

```sh
PYTHONPATH="$PWD:/private/tmp/sosora_nemo_gym_runtime/official" /private/tmp/sosora_nemo_gym_runtime/venv/bin/python scripts/vllm/run_fresh_exam2.py --output ml/nemo_gym/evidence/test_fresh2_relaunch_2026-10-18 --seal-commit 68f5b1a
```

Completion: 08:18:41 AM ET. Idle check: 08:19:04 AM ET, zero running/waiting requests;
GPU query: 0% utilization. Shared serving compute and the restored 18080 tunnel
were left running for dashboard filming. No further exam generation follows.
