# SOSora video script v3 (Jia + Ria's script, edited). Target 4:45, hard max 5:00.

TIMING: read it aloud with a timer before filming. If it runs past 4:50, cut the lines marked [CUT IF LONG] first,
then Scene 3 (the app). A late or over-length video is rejected.
RULES: keep [SIMULATED] labels visible. Never show phone signal bars while saying there's no signal.
Footage: use public-domain Helene photos/video only (NCDOT, FEMA, National Guard/DVIDS, NOAA aerials), not TV news clips.
[FINAL] numbers come from docs/GYM_RESULTS.md, docs/VLLM_RESULTS.md, docs/PARAM_BUDGET.md.

## SCENE 1 — THE PROBLEM (0:00–0:45) | Jia + Ria
[Public-domain Helene footage: washed-out roads, collapsed bridges, flooded neighborhoods. Then both of you on camera.]
JIA: September 2024. Hurricane Helene tears through western North Carolina. Roads wash away. Bridges collapse.
Now imagine you're trapped in your home. The water's rising. You call 911, and nothing goes through.
And even if rescuers know where you are, the only road to your house might be gone.
[Stats on screen, one at a time.]
RIA: At one point, about 74% of cell sites in the 21-county disaster area were down. By November, the state had logged more than 8,100 damaged roads, bridges and culverts.
And North Carolina's own after-action review said local teams need to be able to operate for up to 72 hours with no communications at all.
[Both on camera.]
JIA: We're Jia and Ria, two sisters from North Carolina. Watching this happen in our own state, we noticed two networks fail at the same time: the one that tells rescuers who needs help... and the roads that decide how to reach them.
RIA: So we built something that keeps both alive.

## SCENE 2 — INTRODUCING SOSORA (0:45–1:10) | Ria
[Logo → system diagram → Pi on the table → phone → GPU terminal.]
RIA: This is SOSora. It keeps the rescue map alive when the towers and the roads go down.
It has three parts. A field beacon: a Raspberry Pi with a microphone and a water sensor, sitting by a bridge. A resident app that holds your SOS until it finds a connection. And one GPU box that rides in the county's command truck and runs everything with no internet.
The brain is one small model: NVIDIA Nemotron 3.5 Lightning. Let us show you.

## SCENE 3 — THE MOBILE APP (1:10–1:40) | Jia  [ONLY if it works on the real phone this morning; otherwise cut]
[Phone on camera, dashboard visible behind. Show the airplane-mode icon, never signal bars.]
JIA: Let's start with someone who needs help. This is our native iOS app.
[Tap Request Help.] You send an SOS: where you are, what's happening, how many people.
But in a disaster, you can't count on a connection. [Airplane mode on, request shows queued.] So SOSora saves it on the phone, and the second a link comes back... [reconnect; cut to the pin dropping on the dashboard] there it is at command.
[CUT IF LONG] [Tap Report Roads.] Residents and responders can also report a damaged road, right on the map.

## SCENE 4 — THE HERO DEMO (1:40–3:00) | Jia + Ria
[Dashboard, presentation mode (P), fresh Seed (S).]
JIA: This is Swannanoa, North Carolina, one of the communities Helene hit hardest. These are real roads from OpenStreetMap, with nine simulated residents asking for help. Those teal lines are live rescue routes. Right now, everyone's reachable.
[Ria presses the button on the Pi.]
RIA (into the mic, radio voice): "Command, Engine 4. The bridge on Warren Wilson Road is gone. Three families on the far side."
[CUT IF LONG] JIA: Imagine you're the dispatcher getting that call while ten others come in. Which bridge? Which roads? Who can you still reach?
[Agent trace streaming.]
RIA: Here's where SOSora comes in. The voice is transcribed locally. Then Nemotron decides which tools to call, one at a time: find the road, check its status, look for aerial imagery. There isn't any, so it says it's not sure instead of making something up. Then it logs the report and recomputes who can still be reached.
[Bridge goes red, routes break, counter hits 05.]
JIA: Watch. Five of nine families, cut off. One sentence on a radio, and the whole map updates.
[Fresh Seed → Responder radio (R) → bridges A and B pulse.]
RIA: But real radio is messy. Here's the same report with no location... and there are two bridges on Warren Wilson Road.
JIA: So it doesn't guess. It asks us. [Click Confirm bridge A.]
RIA: And here's the wild part. We ran this thirty times, and the model tried to close a bridge anyway nine out of ten times. Our safety rule, written in code, caught every single one.
[DOT says open (D): the bridge stays red.]
JIA: Same here. Someone radios that the bridge is open. It stays red. Closing a road takes one credible report. Reopening one takes verification, because a wrong "open" sends a crew into a river.

## SCENE 5 — THE BEACON (3:00–3:20) | Ria
[Handheld on the table, dashboard visible behind.]
RIA: The beacon doesn't even need a person. [Pour water.] Water rises past the line... [bridge goes red] and it reports itself.
And if the link dies... [pull the router plug; Pi shows QUEUED] it waits. Plug it back in... [SENT] sent. Exactly once.

## SCENE 6 — THE ENGINEERING (3:20–4:20) | Ria + Jia
[Architecture diagram, then real tool calls, terminal, evidence files. Each number pops up on screen.]
RIA: Here's what makes this more than a dashboard. We're not asking an AI to invent rescue routes. Nemotron figures out what a report means and calls tools. Real graph algorithms decide who's reachable. And the safety rules live in code.
[Imagery offline (I): the error appears in the trace.] When a tool breaks, like when we knock out the imagery service here, the agent says so and still lands on a safe answer.
JIA: And we measured everything. Nemotron Lightning is our only language model. We counted every parameter: [FINAL 32.96] billion, under the 33 billion limit.
We serve it with Red Hat's vLLM on a single H100. On the hosted API, one agent step took 24 to 55 seconds. On vLLM, under one second. Across thirty live runs, it found the right bridge twenty out of twenty times.
RIA: We used NVIDIA NeMo Gym to build a graded test of rescue scenarios: ambiguous locations, conflicting evidence, broken tools. On [FINAL 42] brand-new scenarios, our agent went from [FINAL 38] to [FINAL 71] percent, and we tested each change separately to see what actually helped.
JIA: We also fine-tuned an NVIDIA SegFormer model to spot flooded roads from aerial imagery. Honestly? Our tests say it isn't reliable yet. So SOSora treats it as a clue, never as the truth.
[CUT IF LONG] RIA: Because emergency decisions need more than a convincing answer. They need a defensible one.

## SCENE 7 — THE IMPACT (4:20–4:45) | Jia + Ria
[Map with the blocked bridge and five cut-off pins, then both of you on camera.]
JIA: Think about what just happened. One report about one bridge, and SOSora found the real location, updated the road network, and showed exactly which families could no longer be reached.
RIA: It's built for county emergency managers and the command trucks they already roll out. One box. No internet. Seventy-two hours.
JIA: We can't stop the next hurricane. But when the towers go down and the roads wash away...
RIA: ...the rescue map shouldn't disappear with them.
BOTH: We're SOSora. Keeping the rescue map alive.
END CARD: github.com/peanutz28/sosora · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym
