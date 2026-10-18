# Hosted-mode preview captures (local only)

These captures show the isolated production frontend at `http://127.0.0.1:17863`
using the built Linux Docker image on `http://127.0.0.1:17860`.
**They are not public deployment screenshots.** HF Docker Space creation was
blocked by HTTP 402; see `docs/HOSTED_DEMO.md`.

- `01_seed_local.jpg`: seed, nine reachable and no blocked road.
- `02_beacon_local.jpg`: Beacon hero, five cut off/four reachable, cached replay.
- `03_dot_local.jpg`: DOT opening report leaves the existing road avoided.
- `04_responder_review_local.jpg`: ambiguous responder report asks which bridge; no closure.
- `05_responder_confirm_local.jpg`: operator confirms the eastern bridge; closure and assessment.

The requested hosted disclosure appears above the existing UI. The trace badge
says `cached replay` and never substitutes routing time for model latency.
Final DOM states and browser console output are saved in
`docs/evidence/hosted_demo_2026-10-18/`. Initial isolated-browser requests needed
reload/retry; these captures do not establish public cold-start reliability.
