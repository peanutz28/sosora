# V3 aerial flooded-road results

On 38 sealed held-out tiles, F1 went from 0.306459 to 0.273577.

V3 did not beat native v2 on final F1. It is not promoted; the ML service default is unchanged.

This is a single frozen geographic assessment within the known Louisiana and Germany events. It is not unseen-event generalization, an official SpaceNet test benchmark, or Helene accuracy.

| Model | Parameters | Initialization | Dev F1 | Final F1 | Final precision | Final recall | Final IoU |
|---|---:|---|---:|---:|---:|---:|---:|
| Current native v2 | 3,714,658 | Historical fine-tuned ADE-derived SegFormer | 0.176015 | 0.306459 | 0.250597 | 0.394372 | 0.180958 |
| Selected V3 segformer | 3,714,658 | Saved pretrained ADE-derived binary initialization | 0.631778 | 0.273577 | 0.190033 | 0.488211 | 0.158465 |

All final scores use identical original road-mask pixels, the same metric code, native sliding windows and the committed decision rule. Undefined denominators remain null. Full confusion counts and every tile are in [final_evaluation.json](evidence/v3_2026-10-18/final_evaluation.json).

The all-flooded control has final F1 0.261233; the all-non-flooded control has final F1 0.000000. These controls expose class imbalance; they are not pretrained flood models.

Across 822,357 identical scored pixels, V3 has 257,095 false positives versus v2's 145,711, and 63,232 missed flooded pixels versus 74,826. Its higher recall did not offset its lower precision. Tiles with no scored road pixels: 1 of 38; these remain in the manifest and per-tile results with undefined metrics. Overall scores pool labeled pixels rather than averaging tile F1.

Descriptive regional counts below are aggregates of the saved final confusion counts; they do not select another winner or trigger another evaluation.

| Known event region | Tiles | Scored pixels | Flooded pixels | v2 F1 | V3 F1 |
|---|---:|---:|---:|---:|---:|
| Germany_Training_Public | 17 | 409,452 | 123,551 | 0.409017 | 0.470199 |
| Louisiana-East_Training_Public | 21 | 412,905 | 0 | 0.000000 | 0.000000 |

The sealed Louisiana-East_Training_Public block has no positive flooded-road labels, so flooded-road recall there is undefined. It checks false alarms on its labeled road corridors: 79,733 for v2 and 184,397 for V3. This does not establish flooded-road recall for that region.


## Selection and complete run accounting

Selection was committed in `f161cb00e631bff5d4c525adb0c4146e5b4f02fa` before final preparation. It chose segformer, learning rate 0.0002, epoch 10, using only the 99 reviewed development crops from 19 tiles. These overlapping crops are correlated. The binary decision rule and all preparation/inference/metric source hashes were frozen in [selection.json](evidence/v3_2026-10-18/selection.json).

| Attempt | Kind | Outcome | Selected epoch | Best dev F1 | Elapsed seconds |
|---|---|---|---:|---:|---:|
| segformer_benchmark | throughput check | completed | — | undefined | 1.437319 |
| unet_benchmark | throughput check | completed | — | undefined | 0.983176 |
| 01_segformer_lr5e-05 | trained candidate | completed | 3 | 0.576150 | 184.476602 |
| 02_segformer_lr0.0002 | trained candidate | completed | 10 | 0.631778 | 185.779810 |
| 03_unet_lr0.0001 | trained candidate | completed | 13 | 0.404667 | 104.477027 |
| 04_unet_lr0.001 | trained candidate | completed | 18 | 0.286242 | 104.305961 |

Every attempted command, return code, log, checkpoint hash and epoch history is retained under [runs/](evidence/v3_2026-10-18/runs/). The short benchmark rows are throughput checks, not accuracy measurements. Learning rates and initialization differ across architectures; the bounded sweep does not establish equal optimization.

## Evidence and limits

- Selected raw checkpoint SHA256: `154f95c0679f59dedfe1c5c84fa4caf21f6cb098f208f6183dd06a9eb2d9d778`.
- Unchanged native-v2 identity: `sha256:3ab85783b140ec6ebfac7ad45cf78cb38e6b668c082b053d15ef3edcd20ee69b`.
- [Final preparation ledger](evidence/v3_2026-10-18/final_preparation_ledger.json) and [evaluation ledger](evidence/v3_2026-10-18/final_evaluation_ledger.json) record the one-shot stages. Completed stages refuse another evaluation; only a logged failed identical request may retry.
- No final tile was replaced or excluded based on outcomes. Cloud/alignment quality flags and empty-supervision tiles remain accounted for. Narrow buffered-road labels omit off-road false alarms and do not establish closures, travel safety or complete road extraction.
- V3 uses more training geography than the historical v2 run. Both final models are SegFormer-B0; data and training differ. The development gain did not transfer to this sealed set. Clouds, label alignment and sampling are limitations, not proven causes of the regression. The earlier frozen six-tile Germany result remains unchanged.
- Data: [SpaceNet 8 / SpaceNet Partners and Maxar](https://spacenet.ai/sn8-challenge/), licensed CC BY-SA 4.0. Source URLs and processing changes are listed in [data_attribution.json](evidence/v3_2026-10-18/data_attribution.json); the derived proof image retains that attribution/license.
- The stored global annotation CSVs predate this task. Final rows were not interpreted by this pipeline until the committed selection guard passed; the historical seal file was preserved unchanged.
- [1920×1080 proof image](../screenshots/vision-v3-proof.png) uses saved predictions only. Its first tile shows V3 regression by lower F1. No model was rerun to make the image.

## Compute and promotion

Only the approved L4 was used at the quoted $0.845421/hour. Its stop was verified at `2026-10-18T06:43:53.176859+00:00`. Elapsed-time compute estimate: $0.3550; this is not an invoice and excludes retained storage. Quote, CUDA verification, shutdown evidence and cost inputs are saved in this evidence directory. Codex B's H100 was not used.

No V3 promotion: the selected checkpoint lost on final F1, so no environment gate or serving changes were added. The default remains native v2. No ML service restart was needed. The final set is now spent for model selection; future tuning requires a fresh held-out evaluation set.
