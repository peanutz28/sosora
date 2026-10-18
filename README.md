# SOSora

**The rescue map that keeps working when the towers and the roads don't.**

NVIDIA x Red Hat Small Models Hackathon (Raleigh, Oct 2026). Track: **tool-calling**.
Built by two sisters in one weekend.

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
| Speech to text hook | `backend/app/asr.py` | NVIDIA ASR via OpenAI-compatible endpoint |
| Routing + reachability | `backend/app/routing.py` | NetworkX on the real OSM graph (43,590 nodes / 86,254 edges) |
| Agent evaluation | `ml/nemo_gym/` | NVIDIA NeMo Gym resource server + verifier |
| Aerial flood evidence | `ml/vision/` | Fine-tuned NVIDIA SegFormer-B0 |
| Dashboard | `frontend/` | Next.js |
| Beacon | `beacon/` | Raspberry Pi, USB mic, HC-SR04 |

## Why these technologies
- **Nemotron 3.5 Lightning** is the only generative LLM (hackathon cap: 33B total). It is fast
  enough for an agent loop and strong at structured tool calls.
- **Red Hat vLLM** serves it on one GPU, so the whole system can run in a command vehicle
  with no internet and handle many radio channels at once.
- **NeMo Gym** gives fixed tasks and a verifier, so we can measure whether the agent improves.
- **Small models** are the point: the state's own review asks for 72 hours with no comms.

## Results (measured; see evidence folders)
- **Agent policy, NeMo Gym, 14 held-out test scenarios** (Nemotron Lightning, hosted API):
  baseline 1/14 -> evidence-first prompting 4/14. Caveat: these runs had 18 provider HTTP
  errors and 5 timeouts, counted as failures. Rerun on vLLM pending.
  [`ml/nemo_gym/evidence/rollouts_2026-10-17/summary.md`](ml/nemo_gym/evidence/rollouts_2026-10-17/summary.md)
- **Vision fine-tune** (SegFormer-B0, 3.7M params), frozen cross-event check on 6 unseen
  Germany flood tiles: F1 0.23 -> 0.47 versus the same model before fine-tuning.
  [`docs/ml/FROZEN_EXTERNAL_EVALUATION.md`](docs/ml/FROZEN_EXTERNAL_EVALUATION.md)
- **Hero scenario** on real Swannanoa roads: the eastern Warren Wilson Road bridge is the only
  crossing in our map area for the neighborhoods north of it; blocking it makes 5 of 9 simulated
  SOS incidents unreachable. Covered by `backend/tests/test_radio_api.py`.

## What is real and what is simulated
Real: OpenStreetMap / NCDOT roads, the routing graph, Nemotron model calls, NeMo Gym evals,
vision evaluation numbers, Helene statistics (sourced). **Simulated and labeled:** SOS
incidents, radio messages, rescue units. SOSora is a hackathon prototype, not a dispatch system.

## Run it
```bash
# Backend (DEMO_MODE=true needs no API keys; uses cached parses and a cached agent trace)
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
DEMO_MODE=true .venv/bin/uvicorn app.main:app --port 8000
# Dashboard
cd frontend && npm install && npm run dev        # http://localhost:3000
# Try the hero flow
curl -X POST localhost:8000/api/radio/demo/seed
curl -X POST localhost:8000/api/radio -H 'content-type: application/json' \
  -d '{"message":"<hero_message from the seed response>","source_type":"beacon","lon":-82.42702,"lat":35.61258}'
```
Live models: set `DEMO_MODE=false` and `NVIDIA_API_KEY` (hosted) or `LLM_BASE_URL` /
`LLM_MODEL` / `LLM_API_KEY` (your vLLM server). ML service: see `docs/ml/` (Python 3.12).

Tests: `cd backend && pytest` (28 tests).

## Repository map
`backend/` app API, agent, radio + beacon endpoints · `ml/` model service, Gym, vision ·
`frontend/` dashboard · `beacon/` Raspberry Pi device · `docs/CONTEXT.md` living context ·
`docs/briefs/` task briefs for each workstream · `contracts/` API contracts ·
`docs/ml/PREVIOUS_README.md` detailed ML notes.
