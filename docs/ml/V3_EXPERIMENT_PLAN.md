# Bounded v3 experiment — preparation, not a result

The historical native-v2 model, four-panel demo and Germany six-tile result remain unchanged. No v3 improvement is claimed. Additional public-data storage is capped at 2 GiB, including raw and derived preparation files; raw source files may use at most 1.5 GiB. Downloads have bounded retries and SHA256 receipts. No paid infrastructure is started by these scripts.

Run metadata-first planning with `python -m scripts.ml.prepare_v3_experiment plan`. It uses existing mapping CSVs and grid anchors, selects fixed geographic blocks without flood labels, downloads pre-event rasters to verify their actual footprints, and checks at least 1,000 metres edge separation across splits in UTM15N/32N. Historical Louisiana and Germany tile IDs are excluded. The protocol is written only after verification; it refuses to overwrite an existing protocol.

Then `python -m scripts.ml.prepare_v3_experiment prepare` checks the protocol digest and creates a timestamped final-ID seal before interpreting training/development labels. Final rows are filtered out before CSV flood attributes or geometry are interpreted; no final masks or post-event imagery are prepared. Existing shared public reference CSVs were already cached during historical work; sealing means the newly selected final records are not used by this pipeline, not that the global dataset annotations have never existed on the machine.

Training/development preparation compares both listed post-event images where available, using fixed coverage, bright-neutral/cloud and coarse gradient-alignment screens, never model performance. Selected sources and all alternatives are recorded. Geospatial warping alone does not guarantee registration. The gradient screen can fail under clouds, flooding and appearance changes; it applies no correction and flags cases for manual review. Bright-neutral screening is not a validated cloud mask. Low-coverage, insufficient-supervision and cloud-screened tiles are logged, not silently replaced. A readiness report requires manual quality review before full training.

Crops remain native 256px with unknown=255. Overlapping label-centred crops are correlated; counts are not independent observations. New full training must use development only for selection and retain a separate sealed final evaluation. New geography within Louisiana/Germany is not unseen-event generalization.

The new runner is `python -m ml.experiments.train_comparator`. It accepts training/development crops only and rejects final/test rows. The four-level width16 U-Net (1,962,642 parameters, random initialization) is a **trained supervised architecture comparator**, not an official SpaceNet baseline or general-purpose pretrained flood detector. SegFormer (3,714,658 parameters) starts from the saved ADE-derived binary initialization. Both use the same normalization, ignored-pixel cross entropy, AdamW and binary argmax, with all weights trainable. Capacities and initialization differ. Learning rates must be specified and justified using development data; a shared rate is not evidence of equal optimization.

CPU benchmark on this Mac, batch4 / two threads / 3 warmup +10 measured steps:

- Four-level U-Net: 3.379s/step, 36.94s total for13 steps.
- SegFormer: 1.605s/step, 21.25s total for13 steps.
- A repeat U-Net benchmark on the reviewed manifest measured 1.152s/step (16.85s total); host load materially affects these short measurements. At544 training crops, batch4 and20 epochs (2,720 updates), U-Net training alone projects to52–153min using the observed1.152–3.379s range; SegFormer measured1.654s/step on the reviewed manifest (22.02s for13 steps), projecting to75min; its earlier1.605s measurement projects to73min. Add99 development crops per epoch, loading and thermal margin. These are extrapolations, not runtime guarantees; data preparation and GPU throughput are separate.

The earlier 118k-parameter two-level U-Net benchmark is historical and must not be used to estimate the upgraded model. Long training is held while CPU/GPU choice and a precise runtime/cost cap are discussed. GPU availability, quoted price, credit eligibility and persistent-storage charges require live account verification; 48GB describes GPU memory, not a model-size requirement. No v3 model is promoted to the current API by this runner.

Preparation completed within the cap:113 usable tiles and742 crops after6 no-supervision
and5 bright-cloud exclusions. All14 alignment-flagged pairs were visually reviewed and
conservatively quarantined without applying a registration correction. The original
prepared manifest remains intact; `reviewed_crop_manifest.json` records the smaller
reviewed set. `readiness.json` binds full training to its exact manifest hash. This is
training/development curation only; the38 sealed final IDs are unchanged. Unflagged
images can still have label/registration errors. No new model result is claimed.

The reviewed set contains80 training /19 development tiles and544 /99 crops. Total additional preparation storage is1,259.2MiB, below2GiB. The protocol SHA256 is `d557eb517e128b3d1a7a3d921850fbbc0d3fa0091ad046436fc42d156cf49ade`; the approved manifest SHA256 is `6d406a00b2247d369fce27caa9d96c3236ba3652136d7a32c1ebbd9aa9b03ebd`. The38 final IDs were sealed at2026-10-17T20:43:09.940735+00:00 before this pipeline interpreted training/development flood labels. No final masks or post-event images were prepared.
