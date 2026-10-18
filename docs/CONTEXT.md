# SOSora: living project context

> **Every AI agent (Claude, Codex, Cursor) reads this first and updates it last.**
> When you finish a task: update the Status table, add a line to the Changelog, and add
> anything the next agent must know to "Open issues". Keep it short and factual.
> Never write a number here that was not measured and saved in the repo.

Deadline: **Sunday Oct 18, 11:00 AM ET** (code freeze + submission). Submission = GitHub
link, project description, **3 to 5 minute video**. Late submissions are rejected.
Team: two sisters. Owners: **Ria** (ML, backend, Beacon hardware, Codex) and **Jia**
(dashboard, resident app, pitch, Cursor). Claude = planner/reviewer.

## The one-liner
**SOSora keeps the rescue map alive when the towers and the roads go down.**

## Problem
In a hurricane two networks fail at once. **Phones** fail, so rescuers lose *who* needs help.
**Roads** fail, so they lose *how* to reach them. During Helene ~74% of cell sites in NC's
21-county disaster area were down (FCC, Sep 28 2024) and NCDOT logged 8,100+ road, bridge and
culvert damage sites by Nov 1 2024. NC's own Helene after-action review (McChrystal Group for
NCEM) found communications breakdowns and poor information sharing, and recommended local
teams be able to operate **without comms for up to 72 hours**.

## Solution (three parts, one system)
- **SOSora Beacon**: Raspberry Pi + USB mic + water-level sensor at a flood-prone crossing.
  Voice reports and sensor readings, store-and-forward when the link is down. (`beacon/`)
- **SOSora Command**: one GPU box in the county's mobile command vehicle, runs offline.
  Speech to text -> Nemotron 3.5 Lightning parses the report -> Lightning tool-calling agent
  resolves the real road on the OSM map, applies the trust rule in code, recomputes who is
  cut off -> command dashboard. (`backend/`, `ml/`, `frontend/`)
- **SOSora SOS**: resident app that queues an SOS with no signal and sends it when any link
  (or a Beacon) appears. (Jia, optional, last in build order)

Track: **Tool-calling** ("falling back gracefully when something breaks" is our disaster).
Bounties: Nemotron Lightning, NeMo Gym model improvement, Red Hat vLLM.

## Hard rules
1. **Nemotron 3.5 Lightning (30B-A3B) is the ONLY generative LLM.** Hackathon cap is 33B total
   across all generative LMs. Never add a second LLM (no Nano, no Llama) for anything.
   ASR (speech) and SegFormer (vision) are not generative LMs; confirm ASR with organizers.
2. Real: OSM/NCDOT roads, Nemotron calls, graph reachability, Gym evals, vision eval numbers.
   Simulated and labeled `[SIMULATED]`: SOS incidents, radio messages, units.
3. Trust rule lives in code (`backend/app/agent.py`, `report_segment`): one credible
   "impassable" report blocks a road; a road reopens only from a verified official source;
   conflicts become "contested" and stay avoided. The LLM cannot override it.
4. Every external call has a DEMO_MODE / cached fallback. No secrets in git or chat.

## Architecture -> folders
| Part | Where | Notes |
|---|---|---|
| Radio + Beacon intake, demo seed | `backend/app/radio_api.py` | `/api/radio`, `/api/radio/confirm`, `/api/radio/audio`, `/api/beacon/{id}/reading`, `/api/radio/demo/seed`, `/api/radio/status`, `/api/beacons` |
| Speech to text hook | `backend/app/asr.py` | OpenAI-compatible `/audio/transcriptions`; `ASR_BASE_URL` |
| Tool-calling agent + trust rule | `backend/app/agent.py` | 6 tools, one tool per turn, emits every call on `/ws/events` |
| Radio text parser (Lightning) | `ml/inference/radio.py` | `POST /ml/radio/parse` on port 8002 |
| Vision model (fine-tuned SegFormer-B0) | `ml/vision/`, `ml/inference/app.py` | aerial flooded-road candidates; hub-side evidence |
| NeMo Gym env + evals | `ml/nemo_gym/` | results in `ml/nemo_gym/evidence/rollouts_2026-10-17/` |
| Dashboard | `frontend/` (Next.js) | Jia, Cursor. Brief: `docs/briefs/DASHBOARD_CURSOR.md` |
| Beacon hardware | `beacon/` | Ria, Codex. Brief: `beacon/README.md` |
| vLLM on Brev + Gym rerun | Brev | Brief: `docs/briefs/BREV_VLLM_CODEX.md` |

## The hero demo (real roads in Swannanoa, NC)
1. `POST /api/radio/demo/seed` -> 9 simulated SOS pins on real roads, all reachable.
2. Beacon at the **eastern Warren Wilson Road bridge over the Swannanoa River** (OSM way
   549633356) sends: *"the bridge on Warren Wilson Road is gone... three families on the far
   side"*. In our map area that bridge is the only crossing for the neighborhoods north of it.
3. Lightning parses it, the agent finds the bridge (Beacon position disambiguates), blocks it,
   recomputes reachability -> **5 of 9 SOS incidents lose road access** (Bee Tree Rd, Riddle
   Rd, Long Branch Rd, Watch Knob Ln, Smokey Mountain Dr). 4 south of the river stay reachable.
4. Same message from a responder radio with no position -> there are **two** Warren Wilson Rd
   bridges -> agent asks the operator to confirm instead of guessing -> `/api/radio/confirm`.
5. A DOT "it's open" report cannot reopen it without verification.
6. Water sensor over threshold at the Beacon -> same agent, same trust rule.

## Status (update this table)
| Item | Status | Evidence |
|---|---|---|
| Merge ML + dashboard into `integration` | Integrated UI merge and reviewed corrections complete | `git log integration`, `docs/screenshots/` |
| Radio parse (Lightning) | Works live, 2.7-4.1 s/message | live run 2026-10-17 ~23:00 |
| Imagery outage demo | I toggles a simulated recoverable imagery-tool failure; trace and assessment disclose missing imagery, trust/reachability still finish; 39 backend and 13 frontend tests pass, production build passes | `docs/evidence/imagery_outage_tests_2026-10-18.xml`, `docs/evidence/imagery_browser_2026-10-18.json` |
| Reachability optimization | Seed/hero outputs identical; median cached hero assessment 3.304→1.138 s over three paired runs; 37 backend tests pass | `docs/evidence/reachability_2026-10-18.json`, `docs/evidence/reachability_tests_2026-10-18.xml` |
| Agent + trust rule, real OSM graph | Works in demo replay; live Lightning resolves the right bridge | `backend/tests/test_radio_api.py` |
| Live agent speed | 20 live beacon runs: exact bridge + five-cut-off 20/20; E2E median 7.912 s/p95 9.782 s. Ambiguous final state 10/10; strict model abstention only 1/10 (code rejects 9 unsafe attempts) | `docs/VLLM_RESULTS.md`, `docs/evidence/reliability_2026-10-18/summary.json` |
| Beacon sensor + audio endpoints | Command endpoints ready; Beacon client implemented with fake sensor, replay, durable outbox and retry | `backend/app/radio_api.py`, `beacon/beacon.py` |
| Beacon client verification | 12 unit checks pass; fake sensor + replay each block bridge and cut off 5 SOS incidents; reconnect sends one report; Pi pending | `beacon/evidence/unit_tests.xml`, `beacon/evidence/demo_verification.json` |
| ASR model | Not chosen/served | `backend/app/asr.py` TODO |
| Gym results | Repeated ablation, three runs/split: test mean baseline 7/14 (range 6–8), descriptions 9 (8–10), prompt 10 (10–10), both 10 (10–10); 336 scenarios, zero provider errors; spent test split, no weights/RL | `docs/GYM_RESULTS.md`, `ml/nemo_gym/evidence/ablation_reliability_2026-10-18/summary.json` |
| vLLM on Brev | RUNNING / HEALTHY; Lightning BF16 H100 left on for 7 AM ET filming, $5.40/hr compute ($5.42 console total) | `docs/evidence/reliability_2026-10-18/filming_readiness.json` |
| Dashboard wired to radio flow | UI FROZEN except bug fixes: synchronized streamed counters, teal operator sign-off, evidence-backed model/serving/latency badge (cached replay labeled), delayed-map React error fixed, 0.85 glass and P-mode key hiding; build + 13 frontend + 22 backend + 17 browser checks pass | `docs/screenshots/cinematic/freeze/README.md`, `docs/screenshots/cinematic/freeze/browser-verification.json` |
| iOS → Command | Mobile adapters, selected-road agent intake and LAN default implemented; SOS coordinates broadcast for dashboard pins; physical phone check pending | `backend/tests/test_mobile_api.py`, `ios-app/README.md`, `docs/evidence/mobile_unit_2026-10-18.xml` |
| Vision V3 | Single sealed final evaluation complete: native v2 F1 0.306459, V3 0.273577; no promotion, default unchanged; L4 STOPPED; development-only postmortem saved | `docs/ml/V3_RESULTS.md`, `docs/ml/V3_POSTMORTEM.md`, `docs/ml/evidence/v3_2026-10-18/final_evaluation.json` |
| Parameter budget | Full Nemotron checkpoint + SegFormer: 32,916,977,826 parameters, under 33B; including Parakeet: 33,534,803,752, over 33B if ASR counts | `docs/PARAM_BUDGET.md`, `docs/evidence/param_budget_2026-10-18/totals.json` |
| Video | Cinematic hero footage ready: 15-second edit plus full capture; submission video edit pending | `docs/screenshots/cinematic/hero-sequence-15s.mp4` |

## Open issues / gotchas
- Reliability caveat: guarded ambiguity outcome 10/10 is not model-only compliance. In 9/10 ambiguous runs Lightning attempted to block both bridges; code rejected it. Strict no-mutation abstention 1/10; some summaries loosely describe rejected reports as recorded. Text-radio timing excludes ASR/physical radio/browser; repeated fixed messages use warm prefixes.
- Imagery outage demo: S seeds (and clears the outage), I toggles **Imagery offline**, B sends the Beacon report. `/api/radio/demo/imagery` changes only the evidence tool, not map layers. A running assessment snapshots the switch; restart the backend to load these changes.
- Parameter budget counts all Nemotron experts and MTP weights. The index core-only total excludes MTP; total_size/2 disagrees with tensor shapes. Full-checkpoint + SegFormer fits 33B without ASR, but adding Parakeet exceeds it if ASR counts. Confirm organizer scope; use `docs/PARAM_BUDGET.md`, not rounded model names.
- **UI FROZEN after the final user-requested pass (2026-10-18): bug fixes only.** Agent runtime metadata is additive on existing agent events/responses; latency is the last successful model HTTP call, never routing/whole-report latency. Cached replay has no invented latency. The updated backend process must be loaded to emit new telemetry; no GPU/model-serving process was started.
- Vision V3 final set is spent: no retuning, reselection or rescoring on these tiles. Known Louisiana/Germany events only; no Helene accuracy claim. Selected weights remain local/ignored, and V3 is not served because it lost final F1. L4 stopped; its existing retained disk still incurs storage charges.
- Cinematic Command: press P outside an input for presentation mode; S seeds, B runs the Beacon hero, R requests bridge review, and A is the eastern bridge. Terrain displacement disables automatically below the frame budget while hillshade remains. Broken-route stubs need the last reachable geometry in the current browser session. The 15-second recording cuts the middle wait and is not a backend latency benchmark. See `docs/screenshots/cinematic/README.md` for measured performance and evidence.
- Gym null compatibility follow-up is opt-in (`--argument-adapter nullable-null-v1`), default off. Offline recorded validation replay accepts 14/14 after four null-only edits; this is not a new model/test score. Fresh fake-provider cases verify real tools/verifier; H100 is now running for filming. Raw/effective arguments are audited.
- grounded_v2 still fails tool-failure and missing-location families: string `None` instead of JSON null makes final arguments invalid. All recommendations request human review; unnecessary review is unpenalized by Gym. Small previously used 14-case test, no broad generalization claim. H100 was stopped after that earlier evaluation; current filming session is running.
- iOS defaults to `http://192.168.68.80:8000`; existing installs retain their saved URL and must update Sync settings. Phone and Mac need the same LAN; Command must bind `0.0.0.0`. Mobile state uses `/api/mobile/state`; Command `/api/state` keeps its shape. Physical phone delivery remains unverified.
- Ria authorized pushing the UI merge and corrections after screenshot retakes; see the latest Changelog entry. UI changes do not modify `dashboard/` or `ios-app/`.
- Command needs `websockets` (now pinned in `backend/requirements.txt`) for streamed events. Build alongside dev with `SOSORA_NEXT_DIST_DIR=.next-build npm run build` to avoid replacing the dev cache. Google Fonts are fetched at build time and served locally afterward; street/satellite basemap tiles still need network/cache.
- Beacon delivery is at-least-once: UUIDs and Idempotency-Key persist, but Command audio/reading endpoints do not deduplicate. Lost acknowledgements can duplicate events. Use `--flush` to resume an offline replay without enqueuing it again.
- Fake sensor must target Command with `DEMO_MODE=true`: the backend currently ignores the posted simulated flag and derives source labels from its own demo setting. Real Pi mic/sensor/button and physical Wi-Fi unplug are unverified.
- Brev H100 is RUNNING for 7 AM ET filming per user request; no automatic stop scheduled. Compute is $5.40/hr plus retained disk ($5.42/hr displayed total). Local ignored `.env.vllm` holds token/tunnel/live ML settings; source it in the Command process for live calls. The benchmark does not reconfigure an already-running dashboard backend. Stop manually after filming when no longer needed; RAM model cache is lost on stop.
- Python 3.12 required for `ml/` (uses `asyncio.timeout`). Two `ml/tests/test_radio.py`
  provider tests fail on 3.10 only.
- Live agent: model batched tool calls with blank ids -> fixed (one tool per turn,
  `parallel_tool_calls: false`). Beacon position is injected by code, not the model.
- Private Brev vLLM is verified for the hero flow. `.env.vllm` is local and ignored; never commit it. Upstream vLLM image is used, not a verified Red Hat distribution. Model cache is in RAM and must download again after instance stop.
- Clean Gym results do **not** support an evidence_first improvement claim. Frozen baseline outperformed it on validation and test. No weights changed or RL ran. Native parsing removed strict-grammar latency; all partial diagnostic attempts remain saved separately.
- `backend/data/sosora.db-journal` is a stray file from a sandbox run; safe to delete.
- Video: never show a phone with signal bars when claiming "no signal".
- Reachability uses one Dijkstra per selected rescue base and caches node snaps for the immutable graph. Full seed/hero route and assessment equality against the old per-incident implementation is saved in `docs/evidence/reachability_2026-10-18.json`.

## Changelog (newest first)
- 2026-10-18 Codex reliability: froze four-way prompt/description ablation in `625bda8`; three validation and three test runs each, 336 scenarios / 1,944 calls, zero provider errors. Test means baseline 7/14, descriptions 9, prompt 10, both 10; spent split disclosed. Then 20 beacon + 10 ambiguous fresh-seed live requests: bridge 20/20, exact five-cut-off 20/20, guarded ambiguity 10/10, strict model abstention 1/10 (9 attempted mutations rejected). Beacon E2E median 7.912 s/p95 9.782 s; model call median 0.628 s/p95 1.633 s. GPU only vLLM, counters match 179 agent + 30 parse calls. 48 Gym + 9 radio tests and evidence checks pass. H100 RUNNING/HEALTHY for 7 AM filming; evidence `docs/evidence/reliability_2026-10-18/` and `ml/nemo_gym/evidence/ablation_reliability_2026-10-18/`.
- 2026-10-18 Codex: added only the requested Imagery offline drill control (I). Backend snapshots a simulated outage per report, emits recoverable ImageryUnavailable in the tool trace, explicitly discloses missing imagery and requests field verification/human review while enforcing existing road trust rules. Browser S→I→B verified 5 cut off/4 reachable and click-to-restore, with zero console errors; 39 backend tests, 13 frontend tests, TypeScript and production build pass. Evidence and trace screenshot in `docs/evidence/imagery_*2026-10-18.*`; frozen styling unchanged.
- 2026-10-18 Codex D follow-up: diagnosed V3 using reviewed train/dev only; full development-tile F1 0.217157→0.688286, processor parity exact on the checked crop. No sealed pixels/predictions reopened, final rerun, tuning or GPU launch. Postmortem recommends geographic development folds and diverse dry-road negatives (`docs/ml/V3_POSTMORTEM.md`). Exact pinned checkpoint audit: Nemotron including MTP 32,913,263,168, Parakeet 617,825,926, SegFormer 3,714,658; sums under 33B without ASR, over with ASR. Three metadata audit guard tests pass. Sources/method: `docs/PARAM_BUDGET.md`.
- 2026-10-18 Codex: committed mobile/iOS work as 02f163a, then replaced per-incident reachability with single-source Dijkstra per selected base plus reusable node snaps. All seed/closed-bridge routes (including full geometry) and assessments equal the old implementation across three paired runs. Median demo hero assessment 3.304→1.138 s; seed routes 0.711→0.372 s. All 37 backend tests pass; benchmark and raw timings saved under `docs/evidence/reachability_2026-10-18.json`.
- 2026-10-18 Codex final UI freeze: counters now consume the streamed reachability snapshot together with no choreography delay; successful resolved assessments show teal Ready for operator / Operator sign-off, while ambiguity/contested states stay yellow. Added truthful `agent_runtime` metadata (response model ID, configured serving backend, measured last successful HTTP-call latency; cached values null). Reproduced and fixed the Next.js slow-map timeout calling the parent setter inside a child state updater. Glass opacity 0.85; P hides map key. Production build, 13 frontend tests, 22 backend tests and 17 full development-browser checks pass with zero console/runtime errors; screenshots and before/after error logs in `docs/screenshots/cinematic/freeze/`. UI is now frozen except bug fixes; unrelated mobile work preserved.
- 2026-10-18 Codex D: trained the bounded SegFormer/U-Net sweep on the approved L4, committed development selection in f161cb0 before final preparation, and scored native v2 plus selected V3 exactly once on the same 38 sealed tiles. Final F1 0.306459→0.273577; no promotion or service changes. Saved all runs/counts/hashes and a 1920×1080 proof image including a V3 regression. Full ML suite 121 passed; final critical checks 14 passed. GPU stop verified at 02:43:53 ET; compute estimate $0.3550 excluding retained storage. Report/evidence: `docs/ml/V3_RESULTS.md`, `docs/ml/evidence/v3_2026-10-18/`.
- 2026-10-18 Codex buddy: completed the eight cinematic Command stages in ordered screenshot checkpoints on integration. Frontend visuals only; APIs/WebSocket contracts and simulated labels preserved. Production build, 11 frontend tests and 15 browser flow checks pass. Six 1920×1080 before/after captures and an edited 15-second hero recording are in `docs/screenshots/cinematic/`. Terrain falls back to hillshade under load; idle RAF sample 59.0 fps, complete hero 56.9 fps (16.8 ms p95), so sustained 60 fps remains a demo-machine limitation. Shared routes draw once; unrelated in-progress work was not included.
- 2026-10-18 Codex Gym follow-up: added opt-in schema-aware null argument adapter and raw/effective audit without changing verifier, policy or tasks. Offline validation replay 10/14→14/14 with exactly four null edits; no new model calls/test runs or GPU restart. Evidence `ml/nemo_gym/evidence/null_adapter_2026-10-18/`; original measured test remains 10/14 vs 6/14.
- 2026-10-18 Codex Gym: developed only grounded_v2 prompt/tool descriptions on validation (R1 4/14, R2/R3 10/14; fresh baseline 5/14), froze R2 in 269abc4 before test. Exactly one fresh test each: baseline 6/14, grounded_v2 10/14, zero provider errors; 26 Gym tests pass. Same Lightning BF16, tasks, schemas, sampling and official verifier. No weights changed/RL. H100 ($5.40/hr quoted before restart) verified STOPPED per user request. Full traces, family/verifier analysis and selection hashes in `ml/nemo_gym/evidence/grounded_v2_2026-10-18/`; report `docs/GYM_RESULTS.md`.
- 2026-10-18 Codex: added Command mobile health/catalog/state/status adapters and iOS incident aliases without removing the Command envelope. Selected road reports become responder radio evidence and run agent tools on exact segments (both directions), preserving reopening restrictions. Phone SOS coordinates broadcast in Command state for dashboard pins; All 33 backend tests pass, including real-road radio regressions (`docs/evidence/mobile_api_2026-10-18.xml`). iOS simulator SDK arm64 build succeeds (`docs/evidence/mobile_ios_build_2026-10-18.txt`). LAN setup documented in `ios-app/README.md`; physical phone check pending.
- 2026-10-18 02:00 Codex: corrected physical closure counts (opposite edge directions deduped), RadioTower Beacon icon/label, shared idle/working/needs-review status, disabled dev indicators, and 7px red closure line with dark casing. Production build and 8 frontend tests pass; hero and ambiguity screenshots retaken at both requested sizes and shown before push. README now reports the clean vLLM Gym table and measured hero speed, with no policy-improvement or Red Hat image claim. Evidence: `docs/evidence/ui_corrections_2026-10-18/`.
- 2026-10-18 00:48 Codex: UI merge Steps 0–5 completed on the existing Claude palette/fonts/track groundwork. Verified S→B, S→R→confirm eastern bridge→D (no reopening), S→W, primary Run demo, Helene track and incident details. Each closure flow cuts off 5 of 9 SOS incidents; 6 frontend tests and 30 backend tests pass, production build passes. Screenshots at 1440×900 and 1920×1080 saved in `docs/screenshots/`; local commit/docs ready, push/PR held for requested visual review.
- 2026-10-18 00:18 Codex: wired backend incident reachable/route fields through the dashboard queue, map markers, list and intelligence panel. Missing access and snap failures remain unknown; route existence is not verified passability. Node regression tests and TypeScript check pass; live dashboard confirmed SOS-001 through SOS-005 show No road access while the other seeded incidents retain routes.
- 23:51 Codex: Job A done: H100 Lightning BF16 vLLM; final hero 5/5, mean 12.442 s; clean Gym test baseline 7/14 vs evidence_first 4/14, no provider errors across 56 scenarios; surge 200/200; GPU STOPPED. Results, commands and restart instructions in `docs/VLLM_RESULTS.md` and `docs/GYM_RESULTS.md`. Do not claim evidence_first improvement or a verified Red Hat-distributed image.
- 23:50 Codex: Beacon client implemented with fake sensor, WAV replay, lazy GPIO/mic, durable outbox/backoff/receipts and `--flush`. 12 unit tests pass; isolated HTTP verification confirms fake sensor and cached replay each block the bridge and cut off 5 of 9 SOS pins; disconnected/restarted queue produces one received report. Evidence in `beacon/evidence/`. Pi hardware and exactly-once backend deduplication remain pending.
- 23:36 Codex: private H100 Lightning BF16 vLLM serving; five live hero runs passed. Fixed vLLM native tool decoding and bounded model-facing route context (full UI geometry preserved); 30 backend + 25 Gym tests pass. Gym rerun active; shutdown still required.
- 23:15 Claude: agent fixes (Lightning-only default, landmark matching, bridge direction
  grouping, retries, real tool descriptions, one tool per turn, trusted beacon position);
  `/api/radio` hero flow, confirm, status, demo seed on real roads; Beacon sensor + audio
  endpoints; ASR hook; tests (28 backend pass); this file; briefs; README.
- 19:45 Codex: Gym rollouts on test split (baseline vs evidence_first).
- 18:48-18:54 Codex: integration merge, radio agent, radio parser.
