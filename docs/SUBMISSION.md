# SOSora — submission draft

SOSora turns field reports into a map of who has just lost road access after a
hurricane. It connects voice and text SOS intake, small-model tool calling, real
road topology, evidence provenance, and deterministic reachability in one
operational workflow.

## The demo

This is a **simulated disaster exercise on real Swannanoa, NC roads**. A physical
Raspberry Pi Beacon captures a bridge-collapse voice report. Local faster-whisper
`tiny.en` transcribes it; Nemotron parses the report and uses tools to locate the
bridge, inspect status/evidence, record the closure, recompute reachability, and
submit an assessment. Blocking the eastern Warren Wilson Road bridge cuts off
five of nine simulated SOS incidents. The dashboard shows the affected incidents
and the tool trace. A subsequent unverified “bridge open” report leaves the
closure in place.

Incidents, disaster messages, and rescue units are simulated and labeled. The OSM
road graph, inference, tool execution, closure state, and routing computation are
real. The physical audio path was exercised; the controlled latency benchmark
below used text ingress and excludes ASR, microphone, and radio transport.

## Engineering and safety

- FastAPI model service and application API; NetworkX reachability on the OSM
  graph; Next.js/MapLibre command dashboard; Beacon audio/sensor intake and a
  field app with an offline outbox.
- Trust lives in code: one credible impassable report is enough to avoid a road;
  a single unverified open report cannot reopen it. Segment states preserve
  source type, time, and text. Ambiguous location requires human review.
- Tool arguments are validated, tool errors are surfaced, and model-facing route
  results are bounded while full geometry remains available to the map.
- Explicit `DEMO_MODE` uses labeled cached parse/agent fixtures while executing
  graph tools locally. The measured live setup uses remote NVIDIA H100 inference
  on Brev. Offline demo replay works locally; a fully offline laptop deployment
  of this full BF16 live model was not benchmarked.

## Models and platform use

| Component | Model | Parameters counted |
|---|---|---:|
| Parse and tool-calling agent | NVIDIA Nemotron 3.5 Lightning BF16; all experts and MTP | 32,913,263,168 |
| Flooded-road imagery | Fine-tuned SegFormer-B0, served native v2 | 3,714,658 |
| Local speech recognition | faster-whisper tiny.en, including frozen positions | 37,760,256 |
| **Total** | | **32,954,738,082** |

The total is **45,261,918 below 33,000,000,000**. Shared use of Nemotron is counted
once. Parakeet is **not used**: substituting it would exceed the cap. Exact tensor
accounting and the local ASR checkpoint hash are in [PARAM_BUDGET.md](PARAM_BUDGET.md).

NVIDIA use is concrete: Nemotron inference on a Brev H100, plus the genuine pinned
NeMo Gym resource server and verifier for tool-use evaluation. Serving uses the
official upstream `vllm/vllm-openai:v0.27.1` image (open-source vLLM) on one H100, with the
native tool-call parser, the Nemotron reasoning parser, prefix caching, async scheduling and
up to 32 concurrent sequences. vLLM is the serving layer for every Nemotron call in the system.

## Measured results

### Fresh live tool-calling exam 1 — prompt/tool policy

The 42-case `test_fresh` split and three policy files were committed before any
live model run (seal commit `5b80c79`). Each policy ran three times in rotated
order: **378 scenario attempts, 2,182 model calls, zero provider errors**. All nine
runs completed at 04:49:20 EDT on Oct 18, before the 06:30 EDT cutoff. Sampling was
temperature 1.0, max_tokens 1,024, no parallel calls, 12 turns, 60-second request
timeout; the optional argument adapter was off. No selective retries or policy
edits occurred after sealing. Existing train/validation/test bytes were unchanged.

| Policy | Complete runs | Passes /42 | Mean /42 | Range /42 | Provider errors |
|---|---:|---|---:|---|---:|
| baseline | 3/3 | 16, 12, 17 | 15.00 | 12–17 | 0 |
| system_prompt_only | 3/3 | 30, 29, 30 | 29.67 | 29–30 | 0 |
| grounded_v2 | 3/3 | 30, 30, 30 | 30.00 | 30–30 | 0 |

Per-family counts are passes / evaluated attempts across three runs (planned18 each):

| Family | Baseline | System prompt only | grounded_v2 |
|---|---|---|---|
| alternate_route | 14/18 (4, 5, 5) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| bridge_closed | 11/18 (5, 2, 4) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| conflicting_evidence | 5/18 (1, 1, 3) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| isolated | 3/18 (1, 1, 1) | 18/18 (6, 6, 6) | 18/18 (6, 6, 6) |
| missing_location | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| tool_failure | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) | 0/18 (0, 0, 0) |
| two_roads_closed | 12/18 (5, 3, 4) | 17/18 (6, 5, 6) | 18/18 (6, 6, 6) |

Baseline averaged **35.7%**, system-prompt-only **70.6%**, and grounded_v2 **71.4%**.
The clearer prompt explains nearly all the observed gain; adding tool-description
changes yielded only one additional pass across 126 attempts versus prompt-only.
With the adapter off in this first exam, missing-location and tool-failure cases
failed in every repetition; these results do not establish reliable recovery. This
is prompt/tool-policy improvement, not a Nemotron weight update or RL.

The split uses larger synthetic graphs (13–18 nodes) in the same seven families,
not a new real-world task distribution. Two size-17 error-handling topologies had
appeared in earlier fake-provider regression tests, though they had no prior live
model exam. The original test split had already been used in earlier experiments.
[Raw results and summary](../ml/nemo_gym/evidence/test_fresh_2026-10-18/summary.md)
and [integrity receipt](../ml/nemo_gym/evidence/test_fresh_2026-10-18/integrity_check.json)
record the sealed provenance and complete outcomes.


### Fresh live tool-calling exam 2 — compatibility repair, not RL

The second sealed split, `test_fresh2`, contains **42 synthetic cases**: all seven
families at node counts **19–24**. Commit `b4b4cc6` sealed the data, hash, three arms
and zero-model-call opening marker before evaluation. All four earlier split hashes
remain unchanged. The `grounded_v2` arms use identical policy bytes; only the third
enables the existing audited **nullable-null-v1** argument adapter, with no edits
to the adapter or verifier. Sampling and serving settings match the first fresh exam.

Three repetitions per arm ran in rotated order. The authorized live relaunch
completed all **378 scenario attempts** at **08:18:41 AM ET on October 18**, using
**2,227 recorded model calls**. One baseline `RemoteProtocolError` remains counted
in its 42-case denominator and was not retried; neither grounded arm had provider errors.

| Arm | Passes /42 | Mean /42 | Range /42 |
|---|---|---:|---|
| baseline | 15, 11, 13 | 13.00 | 11–15 |
| grounded_v2 | 30, 30, 30 | 30.00 | 30–30 |
| grounded_v2 + nullable-null-v1 | 41, 40, 42 | 41.00 | 40–42 |

The adapter improved the mean from **30/42 to 41/42** (71.4% → 97.6%, **+26.19
percentage points**). It made **36 compatibility repairs across 36 tool calls and
36 repeated scenario attempts**: converting `graph_version: "None"` to JSON null.
It does not invent locations, fill missing fields or change rescue decisions.
This is **compatibility repair, not RL**. Nemotron’s weights and the grounded policy
were unchanged.

Across the three repetitions, missing-location passes increased from **0/18 to
18/18**, and tool-failure passes from **0/18 to 15/18**. Both grounded arms passed
**18/18** in each of the other five families. **Three reasoning failures remain
across 126 adapter attempts**: the model submitted `needs_location` for incidents
whose location was known but road status was unavailable; the correct status was
`unknown`. The adapter repaired the encoding while preserving those wrong decisions.

The initial launch hit a missing model tunnel. A shell launch error allowed all
378 attempts to record connection failures, with zero requests reaching the model.
Those records are retained separately. The user explicitly authorized one complete
relaunch with failures retained; commit `68f5b1a` records that exception before live
generation. No selective retry, policy change or tuning occurred within the relaunch.
These larger graphs use the same deterministic families; repetitions reuse 42 cases,
not 378 independent emergencies. The split is now spent, and this result does not
establish real-world accuracy or general reasoning recovery.

[Complete results and per-family counts](GYM_RESULTS.md#fresh-exam-2--argument-repair-isolation-october-18-2026),
[raw summary](../ml/nemo_gym/evidence/test_fresh2_relaunch_2026-10-18/summary.md),
[repair ledger](../ml/nemo_gym/evidence/test_fresh2_relaunch_2026-10-18/adapter_repairs.json)
and [integrity receipt](../ml/nemo_gym/evidence/test_fresh2_relaunch_2026-10-18/integrity_check.json)
retain the sealed provenance, every run and all repairs. Offline official-verifier
rescoring passed, as did all **54 Gym tests**. The scoring command appears first in
GYM_RESULTS.md's Reproduce section.


### Operational repeatability

Twenty bridge-collapse text reports from fresh seeds all closed the exact two
direction IDs of the eastern bridge and cut off exactly SOS-001 through SOS-005:
**20/20**. Ten ambiguous responder reports all ended with human review and no
closure: **10/10 guarded outcomes**. The model itself abstained from attempting an
ambiguous mutation in only **1/10** runs; code rejected the other nine attempts.
This is evidence that the safeguard works, not perfect model disambiguation.
Narrative faithfulness was not scored.

Beacon text-radio request latency: median **7.912 s**, p95 **9.782 s**. Whole-agent
workflow: median **6.922 s**, p95 **8.431 s**; model calls: median **0.628 s**, p95
**1.633 s**. These include live remote inference; they exclude fresh seeding, ASR,
microphone, physical transport, browser rendering and WebSocket delivery. Inputs
repeat with prefix caching enabled. See [VLLM_RESULTS.md](VLLM_RESULTS.md).

### Vision and fine-tuning

The served SegFormer-B0 was fine-tuned for flooded-road segmentation. On a sealed 38-tile
test it scores F1 0.31; a retrained V3 scored 0.27 and was not promoted
([V3_RESULTS.md](ml/V3_RESULTS.md)). That is why SOSora treats imagery as a clue, never proof.
It is not a Helene accuracy measurement or a safety guarantee.

No Nemotron weight update or RL improvement is claimed. The optional LoRA attempt
stopped during infrastructure setup, with zero training steps and no adapter;
see [LoRA feasibility results](LORA_F_RESULTS.md). Prompt/tool-policy experiments
are reported separately from vision fine-tuning.

## Limits and evidence

This prototype supports review of candidate road access; graph connectivity is
not a road-safety clearance. The fresh exam uses synthetic task families;
operational repeats use one bridge scenario, not varied field conditions.
Infrastructure friction and suggested improvements are recorded in
[friction-log.txt](../friction-log.txt), including the disk allocation mismatch,
volatile RAM model cache, LoRA SSH/image-pull failures, BUILDING stop failure, and
vLLM tool-calling/context setup.

Code verification for this submission update: **39 backend tests passed**, plus
two focused mocked-request checks for the ASR default and override. The parameter
audit verified all 12 conversion-added zero key-bias slices and exact arithmetic.
The fresh exam's own integrity and test results are linked with its report.
