# Hosted cached demo — Render + Vercel

- Frontend: **https://sosora-command-demo.vercel.app**
- Backend API: **https://sosora-command-demo.onrender.com**
- Backend health: https://sosora-command-demo.onrender.com/health
- WebSocket: `wss://sosora-command-demo.onrender.com/ws/events`
- [Vercel project](https://vercel.com/peanutz28s-projects/sosora-command-demo)
- [Render service](https://dashboard.render.com/web/srv-dbab6j5g1s2s73bf8uc0)

The user chose Render's free plan after HF returned HTTP 402 for Docker CPU Space
creation. No HF subscription, paid compute, GPU or model credentials are needed
for this hosted replay. The original run stopped before its cutoff; the user
subsequently returned and explicitly requested this new Render deployment.

Deployment identifiers, source hashes, public responses and browser captures are
saved in [`render_demo_2026-10-18/`](evidence/render_demo_2026-10-18/).
The complete public API/WebSocket flow passed, including a final ping/pong.
The final verification summary is `readiness.json`; full HTTP/WebSocket exercise
responses are `public_smoke.json.gz`. Check those files before making a full-flow
verification claim.

## Runtime and limits

[`render.yaml`](../render.yaml) declares a Docker web service on **Free** compute,
using `backend/` as its build context and the `integration` branch. Auto-deploys
are off. The Docker process listens on port 7860 with one Uvicorn worker, so all
visitors share one scenario and WebSocket hub. The hosted entrypoint forces
`DEMO_MODE=true` and uses ephemeral SQLite in `/tmp`.

Render's free CPU makes graph operations noticeably slower than the local demo.
An initial test completed seed, Beacon and its WebSocket broadcast, then hit a
502 when the HTTP health check timed out during CPU work. The service now uses
Render's [default TCP health probe](https://render.com/docs/health-checks).
`/health` remains available for explicit API checks. The hosted Docker WebSocket
heartbeat allows long CPU bursts; the complete smoke test also checks a final
ping/pong after all report flows.

Free services [sleep after inactivity](https://render.com/docs/free), so the first
visit can take about a minute. SQLite state resets on sleep, restart or redeploy.
Other visitors can seed the shared drill. This is a cached demonstration; the
local offline GPU system and its measured live model results are separate.

## Configuration

Render's public settings are `PORT=7860`, `DEMO_MODE=true`, `HOSTED_DEMO=true`,
and `APP_CORS_ORIGINS` containing the production Vercel origin. The comma-separated
origin setting can also allow the team alias. No API keys or secret files are
configured. The image explicitly copies application code and the existing OSM
`graph.json`, `anchors.json` and `roads.geojson`, excluding local credentials,
databases, weights and environments.

Vercel’s project and deployment root are `frontend/`, matching the Git monorepo.
The project’s Git production branch remains `main`; the deployment helper can
publish an explicitly selected committed snapshot to production. It builds with:

```text
NEXT_PUBLIC_APP_API_URL=https://sosora-command-demo.onrender.com
NEXT_PUBLIC_HOSTED_DEMO=true
```

The existing client derives the WSS URL from the HTTPS API base. The hosted-only
banner says “Hosted demo · cached replay · the real system runs offline on one GPU
box”; its trace badge says `cached replay`, without model latency. Local default
URLs, `app.main`, local SQLite state, frozen UI styling and GPU services are
unchanged. Unfinished edits from other chats are excluded from the public build.

## Redeploy and verify

For a new user-authorized deployment after the original run's cutoff:

```sh
cd /Users/peanutz/Documents/GitHub/sosora
ml/.venv312/bin/python scripts/deploy/hosted_demo.py vercel \
  --resumed-by-user \
  --backend-url https://sosora-command-demo.onrender.com \
  --source-ref integration \
  --evidence-dir docs/evidence/render_demo_2026-10-18
ml/.venv312/bin/python scripts/deploy/hosted_demo.py status \
  --resumed-by-user \
  --backend-url https://sosora-command-demo.onrender.com \
  --evidence-dir docs/evidence/render_demo_2026-10-18
```

After Vercel is READY, run `connect` with the same flags. It verifies the public
page's disclosure and the production CORS preflight before writing `public_urls.json`.
Render backend updates use **Manual Deploy → Deploy latest commit** after pushing
the desired integration commit. Stay on the free plan; no disk or extra replicas.

```sh
/private/tmp/sosora-mobile-venv/bin/python scripts/deploy/smoke_hosted.py \
  --resumed-by-user \
  --base-url https://sosora-command-demo.onrender.com \
  --origin https://sosora-command-demo.vercel.app \
  --output docs/evidence/render_demo_2026-10-18/public_smoke.json.gz
```

The smoke sequence checks seed, Beacon hero, WebSocket broadcast, DOT opening
safeguards, responder ambiguity and operator confirmation. Browser QA uses the
same public site: S → B, D, S → R → confirm the eastern bridge, with screenshots.
Do not run competing seeds while verifying: the demo state is intentionally shared.

The initial HF failure evidence and earlier local-only checks remain in
[`hosted_demo_2026-10-18/`](evidence/hosted_demo_2026-10-18/). They are historical;
public verification belongs to the Render evidence folder.
