#!/usr/bin/env bash
# Run from any directory. Loads no secrets; source .env.vllm privately first.
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
export BACKEND_URL=${BACKEND_URL:-http://127.0.0.1:8000}
export FRONTEND_URL=${FRONTEND_URL:-http://127.0.0.1:3000}
export ASR_BASE_URL=${ASR_BASE_URL:-http://127.0.0.1:8003}
exec "${PYTHON:-$ROOT/ml/.venv312/bin/python}" "$ROOT/scripts/demo/preflight.py"
