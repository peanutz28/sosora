# SOSora

**The rescue map that keeps working when the towers and the roads don't.**

**Video:** TODO — add the final submission video link.

**Hosted demo:** [SOSora Command](https://sosora-command-demo.vercel.app) ·
[Backend API](https://sosora-command-demo.onrender.com)
([health](https://sosora-command-demo.onrender.com/health)).
Cached replay on free CPU; the first load may need a cold start.
[Deployment and verification](docs/HOSTED_DEMO.md).

NVIDIA x Red Hat Small Models Hackathon (Raleigh, Oct 2026), built by two sisters (Team SOSora).
**Track:** Tool-Calling. **Bounties:** Best Use of Nemotron Lightning · Best Model Improvement with NeMo Gym · Best Use of Red Hat vLLM.

**What it is:** one GPU box in a county's emergency command truck, no internet required. Radio reports, a Raspberry Pi
water/voice beacon and an offline-first SOS app feed **NVIDIA Nemotron 3.5 Lightning**, served with **vLLM**, which calls
six tools over the real OpenStreetMap road graph and shows dispatchers who can still be reached. Code, not the model,
decides what changes on the map.

| Result (all simulated scenarios) | Measurement | Evidence |
|---|---|---|
| **NeMo Gym, sealed fresh exam 2** (42 unseen scenarios × 3 runs) | Baseline **31%** (39/126) → rewritten system prompt **71%** (90/126) → + argument repair **98%** (123/126); one change at a time | [GYM_RESULTS.md](docs/GYM_RESULTS.md) · [click-through of every attempt](docs/gym/index.html) |
| **vLLM agent step latency** | Hosted API 24–55 s per agent step → **0.85 s** on vLLM (one H100, BF16) | [VLLM_RESULTS.md](docs/VLLM_RESULTS.md) |
| **vLLM surge** | 100 simultaneous radio reports cleared in **20.6 s** vs 84.8 s one at a time (100/100 ok) | [surge.json](docs/evidence/vllm_2026-10-17/surge.json) |
| **Live reliability** (30 runs, fresh seed each) | Right bridge + exact five cut off **20/20**; ambiguous reports held for a human **10/10** (the model attempted a closure 9/10 times; code rejected all 9) | [summary.json](docs/evidence/reliability_2026-10-18/summary.json) |
| **Parameter budget** | Everything served (Nemotron with all experts + MTP, SegFormer, Whisper tiny.en) = **32.95B of 33B** | [PARAM_BUDGET.md](docs/PARAM_BUDGET.md) |
| **Vision hub layer** | Sealed 38-tile test: served v2 F1 0.31; retrained V3 0.27, so not promoted. Imagery is treated as a clue, never proof | [V3_RESULTS.md](docs/ml/V3_RESULTS.md) |

Notes: Gym gains come from instructions and an audited argument-repair layer (string `"None"` → null, 36 edits), not
weight training; the remaining three failures are reasoning errors. Served with vLLM v0.27.1 (upstream open-source vLLM).
Evidence notebook: [`notebooks/SOSora_Evidence.ipynb`](notebooks/SOSora_Evidence.ipynb).

## Features

- Beacon voice and water-sensor reports, durable retry outbox and offline SOS queue.
- Nemotron report parsing and tool calls grounded in real Swannanoa road geometry.
- Code-enforced road trust rules, ambiguity review and recoverable imagery outage drill.
- Graph reachability and a streamed command map showing affected simulated incidents.
- Key-free cached demo with real local graph/tool execution; live vLLM and ASR hooks.
- Reproducible NeMo Gym evaluations and fine-tuned aerial flood evidence.

> New contributor or AI agent? Read [`docs/CONTEXT.md`](docs/CONTEXT.md) first. It is the
> living source of truth for status, decisions and next steps.

## The problem
In a hurricane, two networks fail at the same time.

- **Phones go down**, so rescuers lose track of *who* needs help. During Hurricane Helene,
  about 74% of cell sites in North Carolina's 21-county disaster area were out (FCC, Sep 28 2024).
- **Roads go down**, so rescuers lose *how* to reach them. By Nov 1 2024, NCDOT had identified
  more than 8,100 damage sites on roads, bridges and culverts in western North Carolina.

North Carolina's own Helene after-action review found that communications broke down and
operational information wasn't shared, and recommended that local teams be able to operate
**without communications for up to 72 hours**. Today, a road report heard on the radio lives
on a whiteboard. Crews find out a bridge is gone by driving to it.

## What SOSora does
One field message changes the whole picture, in seconds, with no internet.

1. A **SOSora Beacon** (Raspberry Pi + mic + water-level sensor at a crossing) or a responder
   radio reports: *"the bridge on Warren Wilson Road is gone, three families on the far side."*
2. **Nemotron 3.5 Lightning** turns the garbled message into a structured report.
3. A **Lightning tool-calling agent** finds the real bridge on the OpenStreetMap road graph,
   checks its status and evidence, records the report, and recomputes who can still be reached.
4. The **command dashboard** shows the bridge go red and which families just lost their way out.

When something breaks, it says so instead of guessing: two bridges match -> it asks the
operator; a tool fails -> it reports "unknown"; a single "it's open" report -> the road stays
avoided until verified.

## Architecture
```
 SOSora Beacon (Pi, mic, water gauge) ─┐
 Responder radio (voice) ──────────────┼─> SOSora Command (one GPU box, mobile command vehicle, offline)
 SOSora SOS app (offline queue) ───────┘     speech to text -> Lightning parse -> Lightning agent (vLLM)
                                              -> tools: find road, status, imagery, report (trust rule), reachability
                                              -> offline OSM/NCDOT map -> command dashboard
 NeMo Gym: measures the agent on failure scenarios     Hub (when a link returns): DOT closures, aerial imagery + vision model
```

| Component | Code | Technology |
|---|---|---|
| Radio / Beacon intake, hero flow | `backend/app/radio_api.py` | FastAPI |
| Tool-calling agent + trust rule | `backend/app/agent.py` | Nemotron 3.5 Lightning, OpenAI-compatible tool calls |
| Radio parser | `ml/inference/radio.py` | Nemotron 3.5 Lightning, JSON mode, grounding check |
| Speech to text hook | `backend/app/asr.py` | OpenAI-compatible endpoint; local tiny.en in the measured setup |
| Routing + reachability | `backend/app/routing.py` | NetworkX on the real OSM graph (43,590 nodes / 86,254 edges) |
| Agent evaluation | `ml/nemo_gym/` | NVIDIA NeMo Gym resource server + verifier |
| Aerial flood evidence | `ml/vision/` | Fine-tuned NVIDIA SegFormer-B0 |
| Dashboard | `frontend/` | Next.js |
| Beacon | `beacon/` | Raspberry Pi, USB mic, HC-SR04 |

## Why these technologies
- **Nemotron 3.5 Lightning** is the only generative LLM (hackathon cap: 33B total). It is fast
  enough for an agent loop and strong at structured tool calls.
- **vLLM on one NVIDIA H100** serves Lightning through the configured `redhat_vllm` adapter.
  The verified deployment used upstream vLLM, not a verified Red Hat-distributed image.
  [Serving evidence](docs/VLLM_RESULTS.md).
- **NeMo Gym** gives fixed tasks and a verifier, so we can measure whether the agent improves.
- **Small models** are the point: the state's own review asks for 72 hours with no comms.

## Results and limitations

The headline table above uses saved evidence. [Gym methodology and historical
comparisons](docs/GYM_RESULTS.md), [live serving measurements](docs/VLLM_RESULTS.md),
and [vision evaluation](docs/ml/FROZEN_EXTERNAL_EVALUATION.md) retain the full
protocols and limitations. Experimental V3 lost its sealed comparison and is not
served; see [V3 results](docs/ml/V3_RESULTS.md).

## What is real and what is simulated
Real: OpenStreetMap / NCDOT roads, the routing graph, Nemotron model calls, NeMo Gym evals,
vision evaluation numbers, Helene statistics (sourced). **Simulated and labeled:** SOS
incidents, radio messages, rescue units. SOSora is a hackathon prototype, not a dispatch system.

## Command dashboard screenshots

Jia’s night-operations visual design now runs on the Next.js / MapLibre command dashboard,
with the existing road graph, agent and trust rule. All drill SOS incidents and radio reports
remain labeled **SIMULATED**. In `DEMO_MODE=true`, parsing and the agent plan use cached demo
fixtures; tool execution and reachability run against the real graph.

![Command dashboard, 1440×900](docs/screenshots/ui-hero-1440x900.png)

[1920×1080 hero view](docs/screenshots/ui-hero-1920x1080.png) ·
[Ambiguous bridge review](docs/screenshots/ui-ambiguity-1440x900.png) ·
[1920×1080 bridge review](docs/screenshots/ui-ambiguity-1920x1080.png) ·
[NHC Helene track](docs/screenshots/ui-helene-1920x1080.png) ·
[Incident details](docs/screenshots/ui-incident-1920x1080.png)

Use **Run demo** to seed and submit the Beacon report. The collapsible drill controls also
support **S** seed, **B** Beacon, **R** responder without location, **D** unverified DOT open
claim, and **W** sensor spike. Two matching bridges require an operator to confirm a real
candidate on the map or in the console. The radio feed, tool trace and access counts update
over WebSocket; the interface stays interactive while an assessment runs.

Validation: `node --test frontend/tests/*.test.cjs`, `cd backend && pytest -q`, and
`cd frontend && npm run build`. Saved [UI QA evidence](docs/evidence/ui_merge_2026-10-18/)
covers the Beacon, ambiguity/confirmation, DOT and sensor paths. A production build can run
beside the dev server with `SOSORA_NEXT_DIST_DIR=.next-build npm run build`.

## Run it

Prerequisites: Git, **Python 3.12** (`python3.12`), Node.js and npm (verified with
Node 25.8.2 / npm 11.11.1). Dependency installation needs internet access. Cached
parsing/agent replay needs no API keys or ML service; map tiles need network/cache.
Run each block in a separate terminal, starting from the repository root.

```bash
# First clone, then open the checkout in each terminal below.
git clone https://github.com/peanutz28/sosora.git
cd sosora
# Before integration is merged into main:
git checkout integration
```

Terminal 1 — backend (leave running):

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
DEMO_MODE=true .venv/bin/uvicorn app.main:app --port 8000
```

Terminal 2 — command dashboard (leave running):

```bash
cd frontend
npm install
npm run dev
```

Open [localhost:3000](http://localhost:3000) and select **Run demo**. The frontend
uses `http://127.0.0.1:8000` by default. If either port is occupied, stop that server
or choose another port: backend `--port 18000`; frontend
`NEXT_PUBLIC_APP_API_URL=http://127.0.0.1:18000 npm run dev -- --port 13000`.

Terminal 3 — verify the hero flow using the actual seed message:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail -X POST http://127.0.0.1:8000/api/radio/demo/seed -o /tmp/sosora-seed.json
python3.12 - <<'PYCODE' > /tmp/sosora-radio.json
import json
with open('/tmp/sosora-seed.json') as f:
    seed = json.load(f)
print(json.dumps(dict(message=seed['hero_message'], source_type='beacon',
                      lon=-82.42702, lat=35.61258)))
PYCODE
curl --fail -X POST http://127.0.0.1:8000/api/radio \
  -H 'content-type: application/json' --data-binary @/tmp/sosora-radio.json
```

Expected: nine simulated incidents seeded; `assessment.affected_incident_ids`
contains SOS-001 through SOS-005. Seeding resets the drill. Stop servers with Ctrl-C.

Tests from the repository root:
`(cd backend && .venv/bin/python -m pytest -q)` and
`node --test frontend/tests/*.test.cjs`.
[Fresh-clone verification and environment notes](docs/QUICKSTART_VERIFICATION.md).

Live models: set `DEMO_MODE=false` and `NVIDIA_API_KEY` (hosted) or `LLM_BASE_URL` /
`LLM_MODEL` / `LLM_API_KEY` (your vLLM server). ML service: see `docs/ml/` (Python 3.12).

## Repository map
`backend/` app API, agent, radio + beacon endpoints · `ml/` model service, Gym, vision ·
`frontend/` dashboard · `beacon/` Raspberry Pi device · `docs/CONTEXT.md` living context ·
`docs/briefs/` task briefs for each workstream · `contracts/` API contracts ·
`docs/ml/PREVIOUS_README.md` detailed ML notes.

## Operations dashboard and native iOS app
Two additional applications live beside the agent stack. They do not replace `backend/`, `frontend/`, or `ml/`.

| App | Path | What it is |
|---|---|---|
| Operations dashboard | `dashboard/` | FastAPI plus a Leaflet map for Swannanoa. SOS incidents, road reports, access analysis, the Helene best track, and current weather. |
| Native iOS app | `ios-app/` | SwiftUI field app. Residents queue an SOS offline. Operators can review incidents and send a road report. |

The iOS app supports the Command mobile adapters; its current default is `http://192.168.68.80:8000`. Set the server URL for your own machine in Sync settings; see [iOS setup](ios-app/README.md). The separate operations dashboard uses port 3000, so run it separately from the Next.js dashboard.

Shared HTTP contract:

- `GET /api/health` and `GET /api/state`
- `POST /api/incidents` with `client_id`, `message`, `people`, `place`, `lat`, `lng`
- `PATCH /api/incidents/{id}` with a status of Received, Acknowledged, Under review, or Resolved
- `GET /api/road-segments` and `POST /api/road-reports`

Road geometry in `dashboard/frontend/roads.geojson`, `dashboard/swannanoa_roads.graphml`, and `dashboard/swannanoa_roads.gpkg` is the Swannanoa OpenStreetMap extract. The NHC Helene track used by the map is `dashboard/frontend/helene-best-track.geojson`.

### Run the operations dashboard
```bash
cd dashboard
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```
Open http://127.0.0.1:3000. The resident page is http://127.0.0.1:3000/resident. Tests: `.venv/bin/python -m unittest tests.test_roads tests.test_ops`.

The radio gateway reads `SOSORA_GATEWAY_TOKEN` from the environment. Do not commit that value.

### Run the iOS app
Open `ios-app/SOSora App.xcodeproj` in Xcode, select an iPhone simulator, and run. Start the operations dashboard first. The simulator can reach `127.0.0.1:3000`. A physical iPhone needs the Mac's LAN address in the app's server setting, and the phone and Mac must be on the same network.
