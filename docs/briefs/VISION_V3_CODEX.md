# Codex D brief: V3 aerial flood-road model (optional upside, never blocks the demo)

Owner: Codex D. Planner/checker: Claude. Written 2026-10-18 02:10 ET.

## Goal
Run the already-prepared V3 experiment on a GPU, pick a winner on the development set only,
then open the sealed 38-tile final set exactly once and report the current model (native v2
SegFormer) vs the V3 winner on those same final tiles. Honest result either way.

## Read first
- docs/ml/V3_EXPERIMENT_PLAN.md (protocol, hashes, sealing rules)
- ml/experiments/train_comparator.py and ml/experiments/README.md
- scripts/ml/prepare_v3_experiment.py, scripts/ml/budget_guard.py, scripts/ml/gpu_check.py
- docs/ml/FROZEN_EXTERNAL_EVALUATION.md (how the current 0.231 -> 0.466 Germany number was made)
- docs/CONTEXT.md (hard rules)

## Hard rules
1. Do NOT touch: backend/app/agent.py, backend/app/radio_api.py, frontend/, dashboard/, ios-app/,
   beacon/, ml/nemo_gym/. The demo path is frozen to you.
2. GPU: do NOT use the H100 that Codex B uses for vLLM/Gym. Launch a separate small Brev GPU
   (L4, A10, or similar is plenty: SegFormer-B0 is 3.7M params, U-Net 1.96M). Before launching,
   print GPU type and hourly price and wait for Kam's OK. Brev credits only. Stop the instance the
   moment training/eval is done, and no later than 06:30 ET. Never commit the instance URL or keys.
3. Training must use the reviewed manifest (SHA256 6d406a00...03ebd); the runner already enforces
   this and rejects final rows. Do not edit the protocol or the seal.
4. Selection (architecture, learning rate, epoch/checkpoint, threshold) uses the 19-tile dev set
   only. Freeze the choice in a committed file (selection.json with dev metrics + chosen config +
   checkpoint SHA256) BEFORE preparing any final-set imagery or masks.
5. Final set: prepare and evaluate once. Evaluate BOTH the current native v2 model and the V3
   winner on the identical 38 final tiles with the same metric code (road-flood F1, precision,
   recall, IoU, plus per-tile results). No re-runs after seeing final numbers. If something
   crashes mid-eval, log it and rerun the identical command only.
6. Report every run, including losers and failures. Never write a number that isn't in a saved
   evidence file. No Helene accuracy claims (no ground truth). New geography in Louisiana/Germany
   is not unseen-event generalization; say so.
7. Budget: small LR sweep (e.g. 2 to 3 LRs per architecture), 20 epochs max, early checkpoint by
   dev F1. If the GPU isn't running by 03:30 ET, fall back to SegFormer-only on the Mac CPU
   (~75 min projected) or stop.

## Deadlines (ET)
- 05:30 selection.json committed.
- 06:30 final eval done, GPU stopped.
- 07:00 feature freeze. Anything not done is dropped, not rushed.

## Deliverables
- docs/ml/V3_RESULTS.md: table (model, params, init, dev F1, final F1/P/R/IoU), the honest
  sentence for the video ("On 38 sealed held-out tiles, F1 went from X to Y"), caveats.
- docs/ml/evidence/v3_2026-10-18/: configs, logs, selection.json, final metrics JSON, checkpoint hashes.
- One 1920x1080 proof image: 3 to 4 final tiles, columns = image / ground truth / v2 / V3
  (include at least one tile where V3 is worse). Save to docs/screenshots/vision-v3-proof.png.
- Promotion: only if V3 beats v2 on final F1, add it to the ML service behind an env var
  (ML_MODEL_VERSION=v3, default unchanged), keeping the /ml/predict contract identical, with a
  smoke test. Otherwise no promotion.
- Update docs/CONTEXT.md Status row "Vision V3" and the Changelog. Commit to integration with
  clear messages. Do not push secrets.
