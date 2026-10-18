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
official upstream `vllm/vllm-openai:v0.27.1` image. The OpenAI-compatible adapter is
named `redhat_vllm`; **a Red Hat-distributed image, OpenShift deployment, and Red Hat
bounty eligibility are not established by this deployment**. We claim measured
vLLM integration, not verified Red Hat distribution use.

## Measured results

### Fresh live tool-calling exam

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
Missing-location and tool-failure cases still fail in every repetition; these
results do not establish reliable recovery. This is prompt/tool-policy improvement,
not a Nemotron weight update or RL.

The split uses larger synthetic graphs (13–18 nodes) in the same seven families,
not a new real-world task distribution. Two size-17 error-handling topologies had
appeared in earlier fake-provider regression tests, though they had no prior live
model exam. The original test split had already been used in earlier experiments.
[Raw results and summary](../ml/nemo_gym/evidence/test_fresh_2026-10-18/summary.md)
and [integrity receipt](../ml/nemo_gym/evidence/test_fresh_2026-10-18/integrity_check.json)
record the sealed provenance and complete outcomes.


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

The served SegFormer-B0 was fine-tuned for flooded-road segmentation. A frozen
cross-event check on six unseen Germany flood tiles improved F1 from **0.23 to
0.47** against the same model before fine-tuning. This small external check is not
Helene accuracy or a safety guarantee. The experimental V3 is not served.
See [frozen external evaluation](ml/FROZEN_EXTERNAL_EVALUATION.md).

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
