# SOSora video script v7: explain it like you're telling a friend (~4:15)

Rule of thumb: every section answers one question a listener would ask, in plain words.
[Brackets] = the clip on screen. Lower-thirds name the track/prize during those parts.
Keep [SIMULATED] labels visible; no phone signal bars when saying "no signal"; public-domain Helene footage only.

## 1. WHO WE ARE + WHAT IT IS  [both on camera]
JIA: Hi, I'm Jia.
RIA: I'm Ria. We're sisters from North Carolina, and we built SOSora: a rescue map that keeps working when the internet doesn't.

## 2. THE PROBLEM  [Helene footage; stats appear on screen]
JIA: In 2024, Hurricane Helene hit our state. Two things broke at the same time.
RIA: First, the phones. About three out of four cell towers in the disaster area went down. People couldn't call for help, and rescuers couldn't get updates.
JIA: Second, the roads. More than 8,100 roads, bridges and culverts were damaged. So even when rescuers knew where someone was, they didn't know if they could actually get there.
RIA: The information existed. Crews were reporting washed-out bridges over the radio. But those reports ended up on paper and whiteboards, and nobody could see the full picture.

## 3. THE SOLUTION  [system diagram → command truck/laptop → Pi → phone]
JIA: SOSora fixes that. It's one computer that sits in the county's emergency command truck, and it needs no internet.
RIA: Reports come in three ways that still work in a disaster. Crews talk on the radio. A sensor box we built with a Raspberry Pi sits by a bridge and reports when the water gets too high. And residents use our app, which saves their SOS on the phone until it finds any connection.
JIA: An AI model reads every report, updates the map, and answers the one question dispatchers care about: who can we still reach, and who's cut off?

## 4. THE DEMO  [main clip: one continuous screen recording; Pi press composited in a corner]
RIA: Here's a drill on the real roads of Swannanoa, one of the towns Helene hit hardest. Nine people need help. The teal lines are the routes our rescue truck can take. Right now, we can reach everyone.
JIA: Now a crew radios in. [Pi button] "The bridge on Warren Wilson Road is gone."
RIA: The AI hears that, finds that exact bridge on the map, marks it closed, and recalculates every route.
JIA: Five of the nine are now cut off. The dispatcher knows in seconds instead of hours, and can send a boat or a helicopter instead of a truck.

## 5. HOW IT FITS THE TOOL-CALLING TRACK  [lower-third: TOOL-CALLING TRACK; close-up of the agent trace]
RIA: We entered the tool-calling track. That means one small AI model that gets real work done by using tools, kind of like how you use apps on your phone.
JIA: Our model has six tools: search the map for a road, check that road's status, look at aerial photos, mark a road closed, recalculate who's reachable, and file its report. You can watch it pick them, one at a time, right here.
[Aerial model clip: localhost:9030/fine-tuning.html] RIA: That aerial photo tool uses a vision model we fine-tuned to spot flooded roads. It isn't reliable enough yet, so the AI treats it as a hint, never as proof.
JIA: The track judges whether the model picks the right tool, handles errors, and doesn't break when something goes wrong. So here's what happens when things go wrong.
[Responder radio → A/B pins] RIA: This report doesn't say where the bridge is, and there are two bridges with that name. The AI doesn't guess. It asks the dispatcher.
JIA: In 30 live tests, the AI tried to close a bridge on its own 9 times out of 10. Our code checked every change and stopped it every time. The AI suggests. The code decides.
[DOT says open] RIA: If someone says a closed bridge is open again, it stays closed until it's verified, because a wrong "open" could send a truck into a river.
[Imagery offline] JIA: And if one of its tools crashes, it tells you, and still gives a safe answer.
[Pi: water pour; router unplug/replug] RIA: The sensor box doesn't need a person. When the water rises past the line, it reports the bridge itself. If the connection drops, it saves the report and sends it later.
[Phone mirrored next to dashboard: SOS form → airplane mode → reconnect → pin drops] JIA: Same with the app. No signal? The SOS waits on the phone, and the moment it connects, it shows up on the map.

## 6. THE TECHNOLOGY AND WHY WE CHOSE IT
RIA: Now, the technology, and why we picked it.
[NEMOTRON LIGHTNING; code + trace] JIA: The AI is NVIDIA's Nemotron 3.5 Lightning. A command truck can't hold a data center, so we needed a model small enough to run on one GPU, but smart enough to understand messy radio. Lightning only uses about 3 billion of its 32 billion parameters for each word, so it's fast. It does two jobs for us: turning radio chatter into structured reports, and choosing the tools. It's our only language model, which keeps the whole system under the hackathon's 33 billion parameter limit.
[RED HAT vLLM; Brev terminal: nvidia-smi + vLLM logs scrolling] RIA: To run it on the GPU, we use Red Hat's vLLM. On the hosted API, each AI step took 24 to 55 seconds. On vLLM, it takes 0.85 seconds. And because disasters create floods of reports, we sent 100 reports at once. vLLM handled all of them in 21 seconds, four times faster than one by one.
[NeMo GYM; the red-to-green grid page + notebook] JIA: But how do we know the AI is actually good? We used NVIDIA's NeMo Gym, which is basically a driving test for AI. We wrote 42 practice disasters it had never seen, and a grader that checks every answer.
RIA: It started at 31 percent. We rewrote its instructions, and it hit 71. Then the test showed us its last big mistake: it kept typing the word "None" where the answer should be empty. We fixed that, and it hit 98 percent. We changed one thing at a time, so we know exactly what helped.

## 7. CLOSE  [both on camera]
JIA: So that's SOSora. One computer in a truck, no internet needed, and a map that always knows who rescuers can still reach.
RIA: We can't stop the next hurricane. But we can make sure the rescue map doesn't go dark with the towers.
BOTH: We're SOSora.
END CARD: github.com/peanutz28/sosora · Tool-Calling track · Nemotron 3.5 Lightning · Red Hat vLLM · NeMo Gym
