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
