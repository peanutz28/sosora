# SOSora video script v9 — from a bridge report to a rescue decision

Target: roughly 4:30, including demo pauses; hard maximum 5:00. Keep the official five-part structure. Jia and Ria speak to a county emergency manager, with enough visible engineering for the judges to inspect.

[Brackets] are screen directions, never spoken. Keep [SIMULATED] labels visible. Record the live demo as one continuous take. Let the map change before explaining the result; hold the five cut-off requests on screen.

## 1. INTRODUCE YOUR TEAM (0:00–0:20)

[Both on camera. Brief Helene footage, then the dashboard.]

JIA: Hi, I'm Jia.

RIA: And I'm Ria. We're sisters from North Carolina, and we built SOSora.

JIA: After Helene, rescuers faced damaged roads and disrupted communications. When a crew radios in, “The bridge is gone,” the dispatcher needs to know something immediately: whose rescue route just disappeared?

## 2. ELEVATOR PITCH (0:20–0:50)

[One radio report → one bridge turns red → five SOS requests lose their routes. Show this relationship before the architecture diagram.]

RIA: SOSora connects field reports to the people depending on those roads. When a crossing fails, it shows which SOS requests have just lost road access, so the dispatcher can reassess how to reach them.

JIA: Crew radio, residents' SOS messages, and our bridge sensor feed one operational map. The model interprets the report and calls tools. Road-network code calculates who is still reachable. The dispatcher makes the response decision.

## 3. LIVE DEMO (0:50–2:20)

[Fresh seed. Nine SIMULATED SOS requests, all reachable. Pi and microphone visible in a corner.]

RIA: Here's a drill on real Swannanoa roads. Nine SOS requests. Right now, all nine have a road route from our rescue base.

JIA: Listen to this report.

[Pi voice report: “Command, the bridge on Warren Wilson Road is gone.” Use the real recorded-audio path only when it is ready. Wait for the live assessment.]

RIA: Watch the trace. Nemotron locates the crossing, checks its status and available evidence, records the closure, and asks the routing tools to calculate its effect.

[Hold the red bridge, broken routes and final counters: 05 cut off, 04 reachable, 01 physical crossing blocked.]

JIA: Five SOS requests just lost road access. Four still have a route. The dispatcher can see exactly which requests need another way in, and the report behind that change.

[Fresh seed → responder report without coordinates → two real bridge candidates. Keep the map unchanged until confirmation.]

RIA: Now the same report comes from a crew without a location. Two bridges match. Our code blocks an unresolved closure and asks the operator to choose.

[Confirm the eastern Warren Wilson crossing. Wait for the result.]

JIA: I confirm this crossing. Only then does the map change.

[Unverified DOT open report. Hold the existing closure.]

RIA: And if another radio report says “it's open,” that claim needs verification. The closure stays. Every road change keeps its source and history for review.

## 4. HOW WE BUILT IT (2:20–4:05)

[TOOL-CALLING TRACK · show one tool request beside its graph result.]

JIA: This is why we chose the tool-calling track. Nemotron connects messy field language to tools that inspect evidence, update road status and recompute access. The tools validate each change and return errors to the agent.

[NVIDIA NEMOTRON LIGHTNING · one model serving parser and agent; system total 32.95B parameters, counting all experts.]

RIA: One Nemotron 3.5 Lightning model handles both radio parsing and the agent. With our speech and flood-imagery models included, the system stays below the 33-billion-parameter cap.

[vLLM · NVIDIA BREV · one H100; native tool parser and prefix caching. Chart: 100 radio-parsing requests, ~21 seconds concurrent versus ~85 seconds sequential.]

JIA: Reports arrive in bursts. We serve Lightning through vLLM on one Brev H100. In our load test, it cleared 100 radio-parsing requests in about 21 seconds, versus 85 one at a time.

[Small architecture diagram: Beacon + phone outbox → Command. Distinguish the current Brev GPU from the proposed local command-post deployment.]

RIA: The Beacon queues reports when its connection drops. The phone has an SOS outbox, and speech is transcribed locally. Command is designed for a GPU-equipped command post; today's live model is running on Brev.

[NVIDIA NeMo GYM · frozen fresh2 arms: 30/42 → 41/42 mean; 36 repairs; 3 reasoning failures /126 adapter attempts. Lower-third: COMPATIBILITY REPAIR · NOT RL.]

JIA: We also tested failure recovery. On a sealed exam of 42 synthetic cases, the frozen grounded policy averaged 30 out of 42. Enabling our audited argument adapter raised that to 41 out of 42 across three runs.

RIA: It made 36 compatibility repairs, converting the string “None” to JSON null. Three reasoning failures remained. That's compatibility repair, not RL. The policy and model weights stayed unchanged.

## 5. SO WHAT? (4:05–4:30)

[Return to the same five cut-off SOS requests, then both on camera.]

JIA: One failed crossing can change the rescue plan for an entire neighborhood. SOSora makes that impact visible as reports come in.

RIA: For a dispatcher, that means seeing what changed, who it affects, and what still needs checking before the next response decision.

BOTH: We're SOSora.

[End card: github.com/peanutz28/sosora · Tool-Calling track · NVIDIA Nemotron 3.5 Lightning · vLLM · NVIDIA NeMo Gym.]

---

## Recording and evidence notes — not spoken

- **Pacing:** Rehearse with the actual assessment waits. If over five minutes, shorten the implementation section; keep the before/after map, ambiguity confirmation and closing. Do not speed through the five cut-off requests.
- **Demo readiness:** Follow [FILMING_RUNBOOK.md](FILMING_RUNBOOK.md). A cached replay must be labeled as replay. If using text instead of audio, replace the Pi direction with visible text submission and say “Here's the report.” Do not present that take as voice-to-map. Nine requests are not nine people; graph reachability is not a road-safety clearance. The demo proposes no automatic dispatch.
- **Trust:** The ambiguity outcome depends on code guards and operator confirmation. In ten measured ambiguous reports, the model attempted an unresolved mutation nine times; code blocked all nine. Do not say the model never guesses. Operational repeatability was 20/20 exact Beacon bridge-and-five-incident outcomes and 10/10 guarded ambiguity outcomes in the same exercise, not varied field validation. See [VLLM_RESULTS.md](VLLM_RESULTS.md).
- **Serving/load test:** The 100-request result measures radio parsing (~20.6 seconds concurrent versus ~84.8 seconds sequential), not 100 completed rescue assessments or voice-to-map latency. We used the upstream vLLM image; a Red Hat-distributed image and Red Hat bounty eligibility are unverified. See [SUBMISSION.md](SUBMISSION.md) and [VLLM_RESULTS.md](VLLM_RESULTS.md).
- **Connectivity:** Store-and-forward intake, local ASR and the local-command-post design are distinct from the measured live Brev deployment. Do not describe today's full live BF16 system as a verified offline laptop or deployed command truck. The phone outbox belongs in the architecture shot; add a live phone-sync demonstration only after verifying it for the recording.
- **Fresh2:** 42 cases, seven synthetic families, 19–24 nodes; three repetitions per arm with unchanged sampling. Grounded scores: 30, 30, 30 /42; adapter scores: 41, 40, 42 /42. All 36 repairs changed `graph_version: "None"` to JSON null. Three tool-failure attempts still chose `needs_location` instead of `unknown`; these are three failures across 126 adapter attempts, not three per run. The initial connection-failed launch and authorized complete relaunch are retained. One unretried baseline provider error remains counted. See [GYM_RESULTS.md](GYM_RESULTS.md) and its raw evidence links.
- **Model budget:** The 32.95B total includes every Nemotron expert and MTP, served SegFormer and local tiny.en speech model. See [PARAM_BUDGET.md](PARAM_BUDGET.md).
