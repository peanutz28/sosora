"""Exercise a cached hosted backend over HTTP and a real WebSocket connection."""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import time
from urllib.parse import urlparse
import httpx
from websockets.sync.client import connect

DEADLINE = datetime(2026,10,18,10,30,tzinfo=timezone.utc)


def main(base, origin, output, manual_handoff=False, resumed_by_user=False):
    allow_after_deadline=manual_handoff or resumed_by_user
    if datetime.now(timezone.utc)>=DEADLINE and not allow_after_deadline:
        raise RuntimeError('06:30 AM ET hard stop reached')
    base=base.rstrip('/'); ws=base.replace('https://','wss://').replace('http://','ws://')+'/ws/events'
    local=urlparse(base).hostname in {'localhost','127.0.0.1'}
    evidence={'started_at_utc':datetime.now(timezone.utc).isoformat(),'base_url':base,'origin':origin,
              'scope':'isolated hosted entrypoint, local only' if local else 'public hosted backend',
              'resumed_by_user':resumed_by_user,'checks':{},'requests':[],'websocket_frames':[]}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        content=(json.dumps(evidence,indent=2)+'\n').encode()
        output.write_bytes(gzip.compress(content,mtime=0) if output.suffix=='.gz' else content)
    def post(client,path,body=None):
        if datetime.now(timezone.utc)>=DEADLINE and not allow_after_deadline:raise RuntimeError('Hard stop reached')
        tick=time.perf_counter();r=client.post(path,json=body or {});r.raise_for_status();data=r.json()
        evidence['requests'].append({'path':path,'status':r.status_code,'http_seconds':time.perf_counter()-tick,'response':data});save();return data
    def next_state(socket,predicate):
        for _ in range(150):
            frame=json.loads(socket.recv(timeout=30));evidence['websocket_frames'].append(frame)
            if frame.get('type')=='state' and predicate(frame['state']):return frame['state']
        raise AssertionError('Expected WebSocket state not received')
    def cached(data):
        runtime=data['agent_runtime'];assert runtime['cached'] is True
        assert runtime.get('model_id') is None and runtime.get('last_call_latency_ms') is None
    try:
        with httpx.Client(base_url=base,timeout=60,follow_redirects=True) as client:
            health=client.get('/health');health.raise_for_status();assert health.json()['demo_mode'] is True
            evidence['health']=health.json()
            preflight=client.options('/api/radio/demo/seed',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
            assert preflight.status_code==200 and preflight.headers['access-control-allow-origin']==origin
            evidence['checks']['cors']=True
            with connect(ws,origin=origin,open_timeout=30,max_size=8*1024**2,ping_interval=30,ping_timeout=120) as socket:
                first=json.loads(socket.recv(timeout=30));assert first['type']=='state'
                evidence['websocket_frames'].append(first);evidence['checks']['websocket_initial_state']=True
                seed=post(client,'/api/radio/demo/seed')
                assert len(seed['state']['incidents'])==9 and all(i['reachable'] for i in seed['state']['incidents'])
                next_state(socket,lambda state:state['revision']>=seed['state']['revision'] and len(state['incidents'])==9)
                evidence['checks']['seed']=True
                hero=post(client,'/api/radio',{'message':seed['hero_message'],'source_type':'beacon',**seed['beacon_position']})
                cached(hero);assert hero['assessment']['affected_incident_ids']==[f'SOS-{i:03}' for i in range(1,6)]
                next_state(socket,lambda state:sum(i.get('reachable') is False for i in state['incidents'])==5)
                evidence['checks']['beacon_hero_and_websocket_broadcast']=True
                dot=post(client,'/api/radio',{'message':seed['open_report'],'unit':'DOT'})
                cached(dot);assert len(client.get('/api/radio/status').json()['closed_edge_ids'])==2
                evidence['checks']['dot_open_keeps_closure']=True
                seed=post(client,'/api/radio/demo/seed')
                responder=post(client,'/api/radio',{'message':seed['hero_message'],'unit':'Engine 4'})
                cached(responder);assert responder['assessment']['needs_human_review'] is True
                assert client.get('/api/radio/status').json()['closed_edge_ids']==[]
                confirm=post(client,'/api/radio/confirm',{'radio_id':responder['radio_id'],**seed['beacon_position']})
                cached(confirm);assert confirm['assessment']['affected_incident_ids']==[f'SOS-{i:03}' for i in range(1,6)]
                evidence['checks']['responder_review_and_confirm']=True
                assert socket.ping().wait(timeout=30), 'WebSocket heartbeat failed after the complete flow'
                evidence['checks']['websocket_alive_after_complete_flow']=True
        evidence['passed']=True
    except Exception as exc:
        evidence['passed']=False;evidence['failure']={'type':type(exc).__name__,'message':str(exc)};raise
    finally:
        evidence['finished_at_utc']=datetime.now(timezone.utc).isoformat();save()
    print(json.dumps({'scope':evidence['scope'],'passed':True,'checks':evidence['checks']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',required=True);parser.add_argument('--origin',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--manual-handoff',action='store_true')
    parser.add_argument('--resumed-by-user',action='store_true',help='New smoke run explicitly requested by the user after the original cutoff')
    args=parser.parse_args();main(args.base_url,args.origin,args.output,args.manual_handoff,args.resumed_by_user)
