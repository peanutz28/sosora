from __future__ import annotations
from typing import Optional
"""SOSora prototype API. All incidents and closures are SIMULATED; never for emergency use."""
import os, sqlite3, json, uuid, heapq
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from backend.demo_data import ensure_demo, reset_demo
from backend.ordering import sort_incidents
from backend.road_network import Report, analyze_network, catalog, load_network, serialize_report
from backend.weather import current_conditions, helene_track

ROOT=Path(__file__).resolve().parents[1]
_GRAPHML=ROOT/'swannanoa_roads.graphml'
ROAD_NETWORK=load_network(ROOT/'frontend'/'roads.geojson', _GRAPHML if _GRAPHML.exists() else None)
DB=Path(os.getenv('SOSORA_DB',str(ROOT/'sosora.sqlite3')))
app=FastAPI(title='SOSora demo API',version='0.1.0',description='Simulation only; not an emergency service')

@contextmanager
def db():
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    try:
        yield con
        con.commit()
    finally: con.close()

def now(): return datetime.now(timezone.utc).isoformat()

SEED=[('SOS-1042','critical','Family stranded by floodwater','Swannanoa River Road',4,35.6042,-82.4379,'Received','Four people trapped upstairs. Water rising.'),('SOS-1039','high','Medical evacuation requested','Old Fort Highway',2,35.608,-82.475,'Acknowledged','Two people need medical evacuation.'),('SOS-1036','high','Residents isolated by rising water','Broad River Road',7,35.576,-82.511,'Received','Seven residents cannot cross flooded road.')]

# Small EXPLICITLY SIMULATED road network. Nodes are geographic coordinates, edges are demonstration links,
# NOT verified roads, road safety, travel times or OSM-based routing.
NODES={'base':[35.592,-82.524],'a':[35.594,-82.510],'b':[35.596,-82.496],'bridge':[35.6003,-82.475],'c':[35.603,-82.457],'target':[35.6042,-82.4379],'south1':[35.586,-82.510],'south2':[35.578,-82.485],'south3':[35.586,-82.462]}
EDGES=[('base','a'),('a','b'),('b','bridge'),('bridge','c'),('c','target'),('base','south1'),('south1','south2'),('south2','south3'),('south3','target')]
CLOSURE='b:bridge'
def edgeid(a,b): return ':'.join(sorted([a,b]))
def km(a,b):
    from math import radians,sin,cos,asin,sqrt
    p1,l1=NODES[a];p2,l2=NODES[b];dp=radians(p2-p1);dl=radians(l2-l1)
    return 12742*asin(sqrt(sin(dp/2)**2+cos(radians(p1))*cos(radians(p2))*sin(dl/2)**2))

def pathfind(closed):
    adj={n:[] for n in NODES}
    for a,b in EDGES:
        if edgeid(a,b) in closed:continue
        d=km(a,b);adj[a].append((b,d));adj[b].append((a,d))
    q=[(0,'base',[])];seen=set()
    while q:
        dist,node,path=heapq.heappop(q)
        if node in seen:continue
        seen.add(node);path=path+[node]
        if node=='target':return {'available':True,'coordinates':[[NODES[x][1],NODES[x][0]] for x in path], 'distance_km':round(dist,2),'node_path':path,'source':'simulated_graph','safety_verified':False}
        for nxt,w in adj[node]:
            if nxt not in seen:heapq.heappush(q,(dist+w,nxt,path))
    return {'available':False,'coordinates':[],'distance_km':None,'node_path':[],'source':'simulated_graph','safety_verified':False}

def setup():
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, priority TEXT, description TEXT, place TEXT, people INTEGER, lat REAL, lng REAL, status TEXT, message TEXT, created_at TEXT, source TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, kind TEXT, message TEXT)')
        names={row[1] for row in c.execute('PRAGMA table_info(incidents)')}
        if 'kind' not in names:c.execute("ALTER TABLE incidents ADD COLUMN kind TEXT DEFAULT 'sos'")
        if 'updated_at' not in names:c.execute('ALTER TABLE incidents ADD COLUMN updated_at TEXT')
        if not c.execute('SELECT 1 FROM incidents LIMIT 1').fetchone():
            for x in SEED:c.execute('INSERT INTO incidents (id,priority,description,place,people,lat,lng,status,message,created_at,source,kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(*x,now(),'seeded_simulation','sos'))
        c.execute('CREATE TABLE IF NOT EXISTS deliveries (client_id TEXT PRIMARY KEY, transport TEXT NOT NULL, gateway_id TEXT, gateway_received_at TEXT, center_received_at TEXT, created_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS road_reports (segment_id TEXT PRIMARY KEY, condition TEXT NOT NULL, source TEXT NOT NULL, evidence TEXT NOT NULL, verification TEXT NOT NULL, reported_at TEXT NOT NULL, updated_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS road_report_history (id INTEGER PRIMARY KEY AUTOINCREMENT, segment_id TEXT NOT NULL, condition TEXT NOT NULL, source TEXT NOT NULL, evidence TEXT NOT NULL, verification TEXT NOT NULL, recorded_at TEXT NOT NULL)')
        if not c.execute("SELECT 1 FROM state WHERE key='stage'").fetchone():c.execute("INSERT INTO state VALUES ('stage','0')")
        ensure_demo(c)

def stage(c):return int(c.execute("SELECT value FROM state WHERE key='stage'").fetchone()[0])
def log(c,kind,msg):c.execute('INSERT INTO events (at,kind,message) VALUES (?,?,?)',(now(),kind,msg))

def road_rows(c):
    return [Report(segment_id=r['segment_id'],condition=r['condition'],source=r['source'],evidence=r['evidence'],verification=r['verification'],reported_at=r['reported_at'],updated_at=r['updated_at']) for r in c.execute('SELECT * FROM road_reports ORDER BY updated_at DESC')]

def demo_simulated(c):
    row=c.execute("SELECT value FROM state WHERE key='demo_apply_simulated'").fetchone()
    return bool(row and row['value']=='1')

def incident_class(source:str|None)->str:
    if source in {'seeded_simulation','demo_simulation','scenario'}:return 'simulated'
    return 'unverified_demo'

def present_incident(row):
    item=dict(row)
    item['kind']=item.get('kind') or 'sos'
    item['data_class']=incident_class(item.get('source'))
    item['priority_rank_note']='Unclassified priorities sort after low. Missing timestamps are not invented.'
    return item

def road_snapshot(c):
    reports=road_rows(c)
    incidents=[{'id':r['id'],'lat':r['lat'],'lng':r['lng'],'place':r['place'],'people':r['people'],'source':r['source']} for r in c.execute('SELECT id,lat,lng,place,people,source FROM incidents')]
    analysis=analyze_network(ROAD_NETWORK,reports,incidents,apply_simulated=demo_simulated(c))
    s=stage(c)
    analysis['scenario']={'data_class':'simulated','active_closure':CLOSURE if s>=1 else None,'note':'The stage control draws a fictional closure on a toy route (b:bridge). That closure is not copied onto OpenStreetMap roads and is not a hurricane report.'}
    return [serialize_report(ROAD_NETWORK,report) for report in reports], analysis

setup()

class SOS(BaseModel):
    client_id:str=Field(min_length=5,max_length=120)
    message:str=Field(min_length=3,max_length=2000)
    people:int=Field(ge=1,le=100)
    place:str=Field(min_length=2,max_length=180)
    lat:float=Field(ge=-90,le=90)
    lng:float=Field(ge=-180,le=180)

class Status(BaseModel):
    status:str

class Stage(BaseModel):
    stage:int=Field(ge=0,le=3)

@app.get('/api/health')
def health():return {'ok':True,'mode':'simulation','database':'sqlite'}

@app.get('/api/state')
def state():
    with db() as c:
        s=stage(c);items=[present_incident(r) for r in c.execute('SELECT * FROM incidents ORDER BY created_at DESC')]
        events=[dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 80')]
        history=[dict(r) for r in c.execute('SELECT * FROM road_report_history ORDER BY id DESC LIMIT 40')]
        road_reports, road_analysis = road_snapshot(c)
    with db() as c: deliveries=[dict(r) for r in c.execute('SELECT * FROM deliveries ORDER BY created_at DESC LIMIT 100')]
    return {'stage':s,'incidents':items,'deliveries':deliveries,'events':events,'road_history':history,'road_closures':[CLOSURE] if s>=1 else [],'route':pathfind({CLOSURE} if s>=1 else set()),'route_note':'Demonstration graph; not a navigable or safety-verified driving route','ai_mode':'unconnected','offline_transport':'browser_queue_only','road_reports':road_reports,'road_analysis':road_analysis,'sort_default':'priority','priority_order':['critical','high','medium','low','unclassified'],'data_notes':{'geography':'OpenStreetMap road geometry for Swannanoa is real. SOS text, severities, and demo road conditions are simulated.','helene':'Hurricane Helene track is the NHC best track. It is not a closure layer.','current_weather':'Served separately from /api/weather/current and is not historical.'}}

@app.post('/api/incidents',status_code=201)
def submit(body:SOS):
    with db() as c:
        existing=c.execute('SELECT * FROM incidents WHERE id=?',(body.client_id,)).fetchone()
        if existing:return dict(existing)
        incident=(body.client_id,'high',body.message[:80],body.place,body.people,body.lat,body.lng,'Received',body.message,now(),'resident_demo')
        c.execute('INSERT INTO incidents (id,priority,description,place,people,lat,lng,status,message,created_at,source,kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(*incident,'sos'))
        c.execute('INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?)',(body.client_id,'web',None,None,now(),now()))
        log(c,'sos_received',f'{body.client_id} received from demo client')
        return dict(c.execute('SELECT * FROM incidents WHERE id=?',(body.client_id,)).fetchone())

@app.patch('/api/incidents/{incident_id}')
def update(incident_id:str,body:Status):
    if body.status not in {'Received','Acknowledged','Under review','Resolved'}:raise HTTPException(422,'Unsupported status')
    with db() as c:
        if not c.execute('SELECT 1 FROM incidents WHERE id=?',(incident_id,)).fetchone():raise HTTPException(404,'Incident not found')
        c.execute('UPDATE incidents SET status=?, updated_at=? WHERE id=?',(body.status,now(),incident_id))
        log(c,'status',f'{incident_id} → {body.status}')
        return dict(c.execute('SELECT * FROM incidents WHERE id=?',(incident_id,)).fetchone())

@app.post('/api/scenario')
def scenario(body:Stage):
    with db() as c:
        c.execute("UPDATE state SET value=? WHERE key='stage'",(str(body.stage),))
        if body.stage==3 and not c.execute("SELECT 1 FROM incidents WHERE id='SOS-DEMO'").fetchone():
            c.execute('INSERT INTO incidents (id,priority,description,place,people,lat,lng,status,message,created_at,source,kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',('SOS-DEMO','critical','SIMULATED: resident trapped near Swannanoa','Warren Wilson Road',2,35.609,-82.448,'Received','SIMULATED DEMO. Water is rising around a fictional home. Not a historical report.',now(),'scenario','sos'))
        if body.stage==0:c.execute("DELETE FROM incidents WHERE id='SOS-DEMO'")
        log(c,'scenario',f'Demo stage {body.stage}')
    return state()

@app.get('/api/routes')
def routes():
    with db() as c:s=stage(c)
    return {'route':pathfind({CLOSURE} if s>=1 else set()),'closure':CLOSURE if s>=1 else None,'graph':'simulated'}

CONDITIONS={'passable','blocked','damaged','unknown'}
SOURCES={'operator','resident','simulation'}
VERIFICATIONS={'unverified','verified'}

class RoadReportIn(BaseModel):
    segment_id:str=Field(min_length=5,max_length=80)
    condition:str
    source:str='operator'
    evidence:str=''
    verification:str='unverified'

@app.get('/api/road-segments')
def road_segments():
    return catalog(ROAD_NETWORK)

@app.get('/api/road-reports')
def list_road_reports():
    with db() as c:
        reports,_analysis=road_snapshot(c)
    return {'reports':reports,'disclaimer':'Demo reports only. Unknown means unreported. Not an emergency service.'}

@app.get('/api/road-analysis')
def road_analysis():
    with db() as c:
        _reports,analysis=road_snapshot(c)
    return analysis

@app.post('/api/road-reports')
def save_road_report(body:RoadReportIn):
    if body.condition not in CONDITIONS:raise HTTPException(422,'Condition must be passable, blocked, damaged, or unknown')
    if body.source not in SOURCES:raise HTTPException(422,'Source must be operator, resident, or simulation')
    if body.verification not in VERIFICATIONS:raise HTTPException(422,'Verification must be unverified or verified')
    if body.segment_id not in ROAD_NETWORK.segments:raise HTTPException(404,'Road segment is not in the Swannanoa extract')
    evidence=body.evidence.strip()
    if len(evidence)>2000:raise HTTPException(422,'Evidence is too long')
    if body.condition=='unknown':
        with db() as c:
            c.execute('DELETE FROM road_reports WHERE segment_id=?',(body.segment_id,))
            c.execute('INSERT INTO road_report_history (segment_id,condition,source,evidence,verification,recorded_at) VALUES (?,?,?,?,?,?)',(body.segment_id,'unknown',body.source,evidence or '','unverified',now()))
            log(c,'road_report',f'{body.segment_id} cleared to unknown')
        return {'cleared':True,'segment_id':body.segment_id,'report':None,'data_class':'unknown'}
    if body.source=='simulation' and body.verification=='verified':
        raise HTTPException(422,'Simulated drill markings cannot be stored as verified conditions')
    if body.verification=='verified' and len(evidence)<8:
        raise HTTPException(422,'Verified reports need a short evidence note')
    with db() as c:
        existing=c.execute('SELECT * FROM road_reports WHERE segment_id=?',(body.segment_id,)).fetchone()
        if existing and existing['condition']==body.condition and existing['source']==body.source and existing['evidence']==evidence and existing['verification']==body.verification:
            report=next(item for item in road_rows(c) if item.segment_id==body.segment_id)
            return {'cleared':False,'duplicate':True,'report':serialize_report(ROAD_NETWORK,report)}
        reported_at=existing['reported_at'] if existing else now()
        updated=now()
        c.execute('''INSERT INTO road_reports (segment_id,condition,source,evidence,verification,reported_at,updated_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(segment_id) DO UPDATE SET condition=excluded.condition,source=excluded.source,evidence=excluded.evidence,
            verification=excluded.verification,reported_at=excluded.reported_at,updated_at=excluded.updated_at''',
            (body.segment_id,body.condition,body.source,evidence,body.verification,reported_at,updated))
        c.execute('INSERT INTO road_report_history (segment_id,condition,source,evidence,verification,recorded_at) VALUES (?,?,?,?,?,?)',(body.segment_id,body.condition,body.source,evidence,body.verification,updated))
        segment=ROAD_NETWORK.segments[body.segment_id]
        log(c,'road_report',f"ROAD {segment.name or body.segment_id} {body.condition} {body.source} {body.verification}")
        saved=road_rows(c)
    report=next(item for item in saved if item.segment_id==body.segment_id)
    return {'cleared':False,'report':serialize_report(ROAD_NETWORK,report)}


class RadioSOS(SOS):
    gateway_id:str=Field(min_length=2,max_length=80)
    gateway_received_at:Optional[str]=None

@app.post('/api/gateway/sos',status_code=201)
def gateway_sos(body:RadioSOS,x_gateway_token:Optional[str]=Header(default=None)):
    """Gateway forwards a previously radio-received packet. This endpoint does not implement RF."""
    import secrets
    secret=os.getenv('SOSORA_GATEWAY_TOKEN')
    if not secret:
        raise HTTPException(503,'Gateway intake disabled; configure SOSORA_GATEWAY_TOKEN')
    if not x_gateway_token or not secrets.compare_digest(x_gateway_token,secret):
        raise HTTPException(401,'Invalid gateway token')
    with db() as c:
        existing=c.execute('SELECT * FROM incidents WHERE id=?',(body.client_id,)).fetchone()
        if not existing:
            c.execute('INSERT INTO incidents (id,priority,description,place,people,lat,lng,status,message,created_at,source,kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(
                body.client_id,'high',body.message[:80],body.place,body.people,body.lat,body.lng,
                'Received',body.message,now(),'radio_gateway','sos'))
            log(c,'radio_received',f'{body.client_id} forwarded by gateway {body.gateway_id}')
        c.execute('INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?)',(
            body.client_id,'radio',body.gateway_id,body.gateway_received_at,now(),now()))
        record=dict(c.execute('SELECT * FROM incidents WHERE id=?',(body.client_id,)).fetchone())
    return {'accepted':True,'duplicate':bool(existing),'incident':record,'delivery_state':'rescue_center_received',
            'notice':'Demo gateway intake; not emergency dispatch'}

@app.get('/api/deliveries/{client_id}')
def delivery(client_id:str):
    with db() as c:
        row=c.execute('SELECT * FROM deliveries WHERE client_id=?',(client_id,)).fetchone()
    if not row:raise HTTPException(404,'No center receipt; local or gateway queue status is not visible to server')
    return dict(row)

class SimulationToggle(BaseModel):
    applied:bool

@app.post('/api/demo/reset')
def demo_reset():
    with db() as c:
        reset_demo(c)
        log(c,'scenario','Demo scenario reset. Invented records only.')
    return state()

@app.post('/api/demo/simulation')
def demo_simulation(body:SimulationToggle):
    with db() as c:
        c.execute("INSERT INTO state (key,value) VALUES ('demo_apply_simulated',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",('1' if body.applied else '0',))
        log(c,'scenario','Simulated closures '+('applied to' if body.applied else 'removed from')+' the drill analysis')
    return state()

@app.get('/api/incidents')
def list_incidents(sort:str='priority'):
    if sort not in {'priority','newest','oldest'}:raise HTTPException(422,'Sort must be priority, newest, or oldest')
    with db() as c:
        items=[present_incident(r) for r in c.execute('SELECT * FROM incidents')]
    return {'sort':sort,'priority_order':['critical','high','medium','low','unclassified'],'incidents':sort_incidents(items, sort)}

@app.get('/api/weather/helene')
def weather_helene():
    return helene_track()

@app.get('/api/weather/current')
def weather_current():
    return current_conditions()

@app.get('/api/ai/health')
def ai_health():
    # Intentional non-deceptive integration placeholder; no proxying to an unverified local service.
    return {'connected':False,'integration':'Use existing ML service /ml/predict and /ml/incident/parse on port 8002','mode':'not_configured'}

app.mount('/assets',StaticFiles(directory=str(ROOT/'frontend')),name='assets')
@app.get('/')
def homepage():return FileResponse(ROOT/'frontend'/'index.html')
@app.get('/resident')
def resident():return FileResponse(ROOT/'frontend'/'resident.html')
