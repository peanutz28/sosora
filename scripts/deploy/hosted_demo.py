"""Publish the explicitly requested cached demo; credentials never enter packages.

Run with ml/.venv312/bin/python. HF_TOKEN is read from ml/.env only for HF actions.
Vercel uses VERCEL_TOKEN from that file or the existing CLI login. No shell evaluation.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/evidence/hosted_demo_2026-10-18'
DEADLINE = datetime(2026, 10, 18, 10, 30, tzinfo=timezone.utc)
SPACE = 'peanutz28/sosora-command-demo'
PROJECT = 'sosora-command-demo'
MANUAL_HANDOFF = False


def deadline():
    if datetime.now(timezone.utc) >= DEADLINE and not MANUAL_HANDOFF:
        raise RuntimeError('06:30 AM ET hard stop reached; no further deployment work')


def save(name, payload):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(payload, indent=2) + '\n')


def secret(name):
    path = ROOT / 'ml/.env'
    for line in path.read_text().splitlines() if path.exists() else []:
        match = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
        if match and match[1] == name:
            value = match[2].strip()
            if value[:1] in {'"', "'"} and value[-1:] == value[:1]: value = value[1:-1]
            if value: return value
    raise RuntimeError(f'Missing {name} in ml/.env; do not paste credentials into chat')


def vercel_token():
    try:
        return secret('VERCEL_TOKEN'), 'ml/.env'
    except RuntimeError:
        # Read the user's authenticated CLI session in memory; never copy it to the repo.
        candidates = [Path.home()/'Library/Application Support/com.vercel.cli/auth.json',
                      Path.home()/'.local/share/com.vercel.cli/auth.json']
        for path in candidates:
            if path.exists():
                token = json.loads(path.read_text()).get('token')
                if token: return token, 'Vercel CLI login'
    raise RuntimeError('Run vercel login in your terminal, or save VERCEL_TOKEN in ml/.env')


def verify_vercel_auth():
    deadline()
    token, source = vercel_token()
    user = request('https://api.vercel.com/v2/user', token)['user']
    result = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
              'authenticated': True, 'username': user.get('username'), 'credential_source': source}
    save('vercel_auth.json', result)
    print(json.dumps(result))


def request(url, token=None, method='GET', data=None):
    headers = {'Accept': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    if data is not None: headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, headers=headers, method=method,
        data=json.dumps(data).encode() if data is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Do not echo requests, headers, credentials or server bodies to logs.
        raise RuntimeError(f'{method} {url.split("?")[0]} returned HTTP {exc.code}') from None


def hf_files():
    files = {'Dockerfile': ROOT/'backend/Dockerfile', '.dockerignore': ROOT/'backend/.dockerignore',
             'README.md': ROOT/'backend/SPACE_README.md', 'requirements.txt': ROOT/'backend/requirements.txt'}
    files.update({str(p.relative_to(ROOT/'backend')): p for p in (ROOT/'backend/app').rglob('*.py') if '__pycache__' not in p.parts})
    files.update({'data/'+name: ROOT/'backend/data'/name for name in ('graph.json','anchors.json','roads.geojson')})
    return files


def frontend_files():
    tracked = subprocess.check_output(['git','ls-files','-z','--','frontend'],cwd=ROOT).decode().split('\0')
    tracked += ['frontend/components/shell/HostedDemoBanner.tsx']
    omitted = {'next-env.d.ts', 'tsconfig.tsbuildinfo'}
    files = {}
    for name in sorted(set(filter(None,tracked))):
        path = ROOT/name; relative = path.relative_to(ROOT/'frontend')
        if relative.name in omitted or any(p.startswith('.') or p=='node_modules' for p in relative.parts): continue
        if path.is_file(): files[str(relative)] = path
    return files


def assert_public(files):
    for name,path in files.items():
        if any(part.startswith('.env') for part in Path(name).parts) or path.suffix in {'.db','.sqlite3','.pt','.safetensors'}:
            raise RuntimeError('Private/runtime artifact in deploy package')
        if path.stat().st_size < 2*1024**2:
            text = path.read_text(errors='ignore')
            if re.search(r'\b(?:hf_|nvapi-|sk-proj-)[A-Za-z0-9_-]{20,}|-----BEGIN (?:OPENSSH|RSA|PRIVATE).*KEY-----',text):
                raise RuntimeError('Credential-like content in deploy package')


def prepare():
    deadline()
    groups = {'hugging_face': hf_files(), 'vercel': frontend_files()}
    result = {'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'deadline_utc': DEADLINE.isoformat(),
              'space_id': SPACE, 'vercel_project': PROJECT, 'gpu_used': False, 'packages': {}}
    for kind, files in groups.items():
        assert_public(files)
        result['packages'][kind] = {name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for name,p in files.items()}
    save('package_manifest.json',result)
    print(json.dumps({'prepared': True, 'files': {k:len(v) for k,v in result['packages'].items()}}))


def deploy_hf(origin):
    deadline()
    from huggingface_hub import HfApi
    token = secret('HF_TOKEN')
    api = HfApi(token=token)
    identity = api.whoami()
    if identity['name'] != SPACE.split('/')[0]: raise RuntimeError('HF account does not match intended Space owner')
    api.create_repo(SPACE, repo_type='space', space_sdk='docker', space_hardware='cpu-basic', private=False, exist_ok=True)
    api.add_space_variable(SPACE, key='APP_CORS_ORIGINS', value=origin.rstrip('/'))
    files = hf_files(); assert_public(files)
    with tempfile.TemporaryDirectory(prefix='sosora-hf-public-') as staging:
        for name, source in files.items():
            target = Path(staging)/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
        deadline()
        commit = api.upload_folder(repo_id=SPACE, repo_type='space', folder_path=staging,
                                   commit_message='Deploy SOSora cached CPU demo; no live model or credentials')
    result = {'pushed_at_utc':datetime.now(timezone.utc).isoformat(),'space_id':SPACE,
              'public_url':'https://peanutz28-sosora-command-demo.hf.space',
              'repository_url':'https://huggingface.co/spaces/'+SPACE,'commit':commit.oid,
              'requested_hardware':'cpu-basic','cors_origins':origin.rstrip('/'),'credentials_uploaded':False}
    save('hf_deployment.json',result); print(json.dumps(result))


def hf_cors(origin):
    deadline()
    from huggingface_hub import HfApi
    HfApi(token=secret('HF_TOKEN')).add_space_variable(SPACE,key='APP_CORS_ORIGINS',value=origin.rstrip('/'))
    save('hf_cors.json',{'updated_at_utc':datetime.now(timezone.utc).isoformat(),'origins':origin.rstrip('/')})
    print('Hosted CORS origin configured.')


def vercel():
    deadline()
    # Do not publish a production frontend pointing at a missing backend.
    health=request('https://peanutz28-sosora-command-demo.hf.space/health')
    if health.get('demo_mode') is not True: raise RuntimeError('Hosted cached backend is not ready')
    token, _ = vercel_token(); base='https://api.vercel.com'
    projects=request(base+'/v9/projects?limit=100',token)['projects']
    project=next((p for p in projects if p['name']==PROJECT),None)
    if project is None:
        project=request(base+'/v11/projects',token,'POST',{'name':PROJECT,'framework':'nextjs',
            'buildCommand':'npm run build','installCommand':'npm ci'})
    env={'NEXT_PUBLIC_APP_API_URL':'https://peanutz28-sosora-command-demo.hf.space','NEXT_PUBLIC_HOSTED_DEMO':'true'}
    for key,value in env.items():
        request(base+f"/v10/projects/{project['id']}/env?upsert=true",token,'POST',
                {'key':key,'value':value,'type':'plain','target':['production','preview']})
    files=frontend_files(); assert_public(files)
    payload={'name':PROJECT,'project':project['id'],'target':'production',
             'files':[{'file':name,'data':base64.b64encode(p.read_bytes()).decode(),'encoding':'base64'} for name,p in files.items()],
             'projectSettings':{'framework':'nextjs','buildCommand':'npm run build','installCommand':'npm ci'},
             'meta':{'purpose':'SOSora hosted cached replay'}}
    deadline();deployment=request(base+'/v13/deployments',token,'POST',payload)
    result={k:deployment.get(k) for k in ('id','url','readyState','alias','createdAt')}
    result.update({'project_id':project['id'],'project_name':PROJECT,'public_environment':env,'submitted_at_utc':datetime.now(timezone.utc).isoformat()})
    save('vercel_deployment.json',result);print(json.dumps(result))


def connect_origins():
    deadline()
    deployed=json.loads((EVIDENCE/'vercel_deployment.json').read_text())
    state=request('https://api.vercel.com/v13/deployments/'+deployed['id'],vercel_token()[0])
    if state.get('readyState')!='READY': raise RuntimeError('Vercel deployment is not READY')
    aliases=state.get('alias') or []
    origins=list(dict.fromkeys('https://'+host for host in [*aliases,state['url']]))
    hf_cors(','.join(origins))
    # Fetch the production page without authentication to catch deployment protection.
    with urllib.request.urlopen(origins[0],timeout=45) as response:
        final_host=urllib.parse.urlparse(response.geturl()).hostname
        html=response.read().decode('utf-8', errors='replace')
        if response.status!=200 or final_host!=urllib.parse.urlparse(origins[0]).hostname or 'Hosted demo' not in html:
            raise RuntimeError('Frontend is not publicly accessible with the hosted disclosure')
    result={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'frontend_url':origins[0],
            'backend_url':'https://peanutz28-sosora-command-demo.hf.space','frontend_origins':origins,
            'websocket_url':'wss://peanutz28-sosora-command-demo.hf.space/ws/events'}
    save('public_urls.json',result);print(json.dumps(result))


def status():
    deadline()
    output={'checked_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        hf=request('https://huggingface.co/api/spaces/'+SPACE)
        output['hf']={'runtime':hf.get('runtime'),'host':hf.get('host'),'sha':hf.get('sha')}
    except RuntimeError as exc: output['hf']={'ready':False,'reason':str(exc)}
    deployment=EVIDENCE/'vercel_deployment.json'
    if deployment.exists():
        d=json.loads(deployment.read_text());v=request('https://api.vercel.com/v13/deployments/'+d['id'],vercel_token()[0])
        output['vercel']={k:v.get(k) for k in ('id','url','readyState','alias','errorCode','errorMessage')}
    save('deployment_status.json',output); print(json.dumps(output))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','hf','hf-cors','vercel-auth','vercel','connect','status'])
    parser.add_argument('--frontend-origin',default='https://sosora-command-demo.vercel.app')
    parser.add_argument('--manual-handoff',action='store_true',help='Human-run handoff only: explicitly allow commands after the agent deadline')
    args=parser.parse_args()
    MANUAL_HANDOFF=args.manual_handoff
    try:
        if args.action=='prepare': prepare()
        elif args.action=='hf': deploy_hf(args.frontend_origin)
        elif args.action=='hf-cors': hf_cors(args.frontend_origin)
        elif args.action=='vercel-auth': verify_vercel_auth()
        elif args.action=='vercel': vercel()
        elif args.action=='connect': connect_origins()
        else: status()
    except Exception as exc:
        if type(exc).__name__ in {'HfHubHTTPError','RepositoryNotFoundError','GatedRepoError'}:
            response=getattr(exc,'response',None)
            print(json.dumps({'action':args.action,'error_type':type(exc).__name__,'http_status':getattr(response,'status_code',None)}))
        elif isinstance(exc,RuntimeError): print(str(exc))
        else: print(json.dumps({'action':args.action,'error_type':type(exc).__name__}))
        raise SystemExit(1)
