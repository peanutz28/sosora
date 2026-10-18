# Cinematic SOSora Command demo

The final UI freeze fixes and current screenshots are documented in [freeze/README.md](freeze/README.md). Earlier captures and the video below preserve the preceding cinematic checkpoint.

Visual changes are confined to `frontend/`. Existing HTTP requests, WebSocket events,
trust decisions, incident state, and demo actions are preserved. All captures use
1920 × 1080 pixels and the existing backend in DEMO_MODE with an isolated temporary
database. They show simulated SOS reports on real roads.

| State | Before | After |
|---|---|---|
| Idle: nine reachable SOS | [Before](before-idle.png) | [After](after-idle.png) |
| Hero: five isolated, four reachable | [Before](before-hero-after.png) | [After](after-hero-after.png) |
| Ambiguity: two bridges, confirmation required | [Before](before-ambiguity.png) | [After](after-ambiguity.png) |

`01-` through `08-` files preserve the screenshot checkpoints committed after each
ordered feature. The `after-` files show the cinematic delivery before the final freeze corrections; see `freeze/` for the current UI.

## Video takes

Press **P** outside an input to toggle presentation mode. It hides the incident log,
search, drill controls, Run demo button, basemap/layer/zoom controls, legend, and
assessment footer. Stats, radio, terminal, header, and `[SIMULATED]` remain visible.
Ambiguity confirmation stays available. Press P again to restore the controls.

Seed with **S**, toggle **P**, then press **B** for the Beacon hero or **R** for the
ambiguity case. Confirm **A** for the eastern bridge. **D** tests the unverified
reopening report; **W** tests the water spike. Existing Run demo also works.

[Hero recording, 15 seconds](hero-sequence-15s.mp4). This is an edited screen
recording of the real UI sequence with the middle wait removed to fit the requested
duration. Camera moves and the final closure/count-up sequence retain their original
playback speed. It is not a backend latency benchmark. Timing details are saved in
`recording.json`. The capture is silent at 25 fps. The [full hero capture](hero-sequence-realtime.webm)
is also included.

## Verification and performance

- Production build succeeds: `build.log`.
- Eleven frontend regression checks pass: `frontend-tests.txt`.
- Fifteen browser checks pass, including seed, hero, ambiguity, confirmation,
  reopening protection, water spike, primary Run demo, P/input handling, panel
  collapse, muted zeros, pin counts, terminal scrolling, and absence of page errors:
  `verification.json`.
- Idle RAF delivery measured 59.0 fps. The complete hero measured 56.9 fps, with a 16.8 ms 95th-percentile frame interval. Sustained 60 fps through the entire hero remains unmet on this machine.
- Browser frame samples are saved in `verification.json` and
  `hero-performance.json`. These measure requestAnimationFrame delivery at
  1920 × 1080, not a GPU profiler or a guarantee for other devices.
- Terrain starts at exaggeration 1.3. Sustained frame delivery below 55 fps disables
  terrain displacement first, retaining the AWS Terrarium hillshade. That fallback
  activated on this test machine. Shared route segments draw once to reduce
  overdraw; roads and SOS branches retain their backend geometry.
- Decorative POI icons, road shields, duplicate road casings, and 3D buildings are
  hidden to keep the hero close-up clear and reduce rendering work.

No requested visual feature was omitted. Broken-route stubs use the last reachable
route observed in the current browser session. Reloading an already blocked state
cannot reconstruct historical per-SOS geometry absent from that backend response;
reachable routes and the isolation zone still render. Map tiles and elevation still
need network access or browser cache, as with the existing tile-backed dashboard.
