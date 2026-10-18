# SOSora video script v6: sell the track and every bounty (~4:30 at your pace, hard max 5:00)

Every claim maps to a judging criterion. Lower-thirds name the criterion/prize while you talk.
[X] = number from the final-sprint runs; if a run doesn't finish, cut that sentence (never guess).
Rules: [SIMULATED] labels visible; no phone signal bars with "no signal"; public-domain Helene footage only.

## COLD OPEN (0:00–0:10)
[Dark. Pi button. Dashboard: bridge red, counter hits 05.]
RIA (radio voice): "Command, Engine 4. Warren Wilson Road bridge is gone. Three families on the far side."
JIA (VO): That one radio call just cut five families off from rescue. SOSora knew in seconds.

## INTRO + PROBLEM (0:10–0:40)  [both on camera, then Helene footage + stats]
JIA: Hi, I'm Jia.  RIA: And I'm Ria. We're sisters from North Carolina, and this is SOSora.
JIA: When Helene hit western North Carolina, about three quarters of cell sites in the disaster area went down, and more than 8,100 roads, bridges and culverts were damaged.
RIA: Rescuers lost two things at once: who needs help, and which roads still work. The state's own review says local teams need to run for 72 hours with no communications.
JIA: So we built a rescue map that keeps working with no internet at all.

## SOLUTION (0:40–1:00)  [diagram → Pi → phone → GPU terminal]
RIA: Three parts. A beacon: a Raspberry Pi with a mic and a water sensor that sits by a bridge. An app that holds your SOS until it finds a connection. And Command: one GPU box in the county's command truck.
JIA: The brain is a single small model, NVIDIA Nemotron 3.5 Lightning, served with Red Hat's vLLM, and graded with NVIDIA NeMo Gym. Everything runs on open data: real OpenStreetMap roads, the Hurricane Center's Helene track, and public flood imagery.

## DEMO: TOOL CALLING (1:00–2:25)  [lower-third: TOOL-CALLING TRACK; checklist ticks on screen as you say each]
JIA: Here's a drill on real Swannanoa roads. Nine simulated SOS calls. Teal lines are routes our truck can take.
RIA: The radio call comes in.
[Agent trace.] JIA: Watch the right side. Nemotron decides when to call a tool and which one. Find the road. Check its status. Check aerial imagery. There's none, so it keeps the uncertainty instead of inventing an answer. Report it. Recompute who we can reach.
RIA: Five families cut off. And our truck's routes reroute around the bridge.
[Responder radio, A/B.] JIA: Now the hard case: no location, and two bridges with that name. It doesn't guess. It asks the dispatcher.
RIA: In thirty live tests, the model tried to close a bridge on its own nine times out of ten. Our code verified every change and blocked all nine. The model suggests. The code decides.
[DOT says open.] JIA: An unverified "it's open" can't reopen a road. A wrong "open" sends a crew into a river.
[Imagery offline.] RIA: When a tool fails, the error goes back to the model, it says so, and still lands on a safe answer. If it sends a bad call, like two tools at once, we return the error and it corrects itself on the next turn.
[Pi: water pour; router unplug, replug.] JIA: The beacon reports by itself when water crosses the line, and holds reports when the link drops.
[Optional, only if verified: phone in airplane mode → SOS queued → reconnect → pin drops.]

## WHY LIGHTNING (2:25–2:55)  [lower-third: NEMOTRON LIGHTNING]
RIA: Why Lightning? It's a hybrid Mamba-Transformer mixture of experts: about 32 billion parameters of knowledge, but only around 3 billion active per token. Smart enough to read messy radio, fast enough for one GPU in a truck.
JIA: It does two real jobs: turning radio chatter into structured reports, and running the agent. We use its native tool-call format, switch its reasoning mode off for speed, and follow NVIDIA's recommended sampling. Counting every expert, plus its built-in prediction heads and our speech model, we're at 32.95 billion, under the 33 billion cap.

## WHY vLLM (2:55–3:30)  [lower-third: RED HAT vLLM; show the serve command + numbers]
RIA: vLLM isn't bolted on. It's how Command runs. It serves Lightning on one H100 with the native tool parser and the Nemotron reasoning parser, prefix caching for our long system prompt, and continuous batching.
JIA: One agent step went from 24 to 55 seconds on the hosted API to 0.85 seconds.
RIA: And in a storm, reports arrive all at once. We fired 100 radio reports at the same time, and vLLM's continuous batching cleared all of them in 21 seconds. One at a time, that took 85.
JIA: Across thirty live runs, it found the right bridge twenty out of twenty times.

## WHY NeMo GYM (3:30–4:05)  [lower-third: NeMo GYM; show the results table]
RIA: To make the agent better, we needed a score. So we built a NeMo Gym environment: seven kinds of rescue tasks, real tools, and a verifier that grades every attempt.
JIA: On a sealed exam of 42 scenarios it had never seen, baseline Lightning passed 31 percent. We changed one thing at a time. A rewritten system prompt took it to 71. Then the Gym showed us exactly what was still failing: malformed arguments, like writing the word "None" instead of null. A small repair layer fixed those, and it hit 98 percent.
RIA: Same tasks, same settings, three runs each, every run published.

## CLOSE (4:05–4:25)  [both on camera]
JIA: A county emergency manager could use this tomorrow. One box, a browser, no internet.
RIA: We can't stop the next hurricane. But when the towers go down and the roads wash away, the rescue map shouldn't go down with them.
BOTH: We're SOSora.
END CARD: github.com/peanutz28/sosora · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym · Tool-Calling track
