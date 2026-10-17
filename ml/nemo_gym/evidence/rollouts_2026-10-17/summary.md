# SOSora Nemotron policy evaluation — 2026-10-17

Synthetic simulated rescue scenarios; these results are not real-world road-safety validation.

Model: `nvidia/nemotron-3.5-lightning-30b-a3b` via NVIDIA API. Existing custom chat-completions runner, official pinned NeMo Gym resource server and verifier. Both fixed policies were run on validation before test. No prompt changes, weight updates, RL, cached responses, or selective retries. Each invocation requested all 14 scenarios, at most 12 model turns per scenario, and a 14,400-second run budget.

Pass = verifier reward exactly 1. Mean turns = number of recorded model request latencies plus one for a ReadTimeout/ConnectTimeout/ConnectError/ReadError/WriteError/RemoteProtocolError per scenario. No-response attempts count as turns; multiple tool calls in one response count as one turn.

| Split | Policy | Overall | bridge_closed | two_roads_closed | alternate_route | isolated | tool_failure | conflicting_evidence | missing_location | Mean turns |
|---|---|---|---|---|---|---|---|---|---|---|
| validation | baseline | 1/14 (7.1%) | 0/2 (0.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 1/2 (50.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 3.50 |
| validation | evidence_first | 7/14 (50.0%) | 1/2 (50.0%) | 1/2 (50.0%) | 1/2 (50.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 3.93 |
| test | baseline | 1/14 (7.1%) | 0/2 (0.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 1/2 (50.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 4.00 |
| test | evidence_first | 4/14 (28.6%) | 1/2 (50.0%) | 1/2 (50.0%) | 1/2 (50.0%) | 1/2 (50.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 0/2 (0.0%) | 3.14 |


All family denominators are two scenarios per split; overall denominators are 14. Any unexecuted scenarios remain in the denominator and are listed below.

## Failures

| Split | Policy | Scenario | Family | One-line reason |
|---|---|---|---|---|
| validation | baseline | validation_181a16f887959f1b | bridge_closed | ReadTimeout; missing_required_tools; require_exactly_one_recommendation |
| validation | baseline | validation_b06642ae7f60b60f | two_roads_closed | ReadTimeout; missing_required_tools; require_exactly_one_recommendation |
| validation | baseline | validation_62750ca6b0974168 | alternate_route | ReadTimeout; missing_required_tools; require_exactly_one_recommendation |
| validation | baseline | validation_d075e16f24a90471 | isolated | ReadTimeout; missing_required_tools; require_exactly_one_recommendation |
| validation | baseline | validation_913199d24b8594c0 | tool_failure | ReadTimeout; missing_required_tools; require_exactly_one_recommendation |
| validation | baseline | validation_1a747a29860bdc3b | conflicting_evidence | missing_human_review; missing_required_tools |
| validation | baseline | validation_e834e609ac044f20 | missing_location | incorrect_reachability; invented_graph_version; missing_human_review; unsupported_path |
| validation | baseline | validation_24cc55249c9f9188 | bridge_closed | missing_required_tools |
| validation | baseline | validation_0952ed37d416e13a | two_roads_closed | missing_required_tools |
| validation | baseline | validation_252dbe51c86f0b72 | alternate_route | missing_required_tools |
| validation | baseline | validation_6a5d70a4d7eb062c | tool_failure | incorrect_graph_version; route_tool_before_current_status; stale_graph_version; unsupported_path |
| validation | baseline | validation_4a94b989a0742fff | conflicting_evidence | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| validation | baseline | validation_1ddb85da34002e52 | missing_location | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| validation | evidence_first | validation_1a747a29860bdc3b | conflicting_evidence | missing_human_review; missing_required_tools |
| validation | evidence_first | validation_e834e609ac044f20 | missing_location | invented_graph_version |
| validation | evidence_first | validation_24cc55249c9f9188 | bridge_closed | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| validation | evidence_first | validation_0952ed37d416e13a | two_roads_closed | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| validation | evidence_first | validation_252dbe51c86f0b72 | alternate_route | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| validation | evidence_first | validation_4a94b989a0742fff | conflicting_evidence | missing_human_review; missing_required_tools |
| validation | evidence_first | validation_1ddb85da34002e52 | missing_location | invented_graph_version |
| test | baseline | test_3670cce87e210967 | bridge_closed | missing_required_tools |
| test | baseline | test_13422fce8549be52 | two_roads_closed | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | baseline | test_a8d7b314bd0840a0 | alternate_route | missing_required_tools |
| test | baseline | test_7d15923f0c6dd317 | isolated | unsupported_path |
| test | baseline | test_3e1f762e1f3d6a6a | tool_failure | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | baseline | test_c6c7deadafd6b1d5 | conflicting_evidence | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | baseline | test_490fb73bdfa50109 | missing_location | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | baseline | test_e5919451c87b3098 | bridge_closed | missing_required_tools |
| test | baseline | test_ee8ab9a4f0c1a820 | two_roads_closed | missing_required_tools |
| test | baseline | test_bf7ed6380df8663e | alternate_route | missing_required_tools |
| test | baseline | test_7ce039a63cd1968e | tool_failure | route_tool_before_current_status; stale_graph_version; unsupported_path |
| test | baseline | test_a11eb99e9acb26e6 | conflicting_evidence | missing_human_review; missing_required_tools |
| test | baseline | test_73b37abb54294189 | missing_location | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_3670cce87e210967 | bridge_closed | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_13422fce8549be52 | two_roads_closed | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_a8d7b314bd0840a0 | alternate_route | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_7d15923f0c6dd317 | isolated | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_3e1f762e1f3d6a6a | tool_failure | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_c6c7deadafd6b1d5 | conflicting_evidence | missing_human_review; missing_required_tools |
| test | evidence_first | test_490fb73bdfa50109 | missing_location | invented_graph_version |
| test | evidence_first | test_7ce039a63cd1968e | tool_failure | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_a11eb99e9acb26e6 | conflicting_evidence | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |
| test | evidence_first | test_73b37abb54294189 | missing_location | HTTPStatusError; missing_required_tools; require_exactly_one_recommendation |


Input SHA-256 hashes match the pre-run manifest. Evaluator and scenario files were unchanged. Raw tool traces, model usage, latency, verifier issues, run configuration, exit codes, and logs are preserved beside this summary.

Provider failures: 18 HTTPStatusError, 5 ReadTimeout. The existing runner retains exception types but not HTTP error status codes or response bodies, so HTTPStatusError causes cannot be diagnosed from these outputs. These failures remain in pass-rate denominators. Its language_model_calls metric excludes requests that time out before returning; mean turns above includes those attempts.

Validation: 25 existing Gym tests and two added evidence-integrity tests passed. No source files were edited.
