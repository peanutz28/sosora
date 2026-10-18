# UI merge brief for Codex: one beautiful dashboard (owner: Ria)

Read `docs/CONTEXT.md` first. Deadline 11:00 AM. Beautiful UI is a top judging priority.

## Decision (already made, do not revisit)
There are two dashboards. We ship **one**:
- **Engine = `frontend/` (Next.js + MapLibre).** Keep it. Its map draws the real OSM road
  graph, real routes and closures, and it is wired to `backend/` (port 8000) where the radio
  flow and the tool-calling agent live.
- **Look = Jia's `dashboard/frontend/index.html`.** Port her visual design into `frontend/`:
  palette, DM Sans + Manrope type, brand header, incident cards, map bar, legend footer,
  detail panel, pills. Open her file and copy the feel closely.
- **Do not delete or modify** `dashboard/` or `ios-app/` (Jia's work, separate deliverables).

## Already done by Claude (committed on `integration`; verify, then build on it)
- `frontend/app/globals.css`: `@theme` tokens replaced with Jia's palette
  (bg #090b0e, surface #0e1b25, elevated #152631, card #182f3c, ink #f4f7f8, muted #b4c7d0,
  faint #7d95a2, line #29404c, accent/route teal #3ee0cf, on-accent #08252a, critical #ff6d78,
  warning #f0b429, live cyan #22d3ee), pin colors updated, and new CSS for hero visuals:
  `.shockwave`, `.beacon-pin`, `.candidate-pin`, `.wave`, `.row-in`, `.font-display`, `.font-mono`.
- `frontend/app/layout.tsx`: DM Sans (`--font-dm`), Manrope (`--font-manrope`), IBM Plex Mono.
- Teal buttons now use `text-on-accent` (dark text on teal) in AppShell, RescueMap, IncidentSidebar.
- `frontend/public/helene-best-track.geojson`: real NHC best-track points for Helene (25 Points,
  properties include time, class_label, wind_kt). Copied from Jia's dashboard.

## Step 0: git (DONE by Claude at 00:30, skip)
Beacon work and the UI groundwork are committed, and `origin/main` (Jia's `dashboard/` +
`ios-app/`) is merged into local `integration` with no conflicts. The remote `integration`
branch was deleted after PR #1; push this branch again (`git push -u origin integration`)
and work on it. First run `cd frontend && npm install && npm run build` and
`cd backend && pytest -q`; both must pass before Step 1.

## Step 1: header (frontend/components/shell/Header.tsx)
Match Jia's header: 70px, bg #101114, bottom border. Left: 39px teal rounded-13px tile with "≋"
(dark text), wordmark `SOS<span teal>ora</span>` in Manrope 800 24px tight tracking, under it
"RESCUE INTELLIGENCE" 10px letter-spaced. Center: "Swannanoa operations drill · Western North
Carolina" + bordered "SIMULATION" tag. Right: Map/Model/Agent status dots (keep existing logic,
add an "Agent: idle | working" dot driven by Step 3), outline link "Resident SOS ↗" (to
`/resident` if it exists, else hide), and the teal primary "▶ Run demo" button.

## Step 2: layout + cards
- Left rail (IncidentSidebar, 275px, bg #0e1b25): eyebrow "OPERATIONS", title "Incident log" + count
  (Manrope 800 23px), segmented filter (All / Critical / Cut off), cards like Jia's `.incident`
  (rounded 12px, bg #152631, critical gets red inset left border, selected teal border, priority
  label, place + people, time). Add an access line on each card: teal "Route available" or red
  "No road access" from `lib/access.ts`.
- Map card: rounded 13px border #33505c, map bar on top (bg #132734): "◉ Swannanoa · Roads ·
  incidents · access", Street / Satellite toggle (existing basemap logic), and overlay toggles.
  Legend footer under the map (bg #102430) like Jia's: Rescue unit, SOS reachable (teal), SOS
  cut off (red "!"), Beacon (cyan), Blocked road (red), Contested (amber), Helene track.
- Right column 340px: **OpsConsole** (Step 3) by default; IntelPanel replaces it when an
  incident is selected (close returns to OpsConsole). Restyle IntelPanel like Jia's `.detail`.

## Step 3: OpsConsole, the hero panel (new: frontend/components/ops/OpsConsole.tsx)
This is where the demo happens on camera. Sections top to bottom:
1. **KPI tiles** (2x2, Jia's `.summary-grid` style, Manrope numbers): "Families cut off"
   (count of incidents with `reachable === false`, red, animate the number up), "SOS reachable"
   (teal), "Roads blocked" (`state.closures.length`), "Agent" (idle / working / needs review).
2. **Drill controls** (collapsible, small, hideable for filming; keyboard shortcuts in brackets):
   - [S] Seed drill: `POST /api/radio/demo/seed` -> store `hero_message`, `open_report`,
     `beacon_position` from the response; then fly the map to the Swannanoa drill area
     (center ~[-82.42, 35.618], zoom ~12.6).
   - [B] Beacon voice report: `POST /api/radio` `{message: hero_message, source_type:"beacon", lon, lat: beacon_position}`
   - [R] Responder radio, no location: same without lon/lat, `unit:"Engine 4"` (agent will ask to confirm)
   - [D] DOT says open: `{message: open_report, unit:"DOT"}` (bridge must stay blocked)
   - [W] Water sensor spike: `POST /api/beacon/beacon-ww-bridge/reading {"water_level_cm": 45}`
   These requests can take seconds (minutes on hosted API): fire-and-forget, show Agent "working",
   never block the UI; results arrive over the WebSocket.
3. **Radio feed**: events with `kind` in radio_received, voice_transcribed, radio_parsed,
   sensor_reading, radio_location_confirmed. Newest first. Newest row shows the cyan `.wave`
   animation for ~3 s. Show source (Beacon / Engine 4 / DOT), the message in quotes, and for
   radio_parsed a pill row: event_type, road_name, urgency.
4. **Agent trace**: events with kind agent_tool_call / agent_tool_result / agent_error, as rows:
   mono tool name chip (cyan), one-line arguments for calls, one-line result summary for results
   (e.g. find_segments -> "2 locations match -> needs review" or "1 bridge found";
   report_segment -> status; recompute_reachability -> "5 incidents lost access";
   errors in red). Rows animate in with `.row-in`. This panel is how judges SEE tool calling.
5. **Needs-review card** (amber): when the latest find_segments result has
   `distinct_locations > 1` and the assessment says `needs_human_review`, list the candidate
   bridges (dedupe ids by stripping `:f`/`:b`), label them A, B, show them on the map as
   `.candidate-pin` markers, and a "Confirm bridge A" button ->
   `POST /api/radio/confirm {radio_id, lon, lat}` using that candidate's centroid.
   `radio_id` comes from the radio_received event / POST response.
6. **Latest assessment** card: summary, affected ids, "Human review required" pill when true.

Data plumbing (frontend/hooks/useOps.ts): the socket currently only reads `payload.state`.
Also handle `{type:"agent_event", event}` and `{type:"radio_event", event}`: append to a
`stream` array (dedupe by `${id}-${kind}-${at}`), merge with `state.events` (the backend also
stores these events there), clear on seed/reset. Export `stream` and an `agentWorking` flag
(true from radio_received until the next `state` frame after submit_assessment result).

## Step 4: map additions (frontend/components/map/RescueMap.tsx)
- **Beacon marker**: `GET /api/beacons` -> `.beacon-pin` with "B" at each beacon, tooltip name.
- **Shockwave**: when `state.closures.length` increases, place a `.shockwave` marker (with an
  inner `<i>`) at the midpoint of the newest closure geometry; remove after ~5 s. Then keep the
  closure line red (#FF3B30, width 6) with a dark casing underneath.
- **Candidate pins** from Step 3 (amber, clickable = confirm).
- **Helene track overlay** toggle: load `/helene-best-track.geojson`, draw a line through the
  points sorted by `time` (#c084fc, dashed, 2px) plus small circles sized by `wind_kt`, label
  "Helene · NHC best track". Off by default.
- **Fly-to** prop so OpsConsole can center the drill area after seeding.
- Recolor existing layer paints to the palette: routes teal #3EE0CF, conflicts amber #F0B429,
  closures red, damage amber.

## Step 5: QA (do this, do not skip)
- `npm run build` passes, no TypeScript errors. `backend` tests pass.
- Run backend (`DEMO_MODE=true uvicorn app.main:app --port 8000`) and `npm run dev`. Click
  through S -> B, then S -> R -> confirm A/B -> D, then S -> W. Expected each time:
  bridge turns red with shockwave, 5 SOS pins flip to red "!", KPI "Families cut off" = 5,
  trace shows ~6 tool calls, D leaves the bridge blocked.
- Take screenshots at 1440x900 and 1920x1080 and save them to `docs/screenshots/`
  (they are useful for the video and README). Fix anything cramped, clipped or low-contrast.
- No phone-signal or "live dispatch" claims in the UI. Simulated items keep a SIMULATED pill.

## Step 6: wrap up
Update `docs/CONTEXT.md` (Status table + Changelog), update README screenshots section, commit
with a clear message, push `integration`, and open a PR to `main`.
