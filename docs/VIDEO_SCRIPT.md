# SOSora video script v5: short, punchy, pitch style (~3:20 at your pace)

Rules: [SIMULATED] labels visible. Never show phone signal bars while saying "no signal".
Public-domain Helene footage only (NCDOT, FEMA, National Guard/DVIDS, NOAA). Numbers match docs/.
Prize name as a lower-third during PROOF (NEMOTRON LIGHTNING, RED HAT vLLM, NeMo GYM, TOOL CALLING).
Say it in your own words wherever a line feels stiff.

## COLD OPEN (0:00–0:10)
[Dark. Hand presses the Pi button. Dashboard: bridge goes red, counter hits 05.]
RIA (radio voice): "Command, Engine 4. Warren Wilson Road bridge is gone. Three families on the far side."
JIA (VO): That one radio call just cut five families off from rescue. SOSora knew in seconds.

## INTRO (0:10–0:20)  [both on camera]
JIA: Hi, I'm Jia.
RIA: And I'm Ria. We're sisters from North Carolina, and this is SOSora.
JIA: It keeps the rescue map working when the cell towers and the roads go down.

## PROBLEM (0:20–0:45)  [Helene footage, stats on screen]
RIA: When Helene hit western North Carolina in 2024, about three quarters of cell sites in the disaster area went down. More than 8,100 roads, bridges and culverts were damaged.
JIA: So rescuers had two problems at once. They didn't know who needed help. And they didn't know which roads still worked.
RIA: Road reports came in over the radio and got written on whiteboards. The state's own review says local teams need to run for 72 hours with no communications.

## SOLUTION (0:45–1:05)  [diagram, Pi, phone, GPU terminal]
JIA: So we built three things that work without the internet.
RIA: A beacon: a Raspberry Pi with a mic and a water sensor you can mount near a bridge.
JIA: An app that saves your SOS on your phone until it finds a connection.
RIA: And Command: one GPU box in the county's command truck. It runs NVIDIA Nemotron 3.5 Lightning, which reads every report and updates the map.

## DEMO (1:05–2:30)  [presentation mode, fresh Seed each beat]
JIA: This is a drill on real roads in Swannanoa. Nine simulated SOS calls. The teal lines are routes our rescue truck can take. Everyone's reachable.
RIA: Now the radio call comes in.
[Agent trace.] JIA: Nemotron reads it, then works through its tools one at a time. Find the road. Check its status. Check for aerial photos. There aren't any, so it says it's unsure. Record the report. Recompute who we can reach.
RIA: Bridge closed. Five families cut off. Seconds, not hours.
[Responder radio, A/B.] JIA: Radio isn't always that clear. Here's the same call with no location, and there are two bridges with that name.
RIA: So it asks the dispatcher instead of guessing.
JIA: That matters. In our tests, the model tried to close a bridge on its own nine times out of ten. A rule in our code blocked it every time. The model suggests. The code decides.
[DOT says open.] RIA: If someone radios that the bridge is open, it stays closed until it's verified. A wrong "open" sends a crew into a river.
[Imagery offline.] JIA: If a tool goes down, it tells you, and still gives a safe answer.
[Pi on the table: water pour, router unplug/replug.] RIA: The beacon doesn't need a person. Water rises past the line, and it reports the road itself. If the link drops, it holds the report and sends it when the link comes back.
[Optional, only if verified on the real phone.] JIA: Residents can send an SOS with no signal. It waits on the phone and shows up here when it reconnects.

## PROOF (2:30–3:05)  [lower-thirds, terminal, evidence files]
RIA: Now the numbers.
JIA: One language model, Nemotron 3.5 Lightning. Counting every expert plus our speech model, we're at 32.95 billion parameters, under the 33 billion limit.
RIA: We serve it with Red Hat's vLLM on one H100. Each agent step went from 24 to 55 seconds on the hosted API to under one second.
JIA: In thirty live runs, it found the right bridge twenty out of twenty times, and held all ten unclear calls for a human.
RIA: We built a NeMo Gym environment to grade the agent. On 42 new scenarios, a better system prompt took it from 36 to 71 percent, and we tested each change on its own to see what helped.
JIA: We also fine-tuned an NVIDIA vision model for flooded roads. It isn't reliable yet, and we say so. SOSora treats it as a clue, not a fact.

## CLOSE (3:05–3:20)  [both on camera]
RIA: Counties already roll out command trucks after every big storm. SOSora is one box that goes in that truck.
JIA: No internet. Seventy-two hours. A map that still knows who you can reach.
RIA: We're Jia and Ria.
BOTH: And this is SOSora.
END CARD: github.com/peanutz28/sosora · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym
