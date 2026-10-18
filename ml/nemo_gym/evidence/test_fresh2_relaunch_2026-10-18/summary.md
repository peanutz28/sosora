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
