# Frozen cross-event evaluation — Germany SpaceNet8

Selected checkpoint: `sha256:3ab85783b140ec6ebfac7ad45cf78cb38e6b668c082b053d15ef3edcd20ee69b`. Same nativecpuv2 epoch9; configuration/threshold frozen before new label access. No training, threshold adjustment or re-selection occurred.

## Result

| Model/control | F1 | IoU | Precision | Recall |
|---|---:|---:|---:|---:|
| tuned | 0.46626 | 0.30401 | 0.40188 | 0.55521 |
| baseline | 0.23083 | 0.13047 | 0.15633 | 0.44103 |
| all_positive | 0.07709 | 0.04009 | 0.04009 | 1.00000 |
| all_negative | 0.00000 | 0.00000 | undefined | 0.00000 |

Six selected and prepared tiles; zero preparation/inference failures. 72,961 labeled road pixels, 2,925 flooded (4.01%). Tuned confusion: TP1,624 / FP2,417 / FN1,301 / TN67,619. Runtime 24.4s for model and baseline inference, not a throughput benchmark.

## Failure cases and complete tile accounting

| Source tile | TP | FP | FN | TN | F1 |
|---|---:|---:|---:|---:|---:|
| 10500500C4DD7000_0_45_63 | 0 | 0 | 0 | 5065 | undefined |
| 10500500C4DD7000_0_18_66 | 0 | 2417 | 0 | 44671 | 0.00000 |
| 10500500C4DD7000_0_31_63 | 1624 | 0 | 575 | 2878 | 0.84959 |
| 10500500C4DD7000_0_38_62 | 0 | 0 | 726 | 0 | 0.00000 |
| 10500500C4DD7000_0_45_70 | 0 | 0 | 0 | 9075 | undefined |
| 10500500C4DD7000_0_39_60 | 0 | 0 | 0 | 5930 | undefined |

All 2,417 false positives occurred on one dry tile. One fully positive labeled-road tile had 726 missed flood pixels and no true positives. A second positive tile achieved F1 0.850. The three correctly negative tiles have undefined positive-class F1 (no true/predicted positives), not fabricated perfect scores. Aggregate improvement does not mean consistent tile-level reliability.

## Protocol and provenance

Official source: https://spacenet.ai/sn8-challenge/ ; individual image/label files from https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Germany_Training_Public/ . License CC-BY-SA4.0. Germany2021 flood event; exact tile capture dates unverified. No Helene accuracy is measured.

Downloaded 32,209,671 bytes (32.2MB), under frozen160MB budget. Frozen selection used seed17017 on sorted image mapping, not flood labels, with no class balancing. Six tile IDs/footprints were persisted before opening the reference flood labels; no replacements afterward. New sample footprints are separated by at least851.9m in EPSG3857. All are in Germany, and the nearest prior Louisiana tile center is 7944km away (great-circle). No previously downloaded tile was selected.

Masks retain the prior four-source-pixel buffered road-centerline convention, ignore255 and bilinear post-to-pre warp. This avoids changing evaluation methodology after viewing labels, but residual registration and corridor-width errors remain. Model/nativewindow256, stride256, binaryargmax0.5 were fixed. The baseline is the saved random binary head on a pretrained backbone/decoder, not a pretrained external flood detector.

## Limits and prior score

This is a small label-blind cross-event convenience sample, not the official SpaceNet test split, a full benchmark, or deployment accuracy. Only two of six tiles have flooded labeled road pixels. Narrow road support excludes off-road false positives. Results cannot establish closures, safe routes, or current conditions. No changes to the frozen model will be made based on this set. Future adaptation would require a new untouched evaluation split.

The earlier Louisiana F1 0.674 / IoU0.509 remains a reused four-tile within-event evaluation. Earlier results/images informed diagnosis, so it is not a pristine holdout. It must not be used alone as a generalization claim. The new Germany F1 0.466 / IoU0.304 is the frozen cross-event result; Swannanoa remains unmeasured zero-shot transfer.

All raw counts, source URLs/SHA256s, selected footprints, freeze time, preparation failures, and final identities are preserved in this evidence folder and ml/artifacts/sn8_frozen_external/. No data/models were published.
