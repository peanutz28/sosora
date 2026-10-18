# Final UI freeze pass

The UI is frozen after this pass except for bug fixes.

- All three access counters consume the same streamed `recompute_reachability` result. The fixed choreography delay was removed; the cut-off count starts immediately, while reachable/blocked values render synchronously.
- Successful, resolved assessments show teal **Ready for operator** in the header and tile, plus **Operator sign-off**. Structured bridge ambiguity or contested segment status remains yellow **Needs review**. Failed/fallback assessments are not presented as ready. Backend trust rules and the existing `needs_human_review` field are unchanged.
- The trace badge reads the additive `agent_runtime` field on existing agent events/responses: `cached`, `model_id`, `serving_backend`, and `last_call_latency_ms`. Live model IDs prefer the serving response's ID, falling back to the requested model ID. Serving names come from configured provider metadata. Latency measures the last successful model HTTP request, including response decoding, excluding graph/tools; it is never a routing or whole-report benchmark. Unavailable metadata is labeled unavailable. Cached runs show only **cached replay**, without an invented model/latency.
- The Next.js issue was reproduced by delaying the map style beyond the loading timeout: a child state updater called the parent setter during render. The timeout now notifies the parent outside the updater. `delayed-map-before.log` contains the reproduction; `delayed-map-after.log` confirms the same delayed-load path no longer emits that error.
- Glass panel opacity is 0.85. P mode explicitly hides the map key and keeps simulated labels visible.

## Evidence

- `frontend-tests.txt`: 13 passing frontend checks.
- `backend-tests.xml`: 22 passing agent/radio checks, including controlled-clock tests of real response-ID selection and latency instrumentation. No live GPU latency is claimed by these unit tests.
- `browser-verification.json`: 17 passing development-browser checks covering the hero, contested report, ambiguity, confirmation, water spike, primary demo, counter timing, metadata, sign-off, opacity and P mode; zero console errors and zero runtime exceptions.
- `build.log`: successful production build.
- Screenshots at 1920 × 1080: `idle.png`, `hero-ready.png`, `ambiguity.png`, `contested.png`, `confirmed-ready.png`, and `presentation.png`.

The new optional backend telemetry fields require the updated backend process. DEMO_MODE is labeled cached replay even if an older running backend has not yet emitted telemetry. No model-serving process was started for this pass.
