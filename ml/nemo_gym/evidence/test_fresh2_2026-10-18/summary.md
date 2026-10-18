| Policy | Complete runs | Passes /42 | Mean /42 | Range /42 | Provider errors |
|---|---:|---|---:|---|---:|
| baseline | 3/3 | 0, 0, 0 | 0.00 | 0–0 | 126 |
| grounded_v2 | 3/3 | 0, 0, 0 | 0.00 | 0–0 | 126 |
| grounded_v2_nullable | 3/3 | 0, 0, 0 | 0.00 | 0–0 | 126 |

Per-family counts are passes / evaluated attempts across three runs (planned 18 each):

| Family | Baseline | grounded_v2 | grounded_v2 + nullable adapter |
|---|---|---|---|
| alternate_route | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| bridge_closed | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| conflicting_evidence | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| isolated | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| missing_location | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| tool_failure | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| two_roads_closed | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |

Adapter repairs (field edits / tool calls / scenarios): baseline: 0 / 0 / 0, grounded_v2: 0 / 0 / 0, grounded_v2_nullable: 0 / 0 / 0
