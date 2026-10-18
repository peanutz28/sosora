# SOSora video script v2: conversational voiceover over clips (~4:15)

Format: VISUAL = the clip on screen. VO = who talks over it. Talk like you're explaining it to a friend.
Rules: [SIMULATED] labels stay visible. Never show phone signal bars while saying "no signal".
[FINAL] numbers get filled from docs/GYM_RESULTS.md, docs/VLLM_RESULTS.md, docs/PARAM_BUDGET.md.

## Shot list (film these as B-roll, any order)
- Pi close-ups: board, USB mic, water gauge, button press, Pi terminal showing QUEUED then SENT
- Hands pouring water into the container; hand pulling the Wi-Fi/router plug and plugging it back in
- Dashboard takes (fresh Seed each, P mode): seed, beacon hero, responder + confirm A, DOT open, imagery offline (I)
- Terminal: vLLM server log / nvidia-smi on the H100, a Gym run finishing, test output passing
- Code scroll: the trust rule in backend/app/radio_api.py, the tool list in backend/app/agent.py
- Map with the Helene Track layer on
- Both of you at the laptop; both of you on camera for the close
- (optional) phone in airplane mode filing an SOS, pin dropping on the dashboard

## Script

[0:00] VISUAL: black, then the Pi on the table. A hand presses the button.
JIA (radio voice, into the mic): "Command, Engine 4. The bridge on Warren Wilson Road is gone. Three families on the far side."
VISUAL: dashboard flies to the bridge, it goes red, counter hits 05.
KAM: "That report's simulated. But these roads are real. And two years ago, this exact valley flooded."

[0:15] VISUAL: Helene Track layer over the map; stats appear as text.
JIA: "When Hurricane Helene hit western North Carolina, about three out of every four cell sites in the disaster area went down. More than eight thousand roads, bridges and culverts were damaged."
KAM: "So rescuers lost two things at the same time. Who needs help... and how to actually get to them."
JIA: "A road report would come in over the radio and end up on a whiteboard. Or nowhere."

[0:35] VISUAL: the two of you at the laptop.
KAM: "We're Kam and Jia, and we built SOSora. It keeps the rescue map alive when the towers and the roads go down."

[0:45] VISUAL: Pi close-up, then phone, then the H100 terminal.
JIA: "There are three pieces. A little beacon by the river: a Raspberry Pi, a mic and a water sensor. An app that holds onto your SOS until it finds a connection. And one GPU box that rides in the command truck. No internet needed."
KAM: "And the brain is one small model: NVIDIA's Nemotron 3.5 Lightning."

[1:05] VISUAL: dashboard, Seed.
KAM: "OK, let's run it. Nine simulated SOS calls on real Swannanoa roads. Those teal lines are live rescue routes. Right now, everyone's reachable."

[1:15] VISUAL: button press, then the agent trace streaming.
JIA: "Now the beacon hears that bridge report."
KAM: "Watch the right side. That's Nemotron deciding what to do, one tool at a time. Find the road. Check its status. Look for aerial imagery. There isn't any, so it says it's not sure instead of making something up. Log the report. Then figure out who can still be reached."
JIA: "Five families, cut off. From one sentence on a radio."
KAM: "And every one of those model steps takes under a second, because we serve it with vLLM."

[1:45] VISUAL: responder radio, A/B bridge pins pulsing.
JIA: "But real radio is messy. Here's the same report with no location... and there are two bridges on Warren Wilson Road."
KAM: "So it doesn't guess. It asks us."
JIA: "Here's the wild part. We ran this thirty times, and the model tried to close a bridge anyway nine out of ten times."
KAM: "Which is exactly why the safety rule lives in our code, not in the model. It caught every single one."

[2:10] VISUAL: DOT says open, the bridge stays red. (Cut to the trust rule in code for 2 s.)
JIA: "Same idea here. Someone radios that the bridge is open. It stays red."
KAM: "One credible report can close a road. Reopening one takes verification. Because a wrong 'open' sends a crew into a river."

[2:25] VISUAL: Imagery offline (I), the error shows in the trace.
KAM: "And when a tool breaks, like here where we knock out the imagery service, it just says so, and still lands on a safe answer."

[2:35] VISUAL: hands pour water; bridge goes red. Hand pulls the router plug; Pi shows QUEUED; plug back; SENT.
JIA: "The beacon doesn't even need a person. Water rises past the line... and it reports itself."
KAM: "And if the link dies, it waits. Plug it back in... sent. Exactly once."

[2:55] VISUAL (optional, only if verified on the real phone): airplane mode, SOS queued, reconnect, pin drops.
JIA: "Same on the resident app. Airplane mode, file an SOS, it waits... and the second it reconnects, there's the pin."

[3:10] VISUAL: terminal, Gym output, evidence files; each number pops up on screen.
KAM: "Quick look under the hood, because we measured everything."
KAM: "Nemotron Lightning is our only language model. We counted every parameter: [FINAL 32.96] billion, out of the 33 allowed."
JIA: "On the hosted API, one agent step took 24 to 55 seconds. On vLLM on a single H100, under one second. And across thirty live runs, it found the right bridge twenty out of twenty times."
KAM: "We also built a NeMo Gym environment that grades the agent on rescue scenarios. On [FINAL 42] brand-new ones it had never seen, it went from [FINAL 38] to [FINAL 71] percent. And we tested each change on its own, so we know what actually helped."
JIA: "We even fine-tuned an NVIDIA vision model to spot flooded roads from the air. Honestly? Our tests say it's not reliable yet. So SOSora treats it as a clue, never as the truth."

[3:50] VISUAL: both of you on camera.
JIA: "We built this for county emergency managers, and the command trucks they already roll out."
KAM: "One box. No internet. Seventy-two hours."
JIA: "SOSora. The rescue map that keeps working when the towers and the roads don't."
END CARD: github.com/peanutz28/sosora · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym
