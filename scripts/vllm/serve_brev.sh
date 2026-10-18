#!/usr/bin/env bash
# Execute on the Brev H100 host with: brev exec INSTANCE @scripts/vllm/serve_brev.sh
set -euo pipefail
umask 077
command -v docker >/dev/null
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
mkdir -p "$HOME/.config/sosora" "$HOME/.cache/huggingface"
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
sudo docker run -d --name sosora-vllm --gpus all --ipc=host \
  --restart unless-stopped -p 8000:8000 \
  --env-file "$HOME/.config/sosora/vllm.env" \
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
