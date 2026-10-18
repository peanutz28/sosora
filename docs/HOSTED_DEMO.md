# Hosted cached demo — deployment handoff

Status: **not published**. On the user's resumed setup request, the
[SOSora Vercel project](https://vercel.com/peanutz28s-projects/sosora-command-demo)
was created in the existing Hobby account and linked to `frontend/`. Its hosted
disclosure flag is configured; the API URL is pending a working public backend.
No deployment was submitted. Setup evidence is in
[`vercel_resume_2026-10-18/`](evidence/vercel_resume_2026-10-18/).

Vercel authentication works as `peanutz28`. Hugging Face
accepted the account/token but returned HTTP 402 when creating a Docker Space on
`cpu-basic`, including a retry with default hardware. The server requires a PRO
subscription for free CPU Docker/Gradio hosting. No subscription was purchased,
no paid hardware was requested, and no broken production frontend was published.
Saved provider response: [`hf_failure.json`](evidence/hosted_demo_2026-10-18/hf_failure.json).
This account eligibility requirement is also in the [HF Spaces documentation](https://huggingface.co/docs/hub/spaces-overview).

| Service | Public URL | Verification |
|---|---|---|
| Backend | Intended target: `https://peanutz28-sosora-command-demo.hf.space` | Not created; HTTP 402 |
| Frontend | Not allocated | Project created and linked; deployment waits for healthy backend |
| WebSocket | Intended target: `wss://peanutz28-sosora-command-demo.hf.space/ws/events` | Public check blocked; exact Docker image passed locally |

The original agent run stopped before **06:30 AM ET, October 18, 2026**; the user
requested a new Vercel setup after returning. The original deployment commands
retain their cutoff guard. If HF still
blocks the free CPU target, drop hosting and use GitHub plus the video for judging.
The commands below are a human handoff; `--manual-handoff` is explicit permission
for the person running them to operate after the agent deadline.

## Exact commands

Run from the repository root. `HF_TOKEN` stays in ignored `ml/.env`, read in memory
only for authenticated HF actions. Vercel uses the existing terminal CLI login;
`VERCEL_TOKEN` in `ml/.env` is an optional alternative. Never copy either token into
a command argument, Docker build context, public environment variable or commit.

First resolve HF account eligibility yourself if you choose to continue. These
commands only request `cpu-basic`; they do not buy a plan or GPU.

```sh
cd /Users/peanutz/Documents/GitHub/sosora
ml/.venv312/bin/python scripts/deploy/hosted_demo.py prepare --manual-handoff
ml/.venv312/bin/python scripts/deploy/hosted_demo.py vercel-auth --manual-handoff
ml/.venv312/bin/python scripts/deploy/hosted_demo.py hf --manual-handoff
ml/.venv312/bin/python scripts/deploy/hosted_demo.py status --manual-handoff
```

If `hf` returns HTTP 402, stop here. Otherwise repeat `status` until the Space
runtime is `RUNNING`, then submit the frontend:

```sh
ml/.venv312/bin/python scripts/deploy/hosted_demo.py vercel --manual-handoff
ml/.venv312/bin/python scripts/deploy/hosted_demo.py status --manual-handoff
```

Repeat `status` until Vercel is `READY`. Connect the actual assigned origins, fetch
the public frontend without credentials, and smoke the public backend + WebSocket:

```sh
ml/.venv312/bin/python scripts/deploy/hosted_demo.py connect --manual-handoff
ml/.venv312/bin/python - <<'PY'
import json
import subprocess
from pathlib import Path
p = Path('docs/evidence/hosted_demo_2026-10-18/public_urls.json')
urls = json.loads(p.read_text())
subprocess.run([
    'ml/.venv312/bin/python', 'scripts/deploy/smoke_hosted.py',
    '--base-url', urls['backend_url'], '--origin', urls['frontend_url'],
    '--output', 'docs/evidence/hosted_demo_2026-10-18/public_smoke.json.gz',
    '--manual-handoff',
], check=True)
print('Frontend:', urls['frontend_url'])
print('Backend:', urls['backend_url'])
PY
```

`connect` must fail if Vercel serves a login/protection redirect or omits the hosted
banner. If protection blocks the site, use Vercel's project Deployment Protection
settings to allow public access, then rerun `connect`. Do not call a protected page
publicly verified. If HF rebuilds after CORS updates, wait for `RUNNING` before the
smoke command.

Open the returned frontend URL and check these exact UI actions: **S** seed
(all reachable), **B** Beacon hero (five cut off/four reachable), **S → R**
(asks which bridge without closing either), select the eastern bridge and confirm
(five cut off), then **D** (unverified DOT opening leaves the bridge avoided).
Capture screenshots with the disclosure banner and `cached replay` trace badge.
Add the verified frontend/backend URLs to the top of `README.md` and to
`docs/CONTEXT.md`, citing `public_urls.json` and `public_smoke.json.gz`, then commit.
No public screenshots or verified URL claims exist in this handoff.

## Package and local behavior

The [Dockerfile](../backend/Dockerfile) follows the [HF Docker SDK port contract](https://huggingface.co/docs/hub/spaces-sdks-docker):
port `7860`, unprivileged user, one Uvicorn worker and WebSockets. The dedicated
`app.hosted:app` entrypoint forces `DEMO_MODE=true` and uses SQLite at
`/tmp/sosora-hosted-demo.sqlite3`. The shared scenario resets on rebuild/restart,
and another visitor can seed it. There is no live model inference in this image.

The curated HF package includes Python application files, pinned requirements,
and the existing OSM `graph.json`, `anchors.json`, `roads.geojson`. It excludes
credentials, runtime databases, checkpoints, tests and local configuration. HF
Space metadata is in `backend/SPACE_README.md`; the push helper maps it to the
Space's root README. `APP_CORS_ORIGINS` is a comma-separated list of actual Vercel
origins. No wildcard is needed for the hosted site.

Frontend deployment packages only `frontend/` sources. The helper sets:

```text
NEXT_PUBLIC_APP_API_URL=https://peanutz28-sosora-command-demo.hf.space
NEXT_PUBLIC_HOSTED_DEMO=true
```

The existing client derives `wss://…/ws/events` from the HTTPS API base; no separate
WebSocket variable is needed. Both are public build settings, never secrets.
Without the hosted flag, the banner returns `null`; local API and WebSocket
defaults remain `http://127.0.0.1:8000` and `ws://127.0.0.1:8000/ws/events`.
Local `app.main`, its database and all GPU/model services remain unchanged.

To run the exact image locally, isolated from the active demo:

```sh
docker build --platform linux/amd64 -t sosora-hosted-demo:20261018 backend
docker run --rm --name sosora-hosted-demo-check -p 127.0.0.1:17860:7860 \
  -e APP_CORS_ORIGINS=http://127.0.0.1:17863 sosora-hosted-demo:20261018
```

See [`readiness.json`](evidence/hosted_demo_2026-10-18/readiness.json) for measured
checks, [`docker_backend_smoke.json.gz`](evidence/hosted_demo_2026-10-18/docker_backend_smoke.json.gz)
for saved HTTP/WebSocket responses, and [`screenshots/hosted_demo/`](screenshots/hosted_demo/)
for isolated preview captures. These are local checks, not public deployment proof.
