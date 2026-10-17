"""Run the frozen local vision API with optional private provider settings."""
import argparse
import os
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_SETTINGS = {'NVIDIA_API_KEY', 'LLM_PROVIDER', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'}


def load_provider_settings(path: Path):
    """Read dotenv values as data; never execute shell expressions or print secrets."""
    if not path.exists():
        return
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip().removeprefix('export ').lstrip()
        if not line or line.startswith('#'):
            continue
        name, separator, value = line.partition('=')
        if not separator:
            raise ValueError(f'Expected a setting assignment on line {number}')
        name = name.strip()
        if name not in PROVIDER_SETTINGS:
            continue
        try:
            parts = shlex.split(value, comments=True, posix=True)
        except ValueError:
            raise ValueError(f'Invalid quoted setting on line {number}') from None
        if len(parts) > 1:
            raise ValueError(f'Expected one setting value on line {number}')
        os.environ[name] = parts[0] if parts else ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / 'ml/.env')
    parser.add_argument('--port', type=int, default=8002)
    args = parser.parse_args()
    try:
        load_provider_settings(args.env_file)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Cannot load private provider settings ({type(exc).__name__}).\n')
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    defaults = {
        'HF_HOME': str(ROOT / 'ml/.cache/huggingface'),
        'HF_HUB_OFFLINE': '1',
        'OMP_NUM_THREADS': '2',
        'VECLIB_MAXIMUM_THREADS': '2',
        'VISION_MODEL': 'ml/artifacts/sn8_native_cpu_v2/model',
        'ML_METRICS_PATH': 'ml/artifacts/sn8_native_cpu_v2_evaluated',
        'ML_IMAGE_MANIFEST': 'data/manifests/native_demo.json',
    }
    for name, value in defaults.items():
        os.environ.setdefault(name, value)
    import uvicorn
    uvicorn.run('ml.inference.app:app', host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
