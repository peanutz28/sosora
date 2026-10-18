# Filming runbook

Run commands from the repository root, each long-running service in a separate terminal.
Use the same checkout for every terminal. Exercise incidents are SIMULATED even with live models.
Do not interrupt another operator's recording. Isolated rehearsal ports: backend 18001,
frontend 13000; reuse the read-only ML 18002 and ASR 8003 services.

## Start in order

1. Start the retained GPU only if it is stopped (do not restart a healthy serving container):
   ```sh
   ml/tools/brev start sosora-lightning-vllm
   ml/tools/brev exec sosora-lightning-vllm @scripts/vllm/serve_brev.sh
   ml/tools/brev port-forward sosora-lightning-vllm -p 18080:8000
   ```
   Keep the port-forward running. If a tunnel is already active, use its URL in
   `LLM_BASE_URL`; the private `.env.vllm` must point to that tunnel.
2. Load private settings in each ML/backend/preflight terminal without printing them:
   ```sh
   set -a
   source .env.vllm
   set +a
   export DEMO_MODE=false LLM_PROVIDER=redhat_vllm
   export ML_SERVICE_BASE_URL=http://127.0.0.1:18002
   export ASR_BASE_URL=http://127.0.0.1:8003 ASR_MODEL=tiny.en
   ```
3. ML parser (skip if healthy on this port):
   ```sh
   ml/.venv312/bin/python -m uvicorn ml.inference.app:app --host 127.0.0.1 --port 18002
   ```
4. ASR (requires prepared `ml/artifacts/asr-tiny.en`; see beacon/README.md):
   ```sh
   ml/.venv312/bin/python -m uvicorn beacon.asr_server:app --host 127.0.0.1 --port 8003
   ```
5. Backend, after loading settings from step 2:
   ```sh
   ml/.venv312/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
6. Frontend:
   ```sh
   cd frontend
   NEXT_PUBLIC_APP_API_URL=http://127.0.0.1:8000 npm run dev
   ```
7. Preflight, from root with step 2 settings:
   ```sh
   scripts/demo/preflight.sh
   ```
   Every line must PASS. A failure exits nonzero and withholds seeding. Preflight
   deliberately resets the demo on success. It checks service readiness, not ASR
   transcription quality or frontend-to-backend configuration. Open localhost:3000,
   wait for the map and live socket, then press S so this browser receives its drill payload.

## Beats and shortcuts

Click outside input fields. Wait for each assessment to finish before the next key.

| Key / beat | Expected picture |
| --- | --- |
| S — seed/reset | 9 SIMULATED SOS, 9 reachable, 0 cut off, no blocked crossing. |
| B — located Beacon | Known Warren Wilson crossing closes; SOS-001 through SOS-005 cut off, 4 reachable. Two directed road edges represent one physical bridge. Live model metadata and tool trace, then operator sign-off. |
| A — acknowledge | Acknowledge an outstanding review request through the existing review action (no effect when no review is requested); does not reopen roads or confirm an ambiguous bridge. |
| D — unverified DOT open claim, after B | Needs review (the live model may request location disambiguation before recording the contested claim); closure remains, 5 cut off and 4 reachable. Do not describe this source as verified authority. |
| S, then R — responder without coordinates | Needs review, two bridge candidates; no guessed closure, all 9 reachable. Click the Warren Wilson candidate to confirm; then 5 cut off, 4 reachable. |
| S, then W — water spike | 45 cm sensor report at the registered Beacon triggers bridge assessment; 5 cut off, 4 reachable. |
| I — imagery outage toggle | SIMULATED imagery evidence offline/restored; road graph, radio and access counts remain usable. Basemap tiles are separate. |
| P — presentation toggle | Cleaner map presentation; simulated labels stay visible. Toggle again to restore. |

For a voice beat use a real recorded WAV through `/api/radio/audio` or the Pi replay
command in beacon/README.md. Verify `transcript.mode=live`; do not present the named
`demo_hero.wav` cached fallback as live speech recognition.

## Reset between takes

Wait until no assessment is running. Restore imagery with I if offline, leave P mode
if needed, close incident details, then S. Verify 9/9 reachable and 0 cut off before
starting. S clears previous reports and road status. After a browser reload, press S
again to load the drill payload needed by B/R/D/W. Do not reset a shared backend while
another person records. For isolated runs use a separate database via `create_app`
(the default `app.main` uses backend/data/sosora.db), frontend dist directory and ports.

If a development-tab reload shows a failed map chunk or unavailable Beacon registry,
open a fresh tab and rerun S; this restored the live browser check during rehearsal.
Do not start filming until the map, Beacon marker and Connected label are present.

Keep model identity and counts legible; hold the final result for several seconds.
A working animation is not completion. Report any provider error, fallback, counter
mismatch, map flicker or console exception; do not silently substitute cached mode.

## Exact isolated rehearsal commands

After step 2, substitute these for steps 5–7 (each server in its own terminal):

```sh
PYTHONPATH=backend ml/.venv312/bin/python -m uvicorn scripts.demo.isolated:create --factory --host 127.0.0.1 --port 18001
```

```sh
cd frontend
NEXT_PUBLIC_APP_API_URL=http://127.0.0.1:18001 SOSORA_NEXT_DIST_DIR=.next-filming ./node_modules/.bin/next dev --turbopack -p 13000
```

```sh
BACKEND_URL=http://127.0.0.1:18001 FRONTEND_URL=http://127.0.0.1:13000 scripts/demo/preflight.sh
# Destructive only to the selected rehearsal backend; do not point at a recording session:
BACKEND_URL=http://127.0.0.1:18001 ml/.venv312/bin/python scripts/demo/rehearse.py
```

Open localhost:13000 for browser checks. The factory creates a fresh temporary database
for each server process. Stop only your own server processes with Ctrl-C afterwards;
leave shared model/ASR/tunnel services running for the recording operator.

## Verification record

See [filming evidence](evidence/filming_2026-10-18/README.md) for the three live API
runs, browser observations, fixed reset bug, and limits of the verification.
