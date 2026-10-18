"""Sequential live text-radio reliability: 20 beacon + 10 ambiguous reports.

Real OSM graph, simulated messages/incidents, no ASR/audio/network-radio timing.
Fresh seed before each request; seed and one-time graph loading excluded from E2E.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time
from fastapi.testclient import TestClient
from app.agent import RadioAgent
from app.factory import create_app
from app.routing import load_anchors,load_graph

NORTH={f'SOS-{i:03}' for i in range(1,6)}
WAY='549633356'

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def quantile(values):
    return {'n':len(values),'median_ms':statistics.median(values) if values else None,'p95_ms':sorted(values)[math.ceil(.95*len(values))-1] if values else None,'p95_method':'nearest rank ceil(0.95*n)','min_ms':min(values) if values else None,'max_ms':max(values) if values else None}
def summarize(rows):
    result={}
    for kind in ['beacon','ambiguous_responder']:
        group=[r for r in rows if r['kind']==kind]
        result[kind]={'attempts':len(group),'live_successes':sum(r['live_success'] for r in group),'correct_segment':sum(r.get('correct_segment',False) for r in group),'correct_ambiguity':sum(r.get('correct_ambiguity',False) for r in group),'five_cut_off_correct':sum(r.get('five_cut_off_correct',False) for r in group),'end_to_end':quantile([r['end_to_end_ms'] for r in group if 'end_to_end_ms' in r]),'agent_calls':quantile([t['latency_ms'] for r in group for t in r['turns']]),'agent_call_sum_per_request':quantile([sum(t['latency_ms'] for t in r['turns']) for r in group]),'end_to_end_successful_only':quantile([r['end_to_end_ms'] for r in group if r['live_success']])}
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    if os.getenv('DEMO_MODE','true').lower()!='false':raise SystemExit('Requires live mode')
    out=Path(a.output)
    if out.exists():raise SystemExit('Use a new output file')
    out.parent.mkdir(parents=True,exist_ok=True)
    graph=load_graph();expected={d['id'] for _,_,d in graph.edges(data=True) if str(d.get('way_id'))==WAY}
    assert expected,'Expected bridge absent from real graph'
    app=create_app(graph,load_anchors(),':memory:');original=RadioAgent.completion;turns=[]
    async def measured(self,messages):
        started=time.perf_counter();t={'index':len(turns)+1}
        try:
            result=await original(self,messages);t['tools']=[c['function']['name'] for c in result.get('tool_calls') or []];return result
        except Exception as exc:t['error_type']=type(exc).__name__;raise
        finally:t['latency_ms']=(time.perf_counter()-started)*1000;turns.append(t)
    RadioAgent.completion=measured;rows=[];started_utc=now()
    meta={'simulated_input':True,'cached_llm':False,'expected_way_id':WAY,'expected_edge_ids':sorted(expected),'expected_lost_incidents':sorted(NORTH),'order':'20 beacon then 10 ambiguous, sequential','timing_scope':'local in-process HTTP text /api/radio including live ML parse, agent loop, graph computation and serialization; excludes seed/loading, ASR/audio and physical radio transport','cache':'server prefix cache enabled, no flush between identical requests','failed_attempts':'retained in denominator; no benchmark retries; internal provider retries remain original application behavior'}
    def save():out.write_text(json.dumps({'started_utc':started_utc,'updated_utc':now(),'metadata':meta,'runs':rows,'summary':summarize(rows)},indent=2)+'\n')
    try:
        with TestClient(app) as client:
            for index in range(30):
                kind='beacon' if index<20 else 'ambiguous_responder';turns.clear();row={'run':index+1,'kind':kind,'turns':[],'live_success':False,'started_utc':now()}
                try:
                    before=time.perf_counter();seed_response=client.post('/api/radio/demo/seed');seed_response.raise_for_status();seed=seed_response.json();row['seed_ms']=(time.perf_counter()-before)*1000
                    assert len(seed['state']['incidents'])==9 and all(i['reachable'] for i in seed['state']['incidents'])
                    payload={'message':seed['hero_message'],'source_type':'beacon' if kind=='beacon' else 'responder_radio','unit':'beacon-ww-bridge' if kind=='beacon' else 'Engine 4'}
                    if kind=='beacon':payload.update(seed['beacon_position'])
                    before=time.perf_counter()
                    try:response=client.post('/api/radio',json=payload)
                    finally:row['end_to_end_ms']=(time.perf_counter()-before)*1000
                    row['http_status']=response.status_code;response.raise_for_status();body=response.json();assessment=body.get('assessment') or {};events=[e for e in app.state.engine.events if e['kind'].startswith('agent_')]
                    closed=set(app.state.engine.closed_ids);lost={i['id'] for i in body['state']['incidents'] if i.get('reachable') is False};live=body['parse'].get('parse_mode')=='nemotron_lightning' and bool(turns) and not any('error_type' in t for t in turns) and not any(e['kind']=='agent_error' or e.get('call_id')=='fallback' for e in events)
                    row.update(parse=body['parse'],assessment=assessment,closed_segment_ids=sorted(closed),lost_incident_ids=sorted(lost),events=events)
                    if kind=='beacon':
                        row['correct_segment']=closed==expected
                        row['five_cut_off_correct']=lost==NORTH and set(assessment.get('affected_incident_ids',[]))==NORTH
                        row['live_success']=live and row['correct_segment'] and row['five_cut_off_correct']
                    else:
                        ambiguity_observed=any(e['kind']=='agent_tool_result' and e.get('tool')=='find_segments' and e.get('result',{}).get('needs_human_review') is True for e in events)
                        row['correct_ambiguity']=ambiguity_observed and assessment.get('needs_human_review') is True and not closed and not lost and assessment.get('affected_incident_ids')==[]
                        row['live_success']=live and row['correct_ambiguity']
                except Exception as exc:row['error_type']=type(exc).__name__
                row['turns']=list(turns);rows.append(row);save();print(json.dumps({k:row[k] for k in ['run','kind','live_success']}),flush=True)
    finally:RadioAgent.completion=original
    save()
if __name__=='__main__':main()
