#!/usr/bin/env bash
# Run only on the separately provisioned sosora-lora-f instance.
set -euo pipefail
umask 077
mkdir -p "$HOME/lora-f"
exec > >(tee "$HOME/lora-f/runtime.log") 2>&1
date -u
nvidia-smi --query-gpu=name,uuid,memory.total,driver_version --format=csv
df -h /
sudo docker pull nvcr.io/nvidia/nemo-automodel:26.08
sudo docker run --rm --gpus all --ipc=host --entrypoint python3 \
  nvcr.io/nvidia/nemo-automodel:26.08 -c \
  'import torch, nemo_automodel; from nemo_automodel.components._peft.lora import PeftConfig; print(torch.cuda.get_device_name()); print(nemo_automodel.__version__); print(PeftConfig)'
