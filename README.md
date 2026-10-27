# SOSora

**A Congressional App Challenge submission by Jia · A disaster-response app designed for unreliable communications.**

SOSora helps residents request help and field responders report damaged roads during a disaster. The iPhone app is the main way people use the project. A connected command system turns those reports into a shared map showing which households may have lost road access; the demonstration uses simulated SOS cases. The app, command tools, and field hardware together make up the submission.

**Try the [SOSora Command demo](https://sosora-command-demo.vercel.app)** · [Backend API](https://sosora-command-demo.onrender.com) · [Hosted demo notes](docs/HOSTED_DEMO.md)

> **Prototype notice:** SOSora is for demonstration and decision support. It does not contact 911, dispatch responders, or verify road safety. The hosted demo uses cached model responses and simulated incidents.

## The app

SOSora’s native iPhone app has two field workflows:

- **Request help:** residents record an incident type, location, number of people, and optional details. Requests are saved on the phone and can sync when a connection is available.
- **Report a road:** responders choose a road from the map and record whether it is passable, blocked, or unknown, with a note and time. Reports are saved locally and queued for sync. Photos stay on the phone and are not sent to the current API.

The app shows sync state and lets residents review accepted request statuses. The local queue helps preserve reports through a connection outage; the live command and AI analysis still depend on the connected system described below.

<table>
  <tr>
    <th>Resident · request help or report roads</th>
    <th>Field responder · inspect a selected road</th>
  </tr>
  <tr>
    <td><img src="docs/screenshots/mobile-resident-home.png" alt="SOSora resident home on iPhone, with Request Help, Report Roads, and a simulated sample request" width="100%"></td>
    <td><img src="docs/screenshots/mobile-responder-map.png" alt="SOSora field responder map on iPhone, showing simulated incidents and a selected road marked unknown" width="100%"></td>
  </tr>
  <tr>
    <td><a href="docs/screenshots/mobile-sos-form.png">View the SOS form</a></td>
    <td><a href="docs/screenshots/mobile-road-report.png">View the road report form</a></td>
  </tr>
</table>

Screenshots are from an iPhone 17 Pro simulator running iOS 26.5. Sample requests are labeled **SIMULATED**. Map locations are for demonstration; the displayed road geometry is not a validated driving route.

## How the full project works

The app is the field interface, and the rest of SOSora supports the shared response workflow:

1. A resident submits an SOS or a responder records a road observation in the iPhone app. A Raspberry Pi Beacon can also send a voice report or water-level reading.
2. When connected, the Command API receives reports and updates the command map. Radio language can be transcribed and parsed into candidate information for review.
3. The system checks road evidence against a real OpenStreetMap road graph and recalculates which simulated SOS locations remain reachable.
4. A person reviews ambiguous locations and important road changes. An unverified field note cannot, by itself, prove that a road is safe or reopen it.

The AI proposes structured information and uses tools to inspect and update the exercise. Code enforces road-trust rules and reachability. If a location is ambiguous or a tool fails, the system can leave the state unknown and request review instead of presenting a guess as fact.

## Command map

The web command view gives field reports a shared operational picture. This screenshot shows a **simulated** Beacon report, a blocked road, and five simulated SOS locations whose access changed during the exercise.

![SOSora Command dashboard: simulated Beacon report, blocked road, and five cut-off incidents](docs/screenshots/cinematic/freeze/hero-ready.png)

[Idle map](docs/screenshots/cinematic/freeze/idle.png) · [Ambiguous bridge awaiting review](docs/screenshots/cinematic/freeze/ambiguity.png) · [Confirmed bridge assessment](docs/screenshots/cinematic/freeze/confirmed-ready.png) · [Presentation mode](docs/screenshots/cinematic/freeze/presentation.png) · [Helene track view](docs/screenshots/ui-helene-1920x1080.png) · [Incident details](docs/screenshots/ui-incident-1920x1080.png)

## Why it matters

During a hurricane, phone networks and roads can fail at the same time. During Hurricane Helene, the FCC reported that about **74.3% of cell sites were out** in the designated 21-county North Carolina disaster-reporting area in its September 28, 2024 snapshot. By November 1, NCDOT had identified **more than 8,100 damage sites** involving roads, bridges, and culverts. North Carolina’s after-action review recommended preparing local emergency managers to operate without communications for up to **72 hours**. These figures describe a past disaster and a preparedness recommendation, not SOSora’s performance. ([FCC report](https://docs.fcc.gov/public/attachments/DOC-405893A1.pdf) · [NCDOT release](https://www.ncdot.gov/news/press-releases/Pages/2024/2024-11-01-ncdot-relief-efforts-helene-western-nc.aspx) · [North Carolina after-action review](https://www.ncdps.gov/tropical-storm-helene-after-action-review))

## What the prototype demonstrates

The primary walkthrough is a simulated exercise on real roads in Swannanoa, North Carolina. A voice report describes a collapsed bridge. The system finds the corresponding road, records the report, and recalculates access for nine simulated SOS locations. In the exercise, blocking the eastern Warren Wilson Road bridge cuts off five of the nine locations. A later unverified “bridge open” report does not clear the closure. If a responder report could refer to either of two bridges, the command workflow asks for human confirmation.

These are saved prototype evaluations, not predictions of field performance:

| Evaluation | Result | What it means |
|---|---|---|
| Tool-use exam · 42 synthetic scenarios, 3 runs | **41/42 average** with audited argument repair (runs: 41, 40, 42) | Three reasoning failures remained across 126 attempts. The repair corrects a narrow formatting issue; it does not change the model’s decision. [Results and method](docs/GYM_RESULTS.md) |
| Bridge and ambiguity checks · fresh-seed runs | Correct bridge and affected households: **20/20** · ambiguous reports held for review: **10/10** | In 9 of the 10 ambiguous runs, code rejected a model attempt to make an unsafe road change. [Reliability evidence](docs/evidence/reliability_2026-10-18/summary.json) |
| Agent step latency | **0.85 s** on one NVIDIA H100 with vLLM | Compared with 24–55 s on the measured hosted API path. This benchmark used remote GPU inference. [Serving measurements and limits](docs/VLLM_RESULTS.md) |

The 42-case exam uses synthetic task families. It does not establish real-world accuracy, safe dispatch, or readiness for emergency use. The optional aerial-imagery experiment is not used to determine road status because it did not outperform the existing model in the sealed comparison. [Vision results and limitations](docs/ml/V3_RESULTS.md)

## Offline capabilities and next steps

Today, the iPhone app and Beacon can save reports locally and queue them for later delivery. The local prototype also includes a road graph, routing code, and offline demo replay. The fully live AI workflow has been measured with remote NVIDIA H100 inference; running the full live model entirely offline on a laptop has not been benchmarked.

Jia plans to use the project’s NVIDIA DGX Spark prize to improve offline operation across the whole system:

1. **Run inference locally:** evaluate a suitable Nemotron serving setup on the DGX Spark so report parsing and tool calling can continue without an internet connection.
2. **Prepare local data:** keep the road graph, map assets, model weights, and speech-recognition files available on the command device before deployment, without relying on online downloads or map tiles.
3. **Connect app, Beacon, and Command over a local network:** let phones and Beacons send queued reports to a nearby command device even when the wider internet is unavailable; preserve reports until Command confirms receipt.
4. **Test outage recovery end to end:** disconnect internet and local links in controlled exercises, restart devices, confirm that reports remain queued without loss or duplication, and measure how long the complete workflow can operate offline.

These are planned improvements, not current guarantees. The goal is for field teams to keep recording, reviewing, and mapping reports during an outage, then synchronize safely when a connection returns.

## Recognition

At the NVIDIA–Red Hat hackathon, SOSora won **1st place in Tool Calling**; judges also complimented Jia’s mobile app. The prize was an **NVIDIA DGX Spark**.

## Technology

- **iPhone app:** SwiftUI, local persistence, connectivity monitoring, queued sync.
- **Command interface:** Next.js, MapLibre, streamed incident and assessment view.
- **API and routing:** FastAPI and NetworkX, using an OpenStreetMap road graph for the Swannanoa demonstration area.
- **Radio parsing and tool calls:** NVIDIA Nemotron 3.5 Lightning through vLLM; deterministic code validates candidate road updates and recomputes reachability.
- **Speech and field hardware:** local Whisper `tiny.en` speech recognition option and a Raspberry Pi Beacon prototype with a microphone and water-level sensor.
- **Evaluation:** NVIDIA NeMo Gym scenarios and verifiers.

```text
Resident / responder iPhone ─┐
Raspberry Pi Beacon ─────────┼──> Command API ──> evidence checks ──> road graph
Radio reports ───────────────┘                         │
                                                      └──> reachability map
```

**Real:** app, API, road-network geometry, routing code, and evaluation tools. **Simulated:** SOS cases, radio reports, responder locations, and the disaster exercise. Imagery-derived outputs are experimental and are not treated as verified road evidence.

## Run the prototype

The local iPhone app and Command service are the main project experience. Xcode, Python 3.12, and the backend requirements are needed. Installing dependencies requires internet access.

### iPhone simulator

1. Start the Command API in demo mode from the repository root:

   ```bash
   cd backend
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   DEMO_MODE=true .venv/bin/uvicorn app.main:app --port 8000
   ```

2. Open [`ios-app/SOSora App.xcodeproj`](ios-app/SOSora%20App.xcodeproj) in Xcode and run it on an iPhone simulator.
3. In the app’s **Sync** tab, set the server address to `http://127.0.0.1:8000` and choose **Sync now** to check the connection.

For a physical iPhone, use the Mac’s LAN address in Sync settings and run the backend with `--host 0.0.0.0`; the phone and Mac must share a network. See [iOS setup notes](ios-app/README.md).

### Web Command demo

With the backend running, start the Next.js interface in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and choose **Run demo**. The local demo uses cached model responses; road tools and reachability calculations run against the local road graph. Map tiles may require network access or a browser cache.

## Project files

- `ios-app/` — resident and field-responder iPhone app.
- `backend/` — Command API, radio agent, trust rules, and routing.
- `frontend/` — web command map and incident workflow.
- `dashboard/` — separate experimental operations dashboard.
- `beacon/` — Raspberry Pi Beacon prototype.
- `ml/` — model serving, evaluation, and experimental vision work.
- `docs/` — setup instructions, evaluation evidence, and prototype limitations.

For the mobile API contract, see [`backend/app/mobile_api.py`](backend/app/mobile_api.py). For deployment details, see [hosted demo notes](docs/HOSTED_DEMO.md).
