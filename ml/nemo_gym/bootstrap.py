"""Install only the genuine Gym core needed by this resource server.
Full Gym CLI/agent orchestration is a separate upstream installation.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
import venv

COMMIT='3045a793346a31291d7ea4ae6af3f94a35036ce5'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime-dir',default='ml/artifacts/nemo_gym_runtime')
    args=parser.parse_args()
    if sys.version_info < (3,13,14):raise SystemExit('Use Python >=3.13.14 (validated here with 3.14.3)')
    root=Path(args.runtime_dir).resolve(); root.mkdir(parents=True,exist_ok=True)
    official=root/'official';official.mkdir(exist_ok=True)
    tree=json.loads(urllib.request.urlopen(f'https://api.github.com/repos/NVIDIA-NeMo/Gym/git/trees/{COMMIT}?recursive=1',timeout=30).read())
    if tree.get('sha')!=COMMIT or tree.get('truncated'):raise RuntimeError('Unexpected upstream source tree')
    files=[r for r in tree['tree'] if r['type']=='blob' and (r['path'].startswith('nemo_gym/') or r['path'] in {'LICENSE','pyproject.toml'})]
    def fetch(row):
        data=urllib.request.urlopen(f'https://raw.githubusercontent.com/NVIDIA-NeMo/Gym/{COMMIT}/'+row['path'],timeout=30).read()
        digest=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if digest!=row['sha']:raise RuntimeError('Git blob mismatch: '+row['path'])
        path=official/row['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,files))
    if not (root/'venv/bin/python').exists():venv.EnvBuilder(with_pip=True).create(root/'venv')
    subprocess.run([str(root/'venv/bin/python'),'-m','pip','install','--no-cache-dir','-r',str(Path(__file__).with_name('requirements-core.lock'))],check=True)
    (root/'source_provenance.json').write_text(json.dumps({'repository':'https://github.com/NVIDIA-NeMo/Gym','tag':'v0.6.0','commit':COMMIT,'files_verified_against_git_blobs':len(files),'installation_scope':'resource-server core; not full Gym CLI dependencies'},indent=2))
    print('Core ready. Set PYTHONPATH to repository root plus '+str(official))
if __name__=='__main__':main()
