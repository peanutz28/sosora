# V3 postmortem and next experiment

**V3 learned a strong development result that did not generalize to the held-out geography. The measured failure was excess false alarms on dry roads. We have not established a single causal training bug.** Native v2 stays served.

This investigation used the original reviewed training/development masks, the existing development histories, and new CPU inference on the development tiles only. It refers to already-published final aggregate counts to describe the observed loss. It did not reopen sealed imagery, masks or predictions, run another final evaluation, select a different checkpoint, change the threshold or train a model. The original final set remains spent. [Data-access and integrity audit](evidence/v3_diagnosis_2026-10-18/integrity_audit.json).

## What the evidence establishes

The original result remains F1 **0.306459 → 0.273577**. V3 found more flooded pixels but generated more false positives: precision **0.250597 → 0.190033**, recall **0.394372 → 0.488211**. These are the original saved results, not a new score. [Original report](V3_RESULTS.md).

On the published Louisiana final block, every scored road label is non-flooded. The false-positive rate on those labeled road pixels was **19.31% for v2 versus 44.66% for V3**. On the old development block from that same capture, the direction is reversed: **10.88% versus 2.91%**. Thus a changed proportion of flooded labels alone cannot explain the loss: the conditional error rate on dry roads also changed. Geographic appearance and image quality are plausible contributors, but these counts do not distinguish them. [Saved comparison](evidence/v3_diagnosis_2026-10-18/diagnosis_summary.json).

## A simple preprocessing or crop-window failure does not fit the checks

I scored the unchanged frozen checkpoints over all of the original development parent tiles using the original native tiler and metric code:

| Development scope | Native v2 F1 | Frozen V3 F1 |
|---|---:|---:|
| Original reviewed crops used for selection | 0.176015 | 0.631778 |
| Full development tiles, diagnostic only | 0.217157 | 0.688286 |

V3 still wins when crop-centered selection is replaced by full-tile inference on development. The manual training preprocessor and inference processor produced exactly equal input tensors and logits on the checked development crop. The selected raw checkpoint, native-v2 identity and frozen sources also still match their committed hashes. This weakens the hypothesis of a simple resize, normalization or checkpoint-loading error; it does not prove the pipeline is free of every possible issue. [Development results and parity checks](evidence/v3_diagnosis_2026-10-18/development_inference.json).

## Likely weaknesses, with their limits

- **Too little independent validation geography.** The reviewed data contains the saved training/development tile membership, while crop selection emphasizes supervised road centers and alternates flooded/dry-dominant windows. Development crops can overlap. The dry Louisiana capture contributes only 9 reviewed training tiles and 5 development tiles. Its crop labels repeat supervised pixels by a factor of 1.796. More crops are not equivalent to more independent geographic tests. This is a validation-risk explanation, not proof that sampling caused the regression. [Sampling audit](evidence/v3_diagnosis_2026-10-18/sampling_audit.json), [crop selection code](../../scripts/ml/prepare_road_crops.py).
- **Training/selection is noisy.** The selected run peaks at development F1 0.631778 at its saved selected epoch and ends at 0.248902; its largest adjacent-epoch change is 0.315590. A small-batch, fixed-rate run with all weights training and a BatchNorm decode head can be sensitive to batch composition and running statistics. Those are hypotheses to test, not a diagnosed BatchNorm fault. The runner did not save training loss, so there is insufficient evidence to claim conventional train-versus-validation overfitting. [History audit](evidence/v3_diagnosis_2026-10-18/training_history_audit.json), [actual training code](../../ml/experiments/train_comparator.py).
- **Development curation is cleaner than an unfiltered target.** Existing train/dev preparation excluded or quarantined cloud/alignment concerns; the sealed assessment retained all fixed tiles. Do not now filter final examples to improve its score. Cloud/registration issues could matter, but their causal contribution was not measured. [Frozen readiness record](evidence/v3_2026-10-18/frozen_inputs/readiness.json), [preparation code](../../scripts/ml/prepare_v3_experiment.py).
- **The target remains narrow.** Unknown/off-road pixels are ignored. These metrics measure flood state on labeled road corridors; they do not establish road extraction, passability, closure correctness or calibrated safety confidence. No Helene accuracy or unseen-event generalization was measured.

## What to try next, in order

1. **Fix validation coverage before changing architecture.** Pre-register a new experiment protocol. Keep every spent final ID and historical test ID excluded. Use geographically separated development folds from the remaining train/dev pool, with multiple blocks per capture/region. Evaluate full parent tiles, report per-region precision/recall and dry-road false-positive rates alongside pooled F1, and count independent tiles/blocks rather than crops. Reserve a genuinely fresh holdout geographically separated from all development data; seal its IDs before model selection. New-event claims require a new labeled event.
2. **Test a focused SegFormer data experiment.** Keep the architecture fixed. Within training folds only, add diverse independently reviewed dry-road negatives and sample across captures/regions. Compare road-balanced training against the original sampler, with label-preserving augmentation as a separate ablation. Avoid blindly increasing positive-class weight, since excess flood false alarms are the measured failure. Mine hard negatives only from training folds; do not use the spent final set.
3. **Make optimization observable and stable.** Save training loss, class/region counts, gradient diagnostics and per-region development metrics at every checkpoint. Use a small predeclared seed/LR comparison, testing a lower backbone rate and warm-up/decay. Separately test frozen/re-estimated decode-head BatchNorm statistics. Compare the existing native-v2 warm start against the original ADE-derived binary initialization under identical data and budgets. No candidate is assumed better until it passes development checks.
4. **Choose operating rules only on development.** If precision must improve, select a threshold or quality-abstention rule against a predeclared false-positive/recall objective on the geographic development folds, then freeze checkpoint, preprocessing and decision rule. Do not choose them against the old final counts. Evaluate the newly sealed holdout once, comparing unchanged v2 and the development winner with the same scoring code. Report the result either way.

The first useful experiment is a fixed-architecture, geographically cross-validated dry-road-negative ablation, not a larger model or more epochs by default. These are proposed experiments; none has been trained or scored here. Any future GPU launch still requires explicit approval of its type and hourly price. The L4 remains stopped.

Reproduce this diagnosis on development only with [diagnose_v3_development.py](../../scripts/ml/diagnose_v3_development.py). Its recorded membership guard rejects sealed IDs before any image access. The script refuses to overwrite completed diagnostic inference evidence. Every number above is in the linked saved evidence; the original selection and final results remain unchanged.
