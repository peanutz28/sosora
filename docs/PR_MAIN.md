# SOSora: integrate field intake, grounded tool calling and command dashboard

Draft PR: **integration → main**. Do not merge automatically; the owner will merge.

SOSora turns a field report into an evidence-backed road update and a map of
which simulated SOS incidents lose road access. This integrates the FastAPI
Command backend, real Swannanoa road graph, Nemotron parsing/tool calling,
Next.js command map, Beacon client, mobile adapters and evaluation evidence.

## Resulting behavior

- A Beacon bridge-collapse report resolves the eastern Warren Wilson Road bridge,
  records closure evidence and recomputes access for the simulated incident queue.
- Ambiguous roads require operator review; code rejects unsafe mutations and
  unverified reopening claims. Imagery failure is disclosed in the assessment.
- The dashboard streams tool progress, closures and access counts; cached demo
  replay requires no model key while executing the real graph tools locally.
- Beacon audio/sensor intake, durable retries and mobile SOS adapters connect field
  input to Command. Physical device delivery limits remain documented.
- README now leads with demo/video links, evidence-backed results, track/bounty
  targets and features; quickstart uses separate terminals and a real seed message.
  SQLite sidecars are ignored; the named stray journal was already absent.

## Evidence and validation

Fresh committed integration clone at `bc5184f`: dependency installs passed,
backend health and cached hero passed (nine seeded; exactly SOS-001..005 affected),
frontend HTTP 200, **41 backend tests and 16 frontend tests passed**. Alternate
ports avoided disturbing the running demo. See [quickstart receipt](QUICKSTART_VERIFICATION.md).
These checks do not validate concurrent uncommitted changes or physical hardware.

Gitleaks 8.30.0 scanned all locally available full-history refs: six candidates,
all manually classified as noncredential source data; no confirmed secrets.
[Scan scope and sanitized findings](SECURITY_SCAN.md). No values are reproduced.

Saved live results: exact bridge/five-cut-off 20/20; ambiguous final review 10/10
but strict model abstention only 1/10. Fresh sealed Gym mean passes /42: baseline
15, prompt-only 29.67, grounded_v2 30, three runs each and zero provider errors.
See [serving evidence](VLLM_RESULTS.md) and [Gym evidence](GYM_RESULTS.md).

## Limits and remaining release checks

This is a simulated exercise on real roads, not a dispatch system. Gym tasks are
synthetic; missing-location and tool-failure families still fail. No Nemotron
weight update or RL gain is claimed. Upstream vLLM was verified; Red Hat image use
and bounty eligibility are unverified. Experimental vision V3 was not promoted.

- Add the final video URL before submission.
- Recheck the public demo immediately before sharing; free hosting may cold-start.
- Review the final integration diff and rerun relevant checks after concurrent
  work lands. npm reported one moderate, one high and one critical vulnerability;
  dependency remediation remains separate from this docs change.
- Preserve ignored credentials and review the scan's local-ref scope before release.

No merge or remote PR creation was performed by this task.
