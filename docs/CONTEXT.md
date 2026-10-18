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
| Merge ML + dashboard into `integration` | Done locally, **NOT PUSHED** as of 23:15 | `git log integration` |
| Radio parse (Lightning) | Works live, 2.7-4.1 s/message | live run 2026-10-17 ~23:00 |
| Agent + trust rule, real OSM graph | Works in demo replay; live Lightning resolves the right bridge | `backend/tests/test_radio_api.py` |
| Live agent speed | **Too slow on hosted API: 24-55 s per turn** | live runs ~23:05 |
| Beacon sensor + audio endpoints | Endpoints done, hardware not started | `backend/app/radio_api.py` |
| ASR model | Not chosen/served | `backend/app/asr.py` TODO |
| Gym results | test: baseline 1/14 -> evidence_first 4/14, **polluted by 18 HTTP errors + 5 timeouts** | `ml/nemo_gym/evidence/rollouts_2026-10-17/summary.md` |
| vLLM on Brev | Not started ($700 credits available) | |
| Dashboard wired to radio flow | Not started | |
| Video | Not started | |

## Open issues / gotchas
- Python 3.12 required for `ml/` (uses `asyncio.timeout`). Two `ml/tests/test_radio.py`
  provider tests fail on 3.10 only.
- Live agent: model batched tool calls with blank ids -> fixed (one tool per turn,
  `parallel_tool_calls: false`). Beacon position is injected by code, not the model.
- Hosted API latency makes live agent runs 2-4 minutes. Fix = vLLM on Brev.
- Gym numbers must be rerun on vLLM (same tasks, same verifier) before claiming improvement.
- `backend/data/sosora.db-journal` is a stray file from a sandbox run; safe to delete.
- Video: never show a phone with signal bars when claiming "no signal".
- Each radio report takes ~5-7 s even in DEMO_MODE: reachability runs one shortest-path
  query per incident on the 86k-edge graph. Optimization: one single-source Dijkstra from the base.

## Changelog (newest first)
- 23:15 Claude: agent fixes (Lightning-only default, landmark matching, bridge direction
  grouping, retries, real tool descriptions, one tool per turn, trusted beacon position);
  `/api/radio` hero flow, confirm, status, demo seed on real roads; Beacon sensor + audio
  endpoints; ASR hook; tests (28 backend pass); this file; briefs; README.
- 19:45 Codex: Gym rollouts on test split (baseline vs evidence_first).
- 18:48-18:54 Codex: integration merge, radio agent, radio parser.
