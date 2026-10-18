"""Three sequential live API rehearsals on an isolated backend; retains failures."""
import json, os, time
from pathlib import Path
import httpx
base=os.environ.get('BACKEND_URL','http://127.0.0.1:18001')
rows=[]
with httpx.Client(base_url=base, timeout=180) as c:
    def post(path, payload=None):
        r=c.post(path,json=payload);r.raise_for_status();return r.json()
    def counts(expected):
        state=c.get('/api/state').json()
        lost=sorted(i['id'] for i in state['incidents'] if i['reachable'] is False)
        assert lost==['SOS-%03d'%i for i in range(1,expected+1)],lost
        reachable=sum(i['reachable'] is True for i in state['incidents'])
        assert len(state['incidents'])==9 and reachable==9-expected
        physical={road['id'].rsplit(':',1)[0] for road in state['closures']}
        assert len(physical)==(1 if expected else 0)
        return {'cut_off':len(lost),'reachable':reachable,'physical_closures':len(physical)}
    for take in range(1,4):
        row={'take':take,'beats':[]}; rows.append(row)
        try:
            for beat in ['beacon','dot','ambiguity','confirm','water','imagery','acknowledge']:
                start=time.monotonic()
                if beat in ('beacon','ambiguity','water'):
                    seed=post('/api/radio/demo/seed'); assert seed['seeded']==9; counts(0)
                if beat=='beacon': out=post('/api/radio',{'message':seed['hero_message'],'source_type':'beacon',**seed['beacon_position']})
                elif beat=='dot': out=post('/api/radio',{'message':seed['open_report'],'source_type':'responder_radio','unit':'DOT'})
                elif beat=='ambiguity':
                    out=post('/api/radio',{'message':seed['hero_message'],'source_type':'responder_radio','unit':'Engine 4'}); radio_id=out['radio_id']; assert out['assessment']['needs_human_review']
                elif beat=='confirm':out=post('/api/radio/confirm',{'radio_id':radio_id,**seed['beacon_position']})
                elif beat=='water':out=post('/api/beacon/beacon-ww-bridge/reading',{'water_level_cm':45})
                elif beat=='imagery':
                    out=post('/api/radio/demo/imagery',{'offline':True}); assert out['state']['imagery']['offline']; counts(5); post('/api/radio/demo/imagery',{'offline':False})
                else:out=post('/api/review',{'decision':'acknowledged'})
                if beat in ('beacon','dot','ambiguity','confirm','water'):
                    assert out['agent_runtime']['cached'] is False
                    assert out['agent_runtime']['model_id']=='nvidia/nemotron-3.5-lightning-30b-a3b'
                result=counts(0 if beat=='ambiguity' else 5)
                state=out.get('state',out)
                errors=[e for e in state.get('events',[]) if e.get('kind')=='agent_error']
                assert not errors,errors
                row['beats'].append({'beat':beat,'seconds':round(time.monotonic()-start,3),**result,'assessment':out.get('assessment'),'runtime':out.get('agent_runtime'),'tool_errors':[e.get('result') for e in state.get('events',[]) if isinstance(e.get('result'),dict) and e['result'].get('error')] if isinstance(state,dict) else []})
                print('PASS take',take,beat,result,flush=True)
            row['passed']=True
        except Exception as exc:
            row['passed']=False;row['error']=str(exc);print('FAIL take',take,type(exc).__name__,str(exc),flush=True)
        Path('docs/evidence/filming_2026-10-18/live_runs.json').write_text(json.dumps(rows,indent=2))
assert all(r['passed'] for r in rows)
