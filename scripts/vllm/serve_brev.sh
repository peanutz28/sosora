#!/usr/bin/env bash
# Execute on the Brev H100 host with: brev exec INSTANCE @scripts/vllm/serve_brev.sh
set -euo pipefail
umask 077
command -v docker >/dev/null
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
# Restore the tmpfs target before following a retained cache symlink on resume.
mkdir -p "$HOME/.config/sosora" /dev/shm/sosora-hf
mkdir -p "$HOME/.cache/huggingface"
if [ ! -s "$HOME/.config/sosora/vllm.env" ]; then
  python3 - <<'PY'
from pathlib import Path
import secrets
p = Path.home() / '.config/sosora/vllm.env'
p.write_text('VLLM_API_KEY=' + secrets.token_urlsafe(32) + '\n')
p.chmod(0o600)
PY
fi
# Upstream vLLM image, not claimed to be a Red Hat distribution.
# BF16 single-H100 recipe from NVIDIA's model card; shorter context for this workload.
sudo docker pull vllm/vllm-openai:v0.27.1
# Brev supplied a 120GB disk despite the 200GB request. Keep the BF16 weights
# off that disk. The VM has 200GiB RAM; /dev/shm provides ~99GiB for this cache.
# This cache is intentionally ephemeral and must be re-downloaded after stop.
mkdir -p /dev/shm/sosora-hf
if [ -d "$HOME/.cache/huggingface" ] && [ ! -L "$HOME/.cache/huggingface" ]; then
  if [ -z "$(find "$HOME/.cache/huggingface" -mindepth 1 -print -quit)" ]; then
    rmdir "$HOME/.cache/huggingface"
    ln -s /dev/shm/sosora-hf "$HOME/.cache/huggingface"
  else
    echo "Existing disk cache found; move it explicitly before deploying on a small disk." >&2
    exit 1
  fi
fi
if sudo docker container inspect sosora-vllm >/dev/null 2>&1; then
  if [ "$(sudo docker inspect -f '{{.State.Running}}' sosora-vllm)" != true ]; then
    sudo docker start sosora-vllm
  fi
  echo "Existing sosora-vllm container retained."
  exit 0
fi
sudo docker run -d --name sosora-vllm --gpus all --ipc=host \
  --restart unless-stopped -p 8000:8000 \
  --env-file "$HOME/.config/sosora/vllm.env" -e HF_XET_CHUNK_CACHE_SIZE_BYTES=0 \
  -e VLLM_ENFORCE_STRICT_TOOL_CALLING=false \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  vllm/vllm-openai:v0.27.1 \
  --model nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 \
  --served-model-name nvidia/nemotron-3.5-lightning-30b-a3b \
  --host 0.0.0.0 --port 8000 --dtype bfloat16 \
  --max-model-len 16384 --max-num-seqs 32 --gpu-memory-utilization 0.90 \
  --enable-prefix-caching --async-scheduling \
  --mamba-backend flashinfer --mamba-ssm-cache-dtype float16 \
  --enable-mamba-cache-stochastic-rounding --mamba-cache-philox-rounds 5 \
  --reasoning-parser nemotron_v3 --tool-call-parser qwen3_coder \
  --enable-auto-tool-choice \
  --default-chat-template-kwargs '{"enable_thinking":false}'
