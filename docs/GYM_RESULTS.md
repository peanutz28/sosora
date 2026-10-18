# NeMo Gym: hosted API versus Brev vLLM

All scenarios are simulated. Same frozen tasks, policies, custom chat-completions
runner and pinned official NeMo Gym tools/verifier; this is not the full Gym CLI.
No weights were updated and no RL was performed. Both policies run on validation
before either runs on test; test data does not tune the policy.

| Serving | Split | Policy | Pass / requested | Provider errors | Mean request ms |
|---|---|---|---:|---:|---:|
| Hosted NVIDIA API | validation | baseline | 1/14 | 7 | 4536.8 |
| Hosted NVIDIA API | validation | evidence_first | 7/14 | 3 | 1633.6 |
| Hosted NVIDIA API | test | baseline | 1/14 | 5 | 1336.5 |
| Hosted NVIDIA API | test | evidence_first | 4/14 | 8 | 1425.2 |
| Brev vLLM | validation | baseline | not measured | — | — |
| Brev vLLM | validation | evidence_first | not measured | — | — |
| Brev vLLM | test | baseline | not measured | — | — |
| Brev vLLM | test | evidence_first | not measured | — | — |

Hosted results contain transport failures; they do not isolate policy quality.
Serving comparisons also change checkpoint precision and backend defaults. The vLLM
server disables thinking by default; the unmodified Gym runner has no per-request
thinking flag. Server structural grammar is disabled for native tool parsing; frozen
strict tool schemas are unchanged and HTTP tools/verifier validate arguments.
Do not attribute all score changes to transport or call this RL.

## Reproduce

```sh
# Export private LLM configuration and these existing runtime paths:
# GYM_PYTHON, GYM_OFFICIAL, GYM_OUTPUT (fresh directory).
bash scripts/vllm/run_gym.sh
python3 scripts/vllm/summarize_gym.py --new ml/nemo_gym/evidence/vllm_2026-10-17
```

New evidence: `ml/nemo_gym/evidence/vllm_2026-10-17`. Each run saves rollout traces, metrics and configuration.
Failed scenarios remain in the requested denominator; no selective retries.

## Frozen task hashes

- `ml/nemo_gym/data/validation.jsonl`: `95cc3e20a782cd11c73c1ce5211b5fbdf9df5f867844472ed472b6abde643650`
- `ml/nemo_gym/data/test.jsonl`: `2b86c0e594b586f733a03f23ae5e607dfaa02a5182e4a1111a921945a8587e3b`
