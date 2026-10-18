# Brev + vLLM brief for Codex (owner: Ria). Budget: Brev credits available (~$700).

Why: hosted NVIDIA API took **24-55 s per agent turn** and caused **18 HTTP errors + 5
timeouts** in our Gym runs. Serving Nemotron 3.5 Lightning ourselves on vLLM fixes the demo
speed, cleans the Gym numbers, and is the Red Hat vLLM bounty. Read `docs/CONTEXT.md` first.

1. Launch one Brev GPU (H100 80GB or similar). Report GPU type and hourly cost before launch.
2. Serve `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B` (pick the precision this GPU supports;
   NVFP4 needs Blackwell) with vLLM, OpenAI-compatible, **tool calling enabled** using the
   tool-call parser / chat template the model card specifies. Expose port 8000 via Brev.
3. Point SOSora at it: `LLM_BASE_URL=<brev>/v1`, `LLM_MODEL=<served name>`, `LLM_API_KEY=<token>`
   for `backend/app/agent.py`; `LLM_PROVIDER=redhat_vllm` + same vars for `ml/`.
   Note: agent.py only sends Lightning-specific sampling when LLM_MODEL equals
   `nvidia/nemotron-3.5-lightning-30b-a3b`; serve under that name (`--served-model-name`).
4. Measure: run the hero flow 5 times (`POST /api/radio` beacon message) and record per-turn
   latency and total time. Write `docs/VLLM_RESULTS.md` with the exact vLLM command and flags.
5. Rerun NeMo Gym on vLLM: `ml/nemo_gym/evaluate_agent.py`, validation then test, baseline then
   evidence_first, same tasks and verifier. Save to a new dated evidence folder. Update
   `docs/GYM_RESULTS.md` with old (hosted) vs new (vLLM) tables and the reproduce command.
6. Surge (if time): 100 concurrent `/ml/radio/parse` calls, sequential vs concurrent,
   msgs/s and p50/p95. Same results file.
7. Stop the instance when idle and before 10:00 AM. Never commit keys or the instance URL.
