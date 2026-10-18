# SOSora parameter budget

**Served system including ASR: 32,954,738,082 parameters, 45,261,918 below 33B.** This counts every Nemotron expert and its MTP weights, plus the served SegFormer once. It does not use the rounded “30B” name or the active-parameter count. One billion means 1,000,000,000; the cap used for this arithmetic is 33,000,000,000.

| Model / scope | Exact parameters counted | Billions |
|---|---:|---:|
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16`, full checkpoint including MTP | 32,913,263,168 | 32.913263168 |
| SOSora flooded-road SegFormer-B0 (served native v2) | 3,714,658 | 0.003714658 |
| Served faster-whisper `tiny.en` (including frozen encoder positions) | 37,760,256 | 0.037760256 |
| `nvidia/parakeet-tdt-0.6b-v2` — **NOT used** | 617,825,926 | 0.617825926 |

| Counting rule | Exact total | Under 33B? | Margin |
|---|---:|---|---:|
| Nemotron + SegFormer, ASR excluded | 32,916,977,826 | **Yes** | 83,022,174 below |
| **Served: Nemotron + SegFormer + Whisper tiny.en** | **32,954,738,082** | **Yes** | **45,261,918 below** |
| Rejected alternative: Nemotron + SegFormer + Parakeet | 33,534,803,752 | **No** | 534,803,752 above |

Parakeet is **NOT used**: replacing tiny.en with it would exceed the cap by 534,803,752 parameters. The served total includes ASR regardless of any ASR eligibility exemption. These are arithmetic conclusions, not an organizer ruling about eligibility. The repository's [hard rule](CONTEXT.md#hard-rules) describes a generative-LM cap; the table also counts vision conservatively as requested. The Parakeet count is retained only to document the rejected alternative. V3 and the experimental U-Net are not additional deployed models. Multiple calls to the same Nemotron checkpoint do not add another set of parameters.

## Nemotron: sum every shard's tensor shapes

Pinned model revision: `a9904d24bcc1d289a1950fa9d2b978c47cf903b9`. Source: NVIDIA's [model.safetensors.index.json](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/blob/a9904d24bcc1d289a1950fa9d2b978c47cf903b9/model.safetensors.index.json), with a [saved exact copy](evidence/param_budget_2026-10-18/nemotron.model.safetensors.index.json).

The index does **not** provide one internally consistent full-checkpoint number:

- `metadata.total_parameters` = 31,577,937,344. This matches the core model **excluding MTP**, after excluding routing buffers.
- `metadata.total_size` = 65,842,365,568 bytes. Dividing by two gives 32,921,182,784, which disagrees with the actual tensor shapes.
- Across the actual [shard headers](evidence/param_budget_2026-10-18/nemotron_headers/), BF16 learned weights contain 32,913,263,168 elements and FP32 routing buffers contain 3,072 elements. Their payload offsets total 65,826,538,624 bytes, also different from the index's size metadata. The cause of that size-metadata discrepancy was not established; the count uses shapes instead.

Method: follow every shard named by the index, read its eight-byte safetensors header length and JSON header using HTTP byte ranges, then sum `math.prod(tensor['shape'])`. Every indexed tensor name and its shard mapping matches the collected headers. No weight payloads were downloaded or models instantiated for this count. The [range receipts](evidence/param_budget_2026-10-18/nemotron_header_receipts.json) save URLs, header hashes and byte ranges.

`e_score_correction_bias` is a registered [routing buffer in the implementation](https://raw.githubusercontent.com/huggingface/transformers/2fa1fdd5b27ae54bdcee0516848c7963393a5f5c/src/transformers/models/nemotron_h/modeling_nemotron_h.py), not a learned parameter. The full checkpoint has 32,913,266,240 stored tensor elements; subtracting those buffers gives **32,913,263,168 learned parameters**. Breaking that down: 31,577,937,344 core + 1,335,325,824 MTP. MTP remains in this budget even if a serving implementation ignores it; no pruning or exclusion is assumed. See [nemotron_counts.json](evidence/param_budget_2026-10-18/nemotron_counts.json).

## Served ASR: exact local faster-whisper tiny.en count

Counted directly from `ml/artifacts/asr-tiny.en/model.bin`, SHA-256
`1a5afae06a4db91c975c9a9d78be5cc110ee4ea022ad57d55492e4550e936b2a`.
The CTranslate2 binary header is version 6, `WhisperSpec` revision 3, with 148 stored
variables and one alias: `decoder/projection/weight` shares
`decoder/embeddings/weight` (51,864 × 384), counted once. FP16 storage and CPU int8
execution do not change the model's parameter count.

Summing each stored shape gives 37,764,873 elements: 37,764,864 floating-point
elements and nine integer configuration scalars. CTranslate2 packs Q/K/V biases,
inserting 384 fixed zero key-bias entries in each of 12 attention blocks (4 encoder
self-attention, 4 decoder self-attention, 4 decoder cross-attention). All 4,608
padding entries were checked to be zero. Remove padding and configuration scalars:
**37,760,256 unique model parameters**. This conservatively includes the 576,000
frozen sinusoidal encoder-position entries; excluding those gives **37,184,256
learned parameters**. The decoder's 172,032 learned position entries remain counted.
The served budget uses the larger 37,760,256 number, not the rounded “39M” name.

Even counting every stored ASR element, including padding and configuration, gives
32,954,742,699 total and 45,257,301 below 33B. The cap conclusion does not depend on
how the frozen ASR positions or conversion padding are classified.

Reproduction: read the little-endian binary using the installed
`ctranslate2/specs/model_spec.py:ModelSpec._serialize` layout: uint32 version,
uint16-length NUL-terminated spec name, uint32 revision and variable count; then
for each variable read its length-prefixed name, uint8 rank, uint32 dimensions,
uint8 dtype, uint32 payload byte count and payload. Sum products of dimensions;
skip payload bytes rather than loading the network. Read the alias table after
all variables and require EOF. Dtype IDs 0/4/5 are float32/float16/bfloat16.
`converters/transformers.py:WhisperLoader` inherits Bart attention fusion;
`specs/attention_spec.py` and `specs/common_spec.py` define the packed layers.
Whisper key projections have no learned bias; the inserted zero slice is the middle
384 entries of each self-attention fused bias and the first 384 entries of each
cross-attention K/V bias. The installed Transformers Whisper implementation freezes
encoder position embeddings. An independent meta-device instantiation with the
local tensor dimensions gives 37,760,256 total / 37,184,256 trainable parameters.
No model download or inference was needed for this audit.

The audit command below and its historical `totals.json` cover Nemotron, SegFormer
and the rejected Parakeet alternative; they predate this local ASR addition and do
not calculate the new served total. The exact arithmetic here is
`32_913_263_168 + 3_714_658 + 37_760_256 = 32_954_738_082`;
`33_000_000_000 - 32_954_738_082 = 45_261_918`.

## Parakeet: exact count from the checkpoint

Pinned model revision: `ae9ad07059c7c739ffaf932226a8fe64ae2620b0`. Source: NVIDIA's [parakeet-tdt-0.6b-v2.nemo](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2/blob/ae9ad07059c7c739ffaf932226a8fe64ae2620b0/parakeet-tdt-0.6b-v2.nemo). Attribution: NVIDIA; [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The checkpoint's [model_config.yaml](evidence/param_budget_2026-10-18/parakeet.model_config.yaml) identifies the FastConformer/RNNT model.

The `.nemo` file is a tar archive. Byte-range reads locate `./model_weights.ckpt`, inspect its ZIP directory, and fetch only `data.pkl`, which contains tensor names, shapes and storage references. A restricted metadata-only unpickler admits only `OrderedDict`, storage descriptors and a tensor-rebuild stub; it never loads tensor storage or executes model code. The [archive offset](evidence/param_budget_2026-10-18/parakeet_tar_member.json), [range receipts](evidence/param_budget_2026-10-18/parakeet_range_receipts.json), [raw checkpoint metadata](evidence/param_budget_2026-10-18/parakeet.model_weights.data.pkl) and [complete tensor inventory](evidence/param_budget_2026-10-18/parakeet_tensor_inventory.json) are saved.

Summing all stored tensor shapes gives 617,908,398 elements. Exclude 82,472 buffer elements: the featurizer window/filterbank plus BatchNorm running means, running variances and batch counters. The [NeMo preprocessing source](https://raw.githubusercontent.com/NVIDIA/NeMo/v2.4.0/nemo/collections/asr/parts/preprocessing/features.py) and [PyTorch BatchNorm source](https://raw.githubusercontent.com/pytorch/pytorch/v2.7.0/torch/nn/modules/batchnorm.py) declare these buffers. The remaining 651 parameter tensors contain **617,825,926 parameters**. The checkpoint's detached `requires_grad=False` flags are not used to decide which tensors are parameters. See [parakeet_counts.json](evidence/param_budget_2026-10-18/parakeet_counts.json).

## SegFormer and reproducibility

SegFormer's 3,714,658 count is the actual `sum(p.numel() for p in model.parameters())`, saved with the checkpoint identity in [v2_dev.json](ml/evidence/v3_2026-10-18/v2_dev.json). The experimental V3 has the same parameter count but is not served.

Run the [audit script](../scripts/ml/audit_parameter_budget.py) against the saved evidence without network or GPU:

```sh
PYTHONDONTWRITEBYTECODE=1 ml/.venv312/bin/python -m scripts.ml.audit_parameter_budget
```

`--fetch` optionally refreshes metadata from the same pinned revisions using bounded byte ranges. [totals.json](evidence/param_budget_2026-10-18/totals.json) contains the exact integer arithmetic. [Implementation-source declarations](evidence/param_budget_2026-10-18/buffer_classification_sources.json) and [audit tests](evidence/param_budget_2026-10-18/audit_tests.xml) document buffer classification and rejection of executable pickle globals, ignored ranges and unbounded downloads.
