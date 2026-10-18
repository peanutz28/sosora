#!/usr/bin/env bash
# Admission gate for the frozen runner. This performs metadata checks, never a probe generation.
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${GYM_PYTHON:?Set the pinned official Gym runtime Python}"
: "${GYM_OFFICIAL:?Set the pinned official Gym source directory}"
: "${LLM_BASE_URL:?Set the private serving base URL}"
: "${LLM_API_KEY:?Set the private serving token}"
: "${LLM_MODEL:?Set the sealed model ID}"
exam_output=${1:?Pass a committed seal directory}
exam_commit=${2:?Pass its seal commit}
export LLM_PROVIDER=redhat_vllm
export PYTHONPATH="$PWD:$GYM_OFFICIAL"
"$GYM_PYTHON" - "$exam_output" "$exam_commit" <<'PY'
import datetime as dt
import json
import os
from pathlib import Path
import sys
import httpx
from scripts.vllm.run_fresh_exam2 import STOP, verify_seal
out=Path(sys.argv[1]).resolve()
assert not (out/'opened.json').exists(), 'Existing exam cannot be reopened'
seal=verify_seal(out,sys.argv[2])
assert dt.datetime.now(dt.timezone.utc)<STOP, 'Evaluation cutoff passed'
assert os.environ['LLM_MODEL']==seal['model']
base=os.environ['LLM_BASE_URL'].rstrip('/')
headers={'Authorization':'Bearer '+os.environ['LLM_API_KEY']}
with httpx.Client(timeout=15) as client:
    health=client.get(base.removesuffix('/v1')+'/health',headers=headers)
    health.raise_for_status()
    models=client.get(base+'/models',headers=headers)
    models.raise_for_status()
    ids=[item['id'] for item in models.json()['data']]
    assert seal['model'] in ids
(out/'admission.json').write_text(json.dumps({'checked_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'seal_commit':sys.argv[2],'health_status':health.status_code,'served_models':ids,'metadata_only_no_generation':True},indent=2)+'\n')
PY
exec "$GYM_PYTHON" scripts/vllm/run_fresh_exam2.py --output "$exam_output" --seal-commit "$exam_commit"
