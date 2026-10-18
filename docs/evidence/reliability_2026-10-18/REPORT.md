### Operational accuracy and model behavior

After Gym finished, exactly **20 beacon reports and 10 ambiguous responder reports** ran sequentially, each from a fresh seed of nine initially reachable simulated incidents on the real Swannanoa OSM graph. No benchmark retries or cached parse/agent fallback counted as success. All 30 completed live.

| Check | Result | Definition |
|---|---:|---|
| Beacon correct segment | 20/20 (100%) | Closed IDs exactly `549633356:0:b` and `549633356:0:f`, the eastern bridge |
| Beacon exact five-cut-off | 20/20 (100%) | Both assessment and state lose exactly SOS-001 through SOS-005 |
| Guarded final ambiguity | 10/10 (100%) | Two plausible bridge locations observed, human review requested, no road closed and no incident loses access |
| Strict model ambiguity abstention | **1/10 (10%)** | No attempted `report_segment` mutation while location remains ambiguous |

**The 10/10 ambiguity outcome depends on the code safeguard.** In 9/10 ambiguous runs the model attempted to report all four direction IDs across both candidate bridges as blocked. Code rejected each with `location unresolved; human review required`; the final state stayed unchanged and requested review. This is not 10/10 model-only disambiguation. Some summaries also describe rejected reports loosely as recorded (for example runs 27, 28 and 30); narrative faithfulness was not scored and is not established by the state checks. No prompt or behavior fix was made during this experiment.

### Latency

| Workload | Requests | Agent model calls | Model-call median / p95 | Whole agent workflow median / p95 | Full text-radio request median / p95 |
|---|---:|---:|---|---|---|
| Beacon | 20 | 120 | 0.628 / 1.633 s | 6.922 / 8.431 s | 7.912 / 9.782 s |
| Ambiguous responder | 10 | 59 | 0.668 / 1.579 s | 6.345 / 7.813 s | 7.455 / 8.671 s |

Model-call timing wraps each original `RadioAgent.completion`, including any original retry behavior. Whole-agent timing wraps `radio_api.run_report`, including agent construction, tool calls and graph work but excluding parsing. End-to-end timing is the in-process HTTP `/api/radio` request, including live ML parsing, model/network calls, graph computation and response serialization. It excludes fresh seeding, graph loading, browser rendering/WebSocket delivery, ASR, microphone, physical radio/LoRa transport and human confirmation. Seed time is retained separately. This is a live remote-GPU text-ingress measurement, not an offline-laptop or microphone-to-map latency test.

P95 uses nearest rank `ceil(0.95*n)`: with ten responder requests its p95 is the maximum. All attempted requests are retained; successful-only latency is identical here because all 30 met the guarded checks. Messages and positions repeat identically, with server prefix caching enabled and no cache flush. This measures repeatability of the hero scenario, not varied field conditions. The backend was copied into a fixed local runtime before measurement; exact source archive/hashes (including pre-existing mobile changes) are saved. Do not attribute differences from the earlier five-run timing solely to model speed.

### Isolation and filming readiness

The model queue was empty before and after measurement. GPU samples every five seconds (59 process samples) and final container/process capture show only vLLM. The successful-request counter rose by exactly **209**, matching **179 agent calls + 30 parse calls**, with no unexplained generation traffic. The coordinating chat reported no H100/Parakeet workload; no separate Codex E service was identifiable. ASR was not running in this measurement. Coordination, process samples and server counters are saved.

H100 was verified **RUNNING, HEALTHY**, with a valid authenticated model endpoint and healthy local ML API after measurement. It remains running for **7 AM ET filming on Oct 18**; no automatic shutdown is scheduled. Ongoing compute/storage charges continue. `.env.vllm` remains local/ignored; source it in the Command process for live calls (the benchmark uses its own in-process app and does not change an already-running dashboard backend’s environment). Resume/stop commands above remain available; stop manually after filming when no longer needed.

### Reproduce and evidence

All raw runs, per-tool events, individual call latencies, summaries, source archive/hashes, GPU samples, metrics and readiness are under `docs/evidence/reliability_2026-10-18/`. Gym artifacts are under `ml/nemo_gym/evidence/ablation_reliability_2026-10-18/`. Checks: **48 Gym tests** and **9 radio API regression tests** passed.

```sh
# Private env exported, DEMO_MODE=false, local ML API and private tunnel running:
PYTHONPATH="$PWD/backend" /path/to/backend/python scripts/vllm/benchmark_reliability.py --output /path/to/fresh/radio_runs.json
```

The script refuses an existing output and always performs the same 20+10 sequence. The saved run used the fixed backend snapshot described in `measurement_sources.json`; the source archive permits reproducing that code without modifying current backend files.
