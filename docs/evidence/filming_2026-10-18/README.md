# Filming verification — October 18, 2026

Services: isolated live backend 127.0.0.1:18001 with a separate temporary database;
isolated Next development server 13000 with `.next-filming`; shared ML parser 18002,
Whisper tiny.en ASR 8003, authenticated vLLM tunnel from private environment.
No recording backend or shared model server was restarted.

`preflight.txt`: all seven checks passed. `live_runs.json` and `live-runs.txt` retain
three sequential live API takes after the reset fix. Each take covers seed, Beacon,
unverified DOT, fresh-seed ambiguity, operator confirmation, fresh-seed 45 cm water
spike, imagery off/on, and acknowledgment. Every model assessment must report
`cached=false` and the expected Nemotron 3.5 Lightning model ID. Failures are retained,
not retried within a take. Exercise inputs remain simulated.

Expected outcomes: seed and ambiguous unlocated reports have 0 cut off / 9 reachable;
Beacon, confirmed location and water spike have exactly SOS-001 through SOS-005 cut
off / 4 reachable. Unverified DOT cannot reopen the bridge. Imagery and acknowledgment
do not change access. Browser displays one physical bridge, represented by two
OSM direction edges. Timings in JSON measure whole API beats, not model-call latency.

## Findings and fixes

- Reproduced: preflight/API seeding while a browser remained open merged old tool
  events into the next take. Old closures could remain in the displayed counter
  while the server had reset to 9 reachable. Added a reset generation to state and
  replace the previous stream on generation changes. Regression tests cover the
  generation and removal of old reachability/closure results. Browser observations
  after the fix showed fresh take history and 0/9/0 before closure.
- Missing requested A shortcut: wired to the existing acknowledgment action, guarded
  during work and while typing/modifier/repeat keys. It acknowledges an outstanding
  scenario review request; no request means no state change. It does not confirm
  bridge candidate A. Regression test exercises the actual shortcut effect.
- Model prose errors remain in the saved post-fix runs: take 1 water says "three
  other incidents (SOS-006–SOS-009)" instead of four; take 3 ambiguity says "eight SOS
  incidents examined" instead of nine. Take 2 DOT describes all four candidate
  direction IDs as blocked, although only the two directions of the known crossing
  were blocked. Take 3 DOT assigns its claim to the other crossing despite unresolved
  location. Structured access results and dashboard counters were correct. No prompt
  or model change was made to hide these unsupported statements. Read authoritative
  counts/location candidates from structured results when filming.
- Live ambiguity sometimes produced a `report_segment` attempt before disambiguation.
  The existing guard rejected it with `location unresolved; human review required`.
  No road was closed before operator confirmation. Recoverable tool errors are
  retained in post-fix JSON; they are not provider failures.
- Browser logs contain terrain-source/maxzoom warnings (see browser-warnings.json).
  No console error was observed. Brief socket reconnect labels appeared during the
  initial development/browser reload period; later sampled states were Connected.
  No reproducible map flicker was seen in sampled screenshots. This was spot checking,
  not a frame-by-frame recording audit, so absence of flicker is not certified.
- A later reload of the original development tab failed to load the MapLibre chunk
  and Beacon registry; B stayed disabled after a failed seed attempt. The chunk,
  registry endpoint and CORS probe returned HTTP 200 directly. A fresh browser tab
  loaded the map/registry and successfully submitted a live Beacon report. Root cause
  remains unconfirmed; no speculative source change was made. Saved DOM and image:
  browser-reload-failure.txt / browser-reload-failure.jpg. Reopen a fresh tab if this
  occurs; do not film the degraded view.

## Validation scope

18 frontend tests, 12 targeted backend tests, 4 preflight gating tests, TypeScript
`tsc --noEmit`, shell syntax check and `git diff --check` passed. XML/text evidence is
saved here. Browser spot checks covered streamed live metadata/counts, external
resets and P mode retaining simulation labels. `presentation.jpg` is a P-mode proof.
A fresh-tab live hero check also reached 5 cut off / 4 reachable / 1 physical bridge,
Ready for operator and Connected (`live-hero.jpg`).
Three complete sequences were driven through real HTTP APIs while the browser
subscribed; they were not three keyboard-only recordings. ASR was health-checked;
no microphone or recorded-audio transcription was exercised in these runs.
