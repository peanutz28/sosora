# Development-only architecture comparator

`python -m ml.experiments.train_comparator` accepts native 256×256 RGB crops
and binary road masks (0 non-flooded, 1 flooded, 255 ignored). It refuses any
final/test manifest row before opening image or mask files. Spatial groups and
identical paths cannot cross train/validation splits; geographic footprint
separation must additionally be enforced by the upstream preparation protocol.

The four-down/four-up U-Net (width 16, bilinear upsampling) has random initialization and is a **supervised architecture
comparator**, not a general-purpose pretrained detector. The SegFormer option
loads the existing local binary initialization checkpoint with downloads disabled.
Both use identical ImageNet normalization, full-resolution interpolated logits,
unweighted ignored-pixel cross entropy, AdamW, and binary argmax evaluation.
All weights train. Learning rates and budgets are explicit; choose them using
development only. No augmentation, class weighting, threshold tuning or final
label evaluation is implemented here.

Explicit `--device cpu` or `--device cuda` is required. `--max-seconds` is checked
between batches after setup, so one batch or checkpoint write can overrun it.
`--max-steps` caps optimizer updates. Complete validation selects the earliest
strictly best finite F1 checkpoint; a partial final training epoch can be validated
but incomplete validation cannot select a checkpoint. The runner never promotes
models into the current demo. `best.pt` is a raw state dict, requiring the same
architecture to reload, and `run.json` records settings, manifest hash and counts.

For a short throughput check add `--benchmark --warmup 3 --max-steps 13`.
Benchmark checkpoints are never saved and validation is skipped. Step timing
includes forward/backward/update but excludes PNG loading and setup; use total
elapsed time as well when estimating a full run. Existing crop manifests containing
test rows must be explicitly filtered by an upstream development-only manifest.

The U-Net has 1,962,642 parameters versus SegFormer’s 3,714,658. This is a
roughly comparable order of capacity, not parameter matching. The earlier two-down
118,290-parameter benchmark remains historical and does not describe this model.

For v3 manifests, a neighboring `readiness.json` must explicitly record completed
manual quality review before full training. Bounded benchmarks may run before that
review. Run metadata includes saved-checkpoint and runner-source hashes for freezing
selection before final evaluation.
