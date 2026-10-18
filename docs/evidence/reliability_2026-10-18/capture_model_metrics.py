import datetime,json,os,re,sys
from pathlib import Path
import httpx
base=os.environ['LLM_BASE_URL'].rstrip('/');url=base.rsplit('/v1',1)[0]+'/metrics'
r=httpx.get(url,headers={'Authorization':'Bearer '+os.environ['LLM_API_KEY']},timeout=10);r.raise_for_status()
metrics={}
for name in ['vllm:num_requests_running','vllm:num_requests_waiting','vllm:request_success_total']:
 rows=[line for line in r.text.splitlines() if line.startswith(name+'{') or line.startswith(name+' ')]
 metrics[name]={'samples':rows,'sum':sum(float(line.rsplit(' ',1)[-1]) for line in rows)}
Path(sys.argv[1]).write_text(json.dumps({'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metrics':metrics},indent=2)+'\n')
print({k:v['sum'] for k,v in metrics.items()})
