"""SOSora prototype API. All incidents and closures are SIMULATED; never for emergency use."""
import os, sqlite3, json, uuid, heapq
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parents[1]
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
        if not c.execute('SELECT 1 FROM incidents LIMIT 1').fetchone():
            for x in SEED:c.execute('INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?,?,?)',(*x,now(),'seeded_simulation'))
        c.execute('CREATE TABLE IF NOT EXISTS deliveries (client_id TEXT PRIMARY KEY, transport TEXT NOT NULL, gateway_id TEXT, gateway_received_at TEXT, center_received_at TEXT, created_at TEXT NOT NULL)')
        if not c.execute("SELECT 1 FROM state WHERE key='stage'").fetchone():c.execute("INSERT INTO state VALUES ('stage','0')")

def stage(c):return int(c.execute("SELECT value FROM state WHERE key='stage'").fetchone()[0])
def log(c,kind,msg):c.execute('INSERT INTO events (at,kind,message) VALUES (?,?,?)',(now(),kind,msg))
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
        s=stage(c);items=[dict(r) for r in c.execute('SELECT * FROM incidents ORDER BY created_at DESC')]
        events=[dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 30')]
    with db() as c: deliveries=[dict(r) for r in c.execute('SELECT * FROM deliveries ORDER BY created_at DESC LIMIT 100')]
    return {'stage':s,'incidents':items,'deliveries':deliveries,'events':events,'road_closures':[CLOSURE] if s>=1 else [],'route':pathfind({CLOSURE} if s>=1 else set()),'route_note':'Demonstration graph; not navigable or safety-verified','ai_mode':'unconnected','offline_transport':'browser_queue_only'}

@app.post('/api/incidents',status_code=201)
def submit(body:SOS):
    with db() as c:
        existing=c.execute('SELECT * FROM incidents WHERE id=?',(body.client_id,)).fetchone()
        if existing:return dict(existing)
        incident=(body.client_id,'high',body.message[:80],body.place,body.people,body.lat,body.lng,'Received',body.message,now(),'resident_demo')
        c.execute('INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?,?,?)',incident)
        c.execute('INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?)',(body.client_id,'web',None,None,now(),now()))
        log(c,'sos_received',f'{body.client_id} received from demo client')
        return dict(c.execute('SELECT * FROM incidents WHERE id=?',(body.client_id,)).fetchone())

@app.patch('/api/incidents/{incident_id}')
def update(incident_id:str,body:Status):
    if body.status not in {'Received','Acknowledged','Under review','Resolved'}:raise HTTPException(422,'Unsupported status')
    with db() as c:
        if not c.execute('SELECT 1 FROM incidents WHERE id=?',(incident_id,)).fetchone():raise HTTPException(404,'Incident not found')
        c.execute('UPDATE incidents SET status=? WHERE id=?',(body.status,incident_id))
        log(c,'status',f'{incident_id} → {body.status}')
        return dict(c.execute('SELECT * FROM incidents WHERE id=?',(incident_id,)).fetchone())

@app.post('/api/scenario')
def scenario(body:Stage):
    with db() as c:
        c.execute("UPDATE state SET value=? WHERE key='stage'",(str(body.stage),))
        if body.stage==3 and not c.execute("SELECT 1 FROM incidents WHERE id='SOS-DEMO'").fetchone():
            c.execute('INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?,?,?)',('SOS-DEMO','critical','Resident trapped near Swannanoa','Swannanoa (simulated)',2,35.609,-82.448,'Received','Water is rising around our home. Please help.',now(),'scenario'))
        if body.stage==0:c.execute("DELETE FROM incidents WHERE id='SOS-DEMO'")
        log(c,'scenario',f'Demo stage {body.stage}')
    return state()

@app.get('/api/routes')
def routes():
    with db() as c:s=stage(c)
    return {'route':pathfind({CLOSURE} if s>=1 else set()),'closure':CLOSURE if s>=1 else None,'graph':'simulated'}


class RadioSOS(SOS):
    gateway_id:str=Field(min_length=2,max_length=80)
    gateway_received_at:str|None=None

@app.post('/api/gateway/sos',status_code=201)
def gateway_sos(body:RadioSOS,x_gateway_token:str|None=Header(default=None)):
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
            c.execute('INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?,?,?)',(
                body.client_id,'high',body.message[:80],body.place,body.people,body.lat,body.lng,
                'Received',body.message,now(),'radio_gateway'))
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

@app.get('/api/ai/health')
def ai_health():
    # Intentional non-deceptive integration placeholder; no proxying to an unverified local service.
    return {'connected':False,'integration':'Use existing ML service /ml/predict and /ml/incident/parse on port 8002','mode':'not_configured'}

app.mount('/assets',StaticFiles(directory=str(ROOT/'frontend')),name='assets')
@app.get('/')
def homepage():return FileResponse(ROOT/'frontend'/'index.html')
@app.get('/resident')
def resident():return FileResponse(ROOT/'frontend'/'resident.html')
