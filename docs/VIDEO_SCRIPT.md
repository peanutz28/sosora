# SOSora demo video script (target 4:00, hard max 5:00)

Rules: keep [SIMULATED] labels visible. Never show phone signal bars while saying "no signal".
Every number on screen must match docs/ (fill the [FINAL] slots from GYM_RESULTS.md / VLLM_RESULTS.md / PARAM_BUDGET.md).
Film each beat as a separate 1920x1080 take, starting from a fresh Seed drill (S). Record voiceover separately. Captions on.
Keys: S seed, B beacon hero, R responder radio, A confirm bridge A, D DOT says open, W water spike, I imagery offline, P presentation mode.

## 0:00-0:15 Cold open (no music for first 3 s)
VISUAL: dark room. Pi + USB mic + water gauge on a table. A hand presses the button.
SISTER (radio voice, into the Pi mic): "Command, Engine 4. The bridge on Warren Wilson Road is gone. Three families on the far side."
VISUAL: dashboard. Camera flies to the bridge, it snaps red, routes break, red zone spreads, "Families cut off" counts to 05.
TEXT: "Swannanoa, NC. Simulated drill on real roads."  Title card: SOSora.

## 0:15-0:45 The problem (sister on camera, or VO over the Helene Track map layer)
"September 2024. Hurricane Helene. In western North Carolina, about 74% of cell sites in the disaster area went down.
NCDOT logged more than 8,100 damaged roads, bridges and culverts.
Rescuers lost two things at once: who needed help, and how to reach them.
The state's own after-action review says local teams must be able to operate for up to 72 hours without communications."
TEXT (small): FCC, Sep 28 2024 · NCDOT, Nov 2024 · NC Helene After-Action Review, 2025

## 0:45-1:05 The solution (system diagram)
"SOSora keeps the rescue map alive when the towers and the roads go down.
A Beacon at the river. One GPU box in the mobile command vehicle. A resident SOS app. No internet required.
And one small model runs the brain: NVIDIA Nemotron 3.5 Lightning."

## 1:05-2:20 Live demo (screen recording, Kam narrates, P mode on)
1. Seed (S): "Nine simulated SOS calls on the real Swannanoa road network. Teal lines are live rescue routes. Everyone is reachable."
2. Beacon (B), slow on the trace: "The voice is transcribed locally. Nemotron parses it, then decides which tools to call:
   find the road, check its status, check aerial imagery. There is none, so it keeps the uncertainty.
   Record the report. Recompute who can be reached." Beat. "One bridge. Five families cut off.
   Each model step takes under a second on vLLM."
3. Seed, Responder radio (R): "Same report from a radio with no location. There are two bridges on Warren Wilson Road.
   SOSora doesn't guess. It asks." Click A. "In thirty live tests, Nemotron tried to close a bridge anyway
   nine times out of ten. Our trust rule, written in code, caught it every time."
4. DOT says open (D): bridge stays red. "One report can close a road. Reopening takes verification,
   because a wrong 'open' sends a crew into a river."
5. Imagery offline (I): "When a tool breaks, the agent says so and still lands on a safe answer."

## 2:20-2:50 Physical beats (handheld camera on the table, dashboard visible behind)
- Pour water into the container: sensor trips, bridge goes red. "The Beacon doesn't need a person to speak."
- Unplug the Wi-Fi / pull the router plug: Pi shows QUEUED. Plug back in: SENT, exactly once.
  "When the link drops, reports wait. When it returns, they arrive once."

## 2:50-3:10 Resident app (ONLY if verified on the physical phone this morning; otherwise cut)
Airplane mode on (show the airplane icon, not signal bars). File an SOS: "queued". Reconnect: pin drops on the dashboard.

## 3:10-3:45 Under the hood (one slide, four numbers, Kam)
- "Nemotron 3.5 Lightning is our only language model. Counting every expert, everything we load is [FINAL 32.9x]B of the 33B budget."
- "Served on Red Hat vLLM on one H100: an agent step went from 24 to 55 seconds on the hosted API to 0.85 seconds.
   Thirty live runs: 20 of 20 found the right bridge and the right five families; 10 of 10 ambiguous reports held safely for a human."
- "With NeMo Gym we built a graded rescue environment. On [FINAL 42] fresh scenarios it had never seen,
   the agent went from [FINAL 38]% to [FINAL 71]%, and an ablation shows the system prompt drove the gain. No retraining."
- "We also fine-tuned NVIDIA SegFormer to spot flooded roads from the air. Our sealed evaluation says it isn't reliable yet,
   so SOSora treats imagery as evidence, never as truth."

## 3:45-4:05 Close (both on camera)
"Built for county emergency managers and the mobile command vehicles they already roll out.
One box. No internet. Seventy-two hours.
SOSora: the rescue map that keeps working when the towers and the roads don't."
End card: github.com/peanutz28/sosora · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym
