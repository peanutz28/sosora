# SOSora video script v8: follows the official 5-part demo structure (~4:15)
Record with camera on (Loom face bubble or similar). Keep the live demo as one take with minimal cuts.
[Brackets] = what's on screen. Lower-thirds name the track/prize. [SIMULATED] labels stay visible.

## 1. INTRODUCE YOUR TEAM (0:00–0:25)  [both on camera]
JIA: Hi, I'm Jia.
RIA: And I'm Ria. We're Team SOSora, two sisters from North Carolina.
JIA: In 2024, Hurricane Helene hit our state. About three out of four cell towers in the disaster area went down, and more than 8,100 roads, bridges and culverts were damaged.
RIA: So rescuers lost two things at once: they didn't know who needed help, and they didn't know which roads still worked. That's what we worked on this weekend.

## 2. ELEVATOR PITCH (0:25–1:05)  [Helene footage → diagram → Pi → phone → dashboard]
JIA: We built SOSora: a rescue map that keeps working when the cell towers and the roads go down.
RIA: It's one computer in the county's emergency command truck. No internet needed. Reports come in three ways that still work in a disaster: crews on the radio, a Raspberry Pi sensor box we built that sits by a bridge and watches the water, and an app that holds a resident's SOS until it finds any signal.
JIA: A small NVIDIA AI model reads every report, uses tools to update a map of real roads, and answers the question every dispatcher has: who can we still reach, and who's cut off?
RIA: Today, those radio reports end up on whiteboards. With SOSora, the map updates itself in seconds.

## 3. LIVE DEMO (1:05–2:05)  [one continuous screen recording; Pi press shown in a corner]
JIA: This is a drill on the real roads of Swannanoa, one of the towns Helene hit hardest. Nine people need help. The teal lines are the routes our rescue truck can take. Everyone's reachable.
RIA: Now a crew radios in. [Pi button] "The bridge on Warren Wilson Road is gone."
JIA: Watch the right side. The AI is choosing tools one at a time: it searches the map for that road, checks its status, checks aerial photos, marks the bridge closed, and recalculates every route.
RIA: Five of the nine are now cut off. The dispatcher sees it in seconds, and can send a boat instead of a truck.
[Fresh seed → responder radio] JIA: Now a harder one. This crew doesn't say where they are, and there are two bridges with that name. The AI doesn't guess. It asks the dispatcher. [Click bridge A]
[Phone mirrored next to dashboard] RIA: And a resident with no signal sends an SOS. It waits on the phone, and the second it connects, the pin drops on our map.

## 4. HOW WE BUILT IT (2:05–3:35)  [diagram, code, terminals, Gym page; lower-thirds per tech]
JIA: Here's how it works under the hood.
[TOOL-CALLING TRACK] RIA: We entered the tool-calling track: one small model that gets real work done by calling tools. Ours has six: find a road, check its status, check aerial photos, report a closure, recalculate who's reachable, and file its assessment. The real routing math runs in code, not in the AI.
[NEMOTRON LIGHTNING] JIA: The model is NVIDIA Nemotron 3.5 Lightning. The hardware drove that choice: a truck can't hold a data center, so we needed one model that fits on one GPU. Lightning only uses about 3 billion of its 32 billion parameters per word, so it's fast, and it's still smart enough to understand messy radio. It parses every radio call and runs the agent, and it's our only language model, so the whole system stays under the 33 billion parameter limit. We even chose a tiny speech model over a bigger one, because the bigger one would have pushed us over.
[RED HAT vLLM; nvidia-smi + vLLM logs] RIA: Our first bottleneck was speed. On the hosted API, each AI step took 24 to 55 seconds. We moved to serving it ourselves with Red Hat's vLLM on one H100, using its native tool-call parser and prefix caching. Now each step takes 0.85 seconds. And when we sent 100 reports at once, like a real storm, vLLM's batching cleared them in 21 seconds instead of 85.
[Safety: DOT open, imagery offline, trust rule in code] JIA: Our second challenge was trust. In 30 live tests, the model tried to close a bridge on its own 9 times out of 10 when the report was unclear. So the AI suggests, and our code decides: it blocks unclear changes, refuses to reopen a road without verification, and when a tool crashes, the agent says so and still gives a safe answer.
[NeMo GYM; red-to-green grid] RIA: To measure the AI, we used NVIDIA NeMo Gym: we built 42 practice disasters it had never seen, with a grader that scores every attempt. It started at 31 percent. Better instructions took it to 71. Then Gym showed us its last mistake: it kept typing the word "None" instead of leaving a field empty. We added a small repair step, and it hit 98 percent. One change at a time, so we know what helped.
[Pi: water pour, router unplug] JIA: And on the edge, voice reports are transcribed locally with no cloud, and the Pi sensor reports by itself when the water crosses a line, and saves reports when the connection drops.

## 5. SO WHAT? (3:35–4:00)  [both on camera]
RIA: During Helene, the information rescuers needed existed. It just never made it onto one map.
JIA: SOSora puts it there: one box in a truck, no internet, one small model doing real work, and a map that always knows who rescuers can still reach.
RIA: We can't stop the next hurricane. But we can make sure the rescue map doesn't go dark with the towers.
BOTH: We're SOSora.
END CARD: github.com/peanutz28/sosora · Tool-Calling track · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym
