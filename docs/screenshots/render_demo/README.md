# Public Render + Vercel verification

These are captures of **https://sosora-command-demo.vercel.app**, connected to
**https://sosora-command-demo.onrender.com**. They are public deployment evidence.

- `01_seed.jpg`: nine reachable, zero cut off.
- `02_beacon.jpg`: five cut off, four reachable, one physical bridge avoided.
- `03_dot.jpg`: an unverified DOT opening leaves the bridge avoided.
- `04_responder_review.jpg`: ambiguous report asks which bridge; no road closed.
- `05_responder_confirm.jpg`: operator confirms the eastern bridge; five cut off.
- `06_after_rebuild.jpg`: fresh load after correcting the Vercel root to `frontend`; banner, cached trace and WebSocket connection verified.

The disclosure banner and cached replay trace badge remain visible. Full DOM
states, console output and HTTP/WebSocket evidence are in
`docs/evidence/render_demo_2026-10-18/`. Actions used the drill keyboard shortcuts
and clicked the eastern bridge confirmation button. The initial automated seed
click required a shortcut retry; the completed flow had no console errors.

The free CPU instance is slower than the local GPU system; screenshots do not
represent live inference or model latency. State is shared and ephemeral.
