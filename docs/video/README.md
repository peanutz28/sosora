# SOSora video asset kit

All graphics and delivery clips are **1920 × 1080**. The graphic set was rebuilt
with larger typography, real Swannanoa road geometry, simplified stat layouts,
and compact transparent lower-thirds. Only the replacement graphics are in `graphics/`. Graphics use the dashboard’s
night-operations palette, Manrope display type, DM Sans body type, and IBM Plex
Mono data labels. SVGs embed the font subsets, so editable text preserves its
appearance. Font licenses are included in `source/font-licenses/`.

## Graphics

Each entry in `graphics/` has matching `.png` and `.svg` files.

| File stem | Content |
|---|---|
| `01-title` | Title card |
| `02-stat-cell-sites` | 74% cell sites out; qualified NC reporting area and date |
| `03-stat-damaged-sites` | 8,100+ damaged sites; sites, not separate destroyed roads |
| `04-stat-72-hours` | NCEM communications-readiness recommendation |
| `05-system-diagram` | Beacon / SOS app → Command / Nemotron on vLLM → rescue map |
| `06-lower-tool-calling` | TOOL CALLING |
| `07-lower-nemotron` | NEMOTRON LIGHTNING |
| `08-lower-redhat-vllm` | RED HAT vLLM, explicitly qualified as an integration target |
| `09-lower-nemo-gym` | NeMo GYM |
| `10-results` | Source-backed Gym, live vLLM and exact parameter-budget results |
| `11-end-card` | End card |

The four lower-thirds have transparent full-HD canvases. Place them directly over
footage; the title bars sit within safe margins near the bottom. Other cards are
opaque. The gallery and contact sheet preview lower-thirds over footage; the downloadable
PNG/SVG files retain transparency. A contact sheet is in
`evidence/graphics-contact-sheet.jpg`.

## Stat sources and qualifications

- **74%:** rounded from the FCC’s September 28, 2024, 9 AM EDT snapshot for the
  designated 21-county North Carolina reporting area. It is not statewide, current,
  or a percentage of residents. [FCC report](https://docs.fcc.gov/public/attachments/DOC-405893A1.pdf).
  Primary hosting blocked direct retrieval during this session; the FCC’s
  [September 29 report, mirrored copy, p. 16](https://wirelessestimator.com/wp-content/uploads/2024/09/Hurricane.Helene.Cell_.Tower_.Status.pdf)
  independently corroborates the prior 74.3% figure.
- **8,100+:** NCDOT’s November 1, 2024 update reports more than 8,100 damaged sites.
  [NCDOT recovery update](https://www.ncdot.gov/news/press-releases/Pages/2024/2024-11-01-this-week-ncdot-now.aspx).
- **72 hours:** the NCEM / McChrystal Group after-action review recommends local
  emergency managers prepare to operate without communications for up to 72 hours.
  This is not a measured SOSora endurance result.
  [NC DPS review](https://www.ncdps.gov/tropical-storm-helene-after-action-review).

`10-results` draws numeric results only from `docs/GYM_RESULTS.md`,
`docs/VLLM_RESULTS.md`, and `docs/PARAM_BUDGET.md`. Exact source snapshots and hashes
are under `source/` and `evidence/results_source_hashes.json`. The slide retains
key limits: synthetic Gym cases, remaining missing-location/tool-failure failures,
and the distinction between guarded ambiguity outcomes and model-only abstention.
Actual model serving is upstream vLLM, not a verified Red Hat distribution; the
requested Red Hat lower-third states that limitation.

## B-roll

Named H.264 MP4s are in `broll/`; original Playwright WebM recordings are in
`broll/raw/`. Each beat starts from its own fresh seed on the isolated stack.
Delivery MP4s omit page loading and setup, retain real-time waits within the beat,
and use 30 fps with no speed changes. Playwright’s raw capture is 25 fps; conversion
duplicates frames to 30 fps and does not create additional temporal detail. Silent.
These clips are visual demonstrations, not latency benchmarks.

| Clip | Sequence |
|---|---|
| `01-seed.mp4` | Fresh seed; nine reachable SOS pins (code-only, no inference needed) |
| `02-beacon-hero.mp4` | Fresh seed → live Beacon report → five cut off / four reachable |
| `03-responder-confirm-A.mp4` | Fresh seed → ambiguous responder → operator clicks bridge A |
| `04-dot-open.mp4` | Fresh seed → Beacon closure as prerequisite → unverified DOT open report |
| `05-imagery-offline.mp4` | Fresh seed → I outage → live Beacon report and recoverable imagery error |
| `06-water-spike.mp4` | Fresh seed → water threshold report → live agent |

The DOT MP4 focuses on the DOT action; its raw recording also retains the fresh
seed and prerequisite Beacon closure. All recordings use presentation mode (P).
Simulated labels and map attribution remain visible. Live calls are verified by
`cached: false`, model IDs and parser modes in the matching `evidence/<beat>.json`.
Seeding itself does not call a language model. Normal imagery lookups return no
associated imagery for this scenario; the outage beat explicitly fails the tool.

The isolated stack uses frontend **13008**, Command **18008**, ML **18028**, and
private vLLM forward **18088**, with `/tmp/sosora-video-command.db`. It does not
mutate the other agents’ dashboard processes or databases. No model-serving flags,
GPU lifecycle state or secrets are changed or included in the deliverables.

## Rebuild and verification

- `source/build_graphics.py`: regenerate the SVGs from the bundled dashboard fonts.
- `source/render_graphics.cjs`: Playwright PNG rendering, font-bound checks, contact sheet.
- `source/record_broll.cjs`: isolated live capture; optional argument selects a named beat.
- `source/build_gallery.py`: regenerate the gallery with contextual lower-third previews.
- `source/check_graphics.cjs`: check visible glyph spacing, dimensions, transparency and gallery links.
- `source/verify_assets.cjs`: check PNG dimensions/transparency; fully decode MP4s;
  extract opening/middle/ending frames and create `manifest.json`.

The scripts record the local browser/dependency paths used here. Recording requires
an existing authenticated live vLLM environment and the isolated services above;
no credentials are stored in these files. `manifest.json` lists verified durations,
formats and file names. Evidence includes final screenshots, full response traces,
raw recordings, and contact sheets for visual review.
