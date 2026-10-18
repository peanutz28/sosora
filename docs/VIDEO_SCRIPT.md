# SOSora video script v4: hook, WIIFM, every feature, why we win each prize. Target 4:45 (fast talkers), hard max 5:00.

Read aloud with a timer once. If over 4:50: cut [CUT IF LONG] lines, then the APP scene.
Rules: [SIMULATED] labels visible; never show phone signal bars while saying "no signal"; public-domain Helene footage only
(NCDOT, FEMA, National Guard/DVIDS, NOAA). [FINAL] numbers from docs/GYM_RESULTS.md, docs/VLLM_RESULTS.md, docs/PARAM_BUDGET.md.
In the "why it wins" section, put the prize name on screen as a lower-third while you talk (TOOL CALLING, NEMOTRON LIGHTNING, RED HAT vLLM, NeMo GYM).

## HOOK (0:00–0:20)
[Dark room. Hand presses the Pi button. Cut: dashboard flies to the bridge, it goes red, counter hits 05.]
RIA (radio voice, into the mic): "Command, Engine 4. The bridge on Warren Wilson Road is gone. Three families on the far side."
JIA: One radio call. One bridge. Five families just fell off the rescue map.
RIA: During Hurricane Helene, that happened all over western North Carolina, with no cell service to tell anyone.
JIA: In the next four minutes, we'll show you how one small NVIDIA model, running on one box with no internet, catches that in seconds and keeps the map alive.

## THE PROBLEM (0:20–0:50)
[Public-domain Helene footage. Stats on screen one at a time.]
RIA: September 2024. About 74% of cell sites in North Carolina's 21-county disaster area went down. The state logged more than 8,100 damaged roads, bridges and culverts.
JIA: So rescuers lost two things at once: who needs help, and how to reach them. Reports came in over the radio and ended up on whiteboards. Or nowhere.
RIA: The state's own after-action review says local teams need to operate for up to 72 hours with no communications.
JIA: We're Jia and Ria, two sisters from North Carolina, and that's exactly what we built for.

## THE SOLUTION (0:50–1:15)
[Logo → system diagram → Pi → phone → GPU terminal.]
RIA: Meet SOSora. Three pieces, zero internet.
A field beacon: a Raspberry Pi with a mic and a water sensor that reports road conditions by voice, or all by itself.
A resident app that holds your SOS until it finds any connection.
And SOSora Command: one GPU box in the county's command truck, where NVIDIA Nemotron 3.5 Lightning turns every report into a live rescue map.
JIA: It's built for county emergency managers. What they get: who's cut off, and why, the moment a report lands.

## THE APP (1:15–1:40)  [ONLY if verified on the real phone; otherwise cut]
[Phone on camera, airplane-mode icon visible, dashboard behind.]
JIA: Start with a resident. Send an SOS: location, what's happening, how many people. No connection? It's saved on the phone. [Reconnect.] The moment a link comes back, it syncs... and the pin drops at command.
[CUT IF LONG] Residents and responders can report damaged roads too, right on the map, and those go straight to the agent.

## THE HERO DEMO (1:40–2:45)
[Dashboard, presentation mode P, fresh Seed S.]
JIA: This is Command. Swannanoa, North Carolina: real OpenStreetMap roads, nine simulated SOS calls. Teal lines are live rescue routes. Everyone's reachable.
[Pi button.] RIA (radio): "Command, Engine 4. The bridge on Warren Wilson Road is gone."
RIA: The voice is transcribed locally. Then Nemotron decides which tools to call, one at a time. Find the road. Check its status. Check aerial imagery: there isn't any, so it keeps the uncertainty instead of making something up. Log the report. Recompute who's reachable.
JIA: Bridge down. Five of nine families cut off. That red zone is who you can't reach by road anymore, and everyone else gets rerouted.
[Fresh Seed → Responder radio R → bridges A and B pulse.]
RIA: Now the hard case. Same report, no location, and there are two bridges on Warren Wilson Road.
JIA: It doesn't guess. It asks. [Click Confirm bridge A.]
RIA: And the wild part: in thirty live tests, the model tried to close a bridge anyway nine out of ten times. Our trust rule, written in code, caught every single one.
[DOT says open D: the bridge stays red.]
JIA: Someone radios that the bridge is open? It stays red. One credible report closes a road. Reopening one takes verification, because a wrong "open" sends a crew into a river.
[Imagery offline I: the error appears in the trace.]
RIA: And when a tool breaks, like the imagery service here, the agent says so and still lands on a safe answer.

## THE BEACON (2:45–3:05)
[Handheld on the table, dashboard behind.]
RIA: The beacon doesn't even need a person. [Pour water.] Water past the line... and it reports itself.
JIA: Link dies? [Pull the router plug: QUEUED.] Reports wait. [Plug back in: SENT.] Link's back, they're delivered.

## WHY IT WINS (3:05–4:25)  [prize name as lower-third for each paragraph; terminal, code, evidence files on screen]
[TOOL CALLING] RIA: For tool calling: six tools, one call at a time. The agent decides when to act, when to ask a human, and how to fall back when something breaks. And the safety rules live in code, not in a prompt.
[NEMOTRON LIGHTNING] JIA: Nemotron 3.5 Lightning is our only language model. It parses every radio call and runs the agent. We counted every parameter, every expert: [FINAL 32.96] billion, under the 33 billion cap, speech model included.
[RED HAT vLLM] RIA: We serve it with Red Hat's vLLM on a single H100. One agent step went from 24 to 55 seconds on the hosted API to under one second. Thirty live runs: the right bridge twenty out of twenty times, and ten out of ten ambiguous calls held safely for a human.
[NeMo GYM] JIA: With NeMo Gym, we built a graded rescue environment: ambiguous locations, conflicting evidence, broken tools. On [FINAL 42] brand-new scenarios, the agent went from [FINAL 38] to [FINAL 71] percent, and an ablation shows exactly which change did it.
[VISION] RIA: We even fine-tuned NVIDIA SegFormer to spot flooded roads from the air. Our sealed test says it's not reliable yet, so SOSora treats it as a clue, never as the truth. That's our whole philosophy.
[CUT IF LONG] JIA: It's all open source, and you can try the hosted demo yourself. Links below.  (only if hosting works)

## CLOSE (4:25–4:45)
[Map with the blocked bridge and five cut-off pins, then both of you on camera.]
JIA: One report about one bridge, and SOSora found the real location, updated the road network, and showed exactly who can't be reached.
RIA: One box. No internet. Seventy-two hours.
JIA: We can't stop the next hurricane. But when the towers go down and the roads wash away...
RIA: ...the rescue map shouldn't disappear with them.
BOTH: We're SOSora.
END CARD: github.com/peanutz28/sosora · hosted demo link · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym
