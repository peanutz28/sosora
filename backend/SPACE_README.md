---
title: SOSora Command cached demo
emoji: 🛰️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
---

# SOSora Command — hosted cached replay

This public CPU demo replays the simulated radio/Beacon scenario against the real
Swannanoa OpenStreetMap graph and deterministic trust/reachability code.
It does not run an LLM, ASR or vision model. The real system runs offline on one GPU box.

The database is ephemeral SQLite under `/tmp`. One server worker owns the shared
demo state and WebSocket broadcast. Other visitors can reset the shared scenario.
Set `APP_CORS_ORIGINS` to the Vercel production origin (comma separated for multiple origins).

Source: https://github.com/peanutz28/sosora (integration branch).
Road data: © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright).
Incidents, radio messages and Beacon readings are labeled simulated.
