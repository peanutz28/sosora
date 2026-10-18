"""A failed admission step must prevent launching the evaluator."""
import os
from pathlib import Path
import subprocess
import pytest

@pytest.mark.parametrize('admission_exit,expected_invocations',[(1,1),(0,2)])
def test_launch_shell_stops_after_failed_admission(tmp_path,admission_exit,expected_invocations):
    python=tmp_path/'fake-python'
    calls=tmp_path/'calls'
    python.write_text('#!/bin/sh\nprintf "invocation\\n" >> "$CALLS"\nif [ "$1" = "-" ]; then cat >/dev/null; exit "$ADMISSION_EXIT"; fi\nexit 0\n')
    python.chmod(0o755)
    env={**os.environ,'GYM_PYTHON':str(python),'GYM_OFFICIAL':str(tmp_path),'LLM_BASE_URL':'http://unused.invalid/v1','LLM_MODEL':'fake','LLM_API_KEY':'fake-never-sent','CALLS':str(calls),'ADMISSION_EXIT':str(admission_exit)}
    result=subprocess.run(['bash','scripts/vllm/launch_fresh_exam2.sh',str(tmp_path/'exam'),'fake-commit'],env=env,capture_output=True)
    assert result.returncode==admission_exit
    assert len(calls.read_text().splitlines())==expected_invocations
