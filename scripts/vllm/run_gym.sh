#!/usr/bin/env bash
# Run from repository root after exporting LLM_BASE_URL/MODEL/API_KEY.
# The existing runner, tasks, policies and official verifier remain unchanged.
set -euo pipefail
: "${LLM_BASE_URL:?Set vLLM base URL privately}"
: "${LLM_API_KEY:?Set vLLM token privately}"
: "${GYM_PYTHON:?Set official Gym runtime Python executable}"
: "${GYM_OFFICIAL:?Set pinned official Gym source directory}"
: "${GYM_OUTPUT:?Set a fresh dated evidence directory}"
export LLM_PROVIDER=redhat_vllm
export LLM_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
export PYTHONPATH="$PWD:$GYM_OFFICIAL"
for split in validation test; do
  for policy in baseline evidence_first; do
    "$GYM_PYTHON" -m ml.nemo_gym.evaluate_agent \
      --split "$split" --policy "$policy" --limit 14 \
      --max-turns 12 --max-seconds 14400 \
      --output "$GYM_OUTPUT/${split}_${policy}"
  done
done
