# Optional rejection-sampling LoRA feasibility attempt

2026-10-18: stopped at the feasibility gate because infrastructure setup failed.
This is an inconclusive architecture result, not evidence that NemotronH cannot
train or serve LoRA adapters. No fine-tuned model or improvement is claimed.

The live Brev quote was shown before launch: a separate Nebius H100 80 GB at
$5.40/hour compute, plus $0.12264/GB-month disk. Only `sosora-lora-f`
(`7va41egen`) was created and operated on. The filming H100
`sosora-lightning-vllm` was not modified. The attempt began at 04:29:12 ET;
termination was requested around 04:35 ET, within the 30-minute gate and well
before the 09:00 ET cutoff. These rates are quotes, not an invoice.

## Feasibility results

| Required gate | Result |
| --- | --- |
| Full Lightning single-GPU LoRA training | Unconfirmed; zero training steps |
| vLLM v0.27.1 serves the resulting adapter | Unconfirmed; no adapter loaded or inference request made |

NVIDIA publishes a [single-GPU AutoModel LoRA recipe](https://github.com/NVIDIA-NeMo/Nemotron/blob/main/usage-cookbook/Nemotron-3.5-Lightning/dgx-station-recipes/lora.md)
for a larger B300 GPU. It excludes Mamba output projections. The
[vLLM v0.27.1 NemotronH implementation](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/model_executor/models/nemotron_h.py)
declares `SupportsLoRA` and adapter mappings. Those source findings do not
substitute for a full-checkpoint training and adapter-serving smoke test.

The new GPU was reachable and identified as H100 80GB HBM3. Initial SSH startup
failed, followed by a connection reset during the official
`nvcr.io/nvidia/nemo-automodel:26.08` pull. The retried `brev exec` runtime
command ended with `unexpected EOF` and exit status 1. A direct SSH image pull
retry was still incomplete when this optional experiment was terminated.
Brev supplied a 116 GiB root filesystem despite the 200 GB disk request.
No out-of-memory or architectural incompatibility was established.

The ordinary stop request failed because Brev still marked the instance
`BUILDING`. Deletion of this disposable instance was requested instead.
Deletion was verified at **04:42:49 ET**, before both the 30-minute feasibility
deadline and the 09:00 ET hard stop. The instance is absent from the live Brev
catalog; the filming H100 remains running and healthy. The local guard was
disarmed after this verification. See the
[lifecycle receipt](evidence/lora_f_2026-10-18/lifecycle.json).

## Training and evaluation

No synthetic training rows, accepted trajectories, SFT adapter, or evaluation
runs were produced. The requested comparison therefore has no scores:

| Arm | Validation repetitions | Test repetitions |
| --- | --- | --- |
| Base + grounded_v2 | 0/3 | 0/3 |
| LoRA + grounded_v2 | 0/3 | 0/3 |

**Test has been used previously** in the existing prompt experiments and
ablation. No additional test execution or selection occurred in this attempt.
README and video claims were not changed.

The intended conditional protocol (new Gym scenarios only, verifier-passing
grounded_v2 trajectories only, three validation runs followed by three test
runs per arm using ablation settings) is recorded in
[protocol.json](evidence/lora_f_2026-10-18/protocol.json).
Observed failure excerpts are in
[failure_excerpt.txt](evidence/lora_f_2026-10-18/failure_excerpt.txt).
