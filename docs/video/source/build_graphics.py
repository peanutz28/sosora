"""Rebuild editable SVG video cards using the dashboard's bundled font files."""
import base64
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/video/graphics'
OUT.mkdir(parents=True, exist_ok=True)
css = ''.join(p.read_text() for p in (ROOT / 'frontend/.next/static/css').glob('*.css'))
font_css = []
fonts = {}
for family in ('Manrope', 'DM Sans', 'IBM Plex Mono'):
    faces = [f for f in re.findall(r'@font-face\{([^}]+)\}', css)
             if re.search(r'font-family:["\']?' + family + r'["\']?;', f) and 'u+00??' in f]
    if not faces:
        raise RuntimeError('Missing bundled Latin font: ' + family)
    face = faces[-1]
    name = re.search(r'src:url\(([^)]+)\)', face)[1]
    data = (ROOT / 'frontend/.next/static/media' / Path(name).name).read_bytes()
    fonts[family] = Path(name).name
    font_css.append("@font-face{font-family:'" + family + "';font-style:normal;font-weight:100 1000;src:url(data:font/woff2;base64," + base64.b64encode(data).decode() + ") format('woff2')}")

# Film graphics: a fixed 96px safe area, large type, actual road geometry.
BG='#090b0e'; NAVY='#0e1b25'; WHITE='#f4f7f8'; MUTED='#b4c7d0'; FAINT='#7d95a2'; LINE='#29404c'; CYAN='#3ee0cf'; CORAL='#ff6d78'
def t(x,y,value,size=32,color=WHITE,font='DM Sans',weight=400,anchor='start',spacing=None):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{color}"'+(f' letter-spacing="{spacing}"' if spacing else '')+'>'+escape(value)+'</text>'
def txt(x,y,values,size=40,color=WHITE,font='DM Sans',weight=400,step=None):
    return ''.join(t(x,y+i*(step or size*1.22),v,size,color,font,weight) for i,v in enumerate(values))
def line(d,color=CYAN,width=2,extra=''):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def box(x,y,w,h,fill=NAVY,stroke=LINE,r=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'
def circle(x,y,r,fill=CYAN,extra=''):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" {extra}/>'
def mark(x,y,size=56):
    return f'<g transform="translate({x} {y}) scale({size/64})">'+box(0,0,64,64,CYAN,CYAN,19)+''.join(line(f'M18 {v} Q25 {v-5} 32 {v} T46 {v}', '#08252a',3.5) for v in (25,33,41))+'</g>'
def header(section):
    return mark(96,72,48)+t(163,109,'SOSora',32,font='Manrope',weight=800)+t(1824,105,section,22,FAINT,'IBM Plex Mono',anchor='end')
def foot(source):
    return line('M96 965 H1824',LINE,1)+t(96,1013,source,22,MUTED,'DM Sans')
def dot(x,y,color=CORAL):
    return circle(x,y,27,color,'opacity=".12"')+circle(x,y,14,'none',f'stroke="{color}" stroke-width="2"')+circle(x,y,6,color)

roads=json.loads((ROOT/'backend/data/roads.geojson').read_text())['features']
def road_map(x,y,w,h,opacity=1,labels=False,pins=True):
    # Swannanoa operations corridor. Projected road geometry is used as design material.
    west,east,south,north=-82.458,-82.365,35.584,35.65
    def xy(p): return x+(p[0]-west)/(east-west)*w,y+(north-p[1])/(north-south)*h
    clip_id=f'crop-{x}-{y}-{w}-{h}'.replace('.','_')
    out=f'<defs><clipPath id="{clip_id}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs><g clip-path="url(#mapClip)"><g opacity="{opacity}" clip-path="url(#{clip_id})"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#ocean)"/>'
    for f in roads:
        pts=f['geometry'].get('coordinates',[])
        if f['geometry']['type']!='LineString' or not pts: continue
        if not any(west<=p[0]<=east and south<=p[1]<=north for p in pts): continue
        prop=f['properties'];name=prop.get('name','');major=prop.get('highway') in ('primary','secondary','motorway','trunk','tertiary')
        highlight=name in ('Warren Wilson Road','Bee Tree Road','Old US Highway 70')
        d='M'+' L'.join(f'{a:.1f} {b:.1f}' for a,b in map(xy,pts))
        out+=line(d,CYAN if highlight else '#395466',2.8 if highlight else 1.4 if major else .8,extra='opacity="'+('0.85' if highlight else '.62' if major else '.35')+'"')
    for p in ([(-82.40719,35.63129),(-82.41446,35.61981),(-82.41475,35.64090),(-82.41149,35.62712),(-82.42622,35.62413)] if pins else []):
        a,b=xy(p);out+=dot(a,b)
    a,b=xy((-82.42702,35.61258));out+=box(a-9,b-9,18,18,CYAN,CYAN,3)
    if labels:out+=t(a+27,b+10,'BEACON',21,CYAN,'IBM Plex Mono')
    return out+'</g></g>'

BASE_DEFS='''<radialGradient id="ocean"><stop stop-color="#102936"/><stop offset="1" stop-color="#090b0e"/></radialGradient>
<linearGradient id="veil"><stop stop-color="#090b0e"/><stop offset=".5" stop-color="#090b0e" stop-opacity=".97"/><stop offset="1" stop-color="#090b0e" stop-opacity="0"/></linearGradient>
<linearGradient id="panel"><stop stop-color="#182f3c"/><stop offset="1" stop-color="#0e1b25"/></linearGradient>
<linearGradient id="rule"><stop stop-color="#3ee0cf"/><stop offset="1" stop-color="#3ee0cf" stop-opacity="0"/></linearGradient>
<clipPath id="mapClip"><rect x="0" y="140" width="1920" height="805"/></clipPath>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10" fill="#3ee0cf"/></marker>'''
def save(name,body,section='',transparent=False):
    bg='' if transparent else f'<rect width="1920" height="1080" fill="{BG}"/>'
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><defs><style>'+''.join(font_css)+'</style>'+BASE_DEFS+'</defs>'+bg+body+(header(section) if section else '')+'</svg>'
    (OUT/(name+'.svg')).write_text(svg)

# Opening: oversized identity against a geographic signal field.
body=road_map(750,150,1250,830,.9,True)+'<rect x="0" y="140" width="1370" height="805" fill="url(#veil)"/>'
body+=t(96,263,'WHEN TOWERS AND ROADS GO DOWN',26,CYAN,'IBM Plex Mono',spacing=2)
body+=t(83,526,'SOSora',252,font='Manrope',weight=800)
body+=txt(103,661,['Keep the rescue','map alive.'],77,WHITE,'Manrope',700,step=91)
body+='<rect x="105" y="814" width="185" height="5" fill="'+CYAN+'"/>'+t(105,883,'BEACON  /  SOS APP  /  COMMAND',26,MUTED,'IBM Plex Mono')
body+=foot('Hackathon prototype  ·  Real road geometry  ·  Simulated incidents')
save('01-title',body,'RESCUE INTELLIGENCE')

# One statistic, one visual idea, one source line.
body=t(96,252,'THE COMMUNICATIONS NETWORK FAILS',26,CYAN,'IBM Plex Mono',spacing=1)
body+=t(80,655,'74',450,font='Manrope',weight=800)+t(610,442,'%',160,CORAL,'Manrope',700)
body+=txt(104,772,['of cell sites were offline.'],63,WHITE,'Manrope',700)+txt(108,856,['North Carolina’s 21-county disaster-reporting area.','September 28, 2024 · 9 AM EDT snapshot.'],29,MUTED,step=43)
body+=circle(1450,440,290,'none',f'stroke="{LINE}" stroke-width="2" stroke-dasharray="2 14"')+circle(1450,440,210,'none',f'stroke="{CORAL}" stroke-width="2" opacity=".35"')
body+=line('M1320 846 L1450 491 L1580 846 M1370 710 H1530 M1405 616 H1495 M1350 788 H1550 M1370 710 L1550 788 M1530 710 L1350 788',FAINT,5)
body+=dot(1450,440,CORAL)+line('M1318 328 Q1243 440 1318 552 M1582 328 Q1657 440 1582 552',CORAL,5)+line('M1259 267 Q1146 440 1259 613 M1641 267 Q1754 440 1641 613',CORAL,3,'opacity=".4"')
body+=t(1450,926,'NO SIGNAL',27,CORAL,'IBM Plex Mono',anchor='middle',spacing=3)+foot('FCC · Helene Communications Status Report · September 28, 2024 · Rounded from 74.3%')
save('02-stat-cell-sites',body,'HELENE / COMMUNICATIONS')

body=road_map(1060,165,920,780,.7,pins=False)+'<rect x="900" y="140" width="420" height="805" fill="url(#veil)"/>'
body+=t(96,252,'THE ROAD NETWORK FAILS TOO',26,CYAN,'IBM Plex Mono',spacing=1)+t(82,583,'8,100+',296,font='Manrope',weight=800)
body+=txt(105,723,['Road, bridge and','culvert damage sites.'],65,WHITE,'Manrope',700,step=82)+txt(109,893,['Damage sites identified in western North Carolina.'],29,MUTED)
body+=foot('NCDOT · Helene recovery update · November 1, 2024 · Sites, not distinct destroyed roads')
save('03-stat-damaged-sites',body,'HELENE / ROAD ACCESS')

body=t(96,252,'THE READINESS REQUIREMENT',26,CYAN,'IBM Plex Mono',spacing=1)+t(80,624,'72',420,font='Manrope',weight=800)+t(685,621,'hours',84,CYAN,'Manrope',700)
body+=txt(105,757,['Prepare to operate','without communications.'],61,WHITE,'Manrope',700,step=76)+t(109,902,'NCEM recommendation — not a measured SOSora runtime.',29,MUTED)
body+=circle(1470,548,286,'none',f'stroke="{LINE}" stroke-width="2"')+circle(1470,548,235,'none',f'stroke="{CYAN}" stroke-width="2" opacity=".2"')
for a in range(0,360,6):body+=line('M1470 248 V'+str(270 if a%30==0 else 259),CYAN if a%30==0 else LINE,4 if a%30==0 else 2,f'transform="rotate({a} 1470 548)"')
body+=line('M1470 350 V548 L1595 622',CYAN,7)+circle(1470,548,10,CYAN)+t(1470,917,'KEEP WORKING.',26,CYAN,'IBM Plex Mono',anchor='middle',spacing=2)+foot('NCEM / McChrystal Group · Tropical Storm Helene after-action review · Communications recommendation')
save('04-stat-72-hours',body,'HELENE / RESILIENCE')

# Architecture: devices and routes rather than a grid of dashboard cards.
body=t(96,254,'Many signals. One rescue picture.',77,WHITE,'Manrope',800)
body+=line('M160 375 V346 M139 365 Q160 346 181 365 M123 351 Q160 317 197 351',CYAN,3)+box(126,382,70,125,'url(#panel)',CYAN,10)+box(141,404,40,29,BG,LINE,3)+circle(161,467,8,CYAN)
body+=t(225,415,'BEACON',37,WHITE,'Manrope',800)+txt(227,463,['Voice + water sensor','Queued at the crossing.'],27,MUTED,step=39)
body+=box(130,620,66,128,'url(#panel)',CYAN,10)+line('M151 635 H175',FAINT,3)+circle(163,689,19,CORAL)+t(225,653,'SOS APP',37,WHITE,'Manrope',800)+txt(227,701,['Resident request + GPS','Queue now. Send when linked.'],27,MUTED,step=39)
body+=line('M555 443 H615 V564 H716',CYAN,3,'marker-end="url(#arrow)"')+line('M555 682 H615 V564',CYAN,3)
body+='<path d="M744 362 H1264 L1300 398 V758 H744 Z" fill="url(#panel)" stroke="'+CYAN+'" stroke-width="2"/>'
body+=t(785,438,'COMMAND',56,WHITE,'Manrope',800)+t(787,501,'Nemotron Lightning',35,CYAN,'Manrope',700)+t(788,547,'ON vLLM',26,MUTED,'IBM Plex Mono')+line('M785 584 H1257',LINE,2)
for x,label,sub in [(787,'Resolve','real road IDs'),(958,'Enforce','trust in code'),(1132,'Recompute','road access')]:
 body+=circle(x+6,627,5,CYAN)+t(x,677,label,26,WHITE,'Manrope',700)+t(x,718,sub,20,MUTED)
body+=line('M1300 564 H1400',CYAN,3,'marker-end="url(#arrow)"')
body+=box(1421,362,403,396,NAVY,LINE,0)+road_map(1441,385,360,348,.85)+t(1422,815,'RESCUE MAP',36,WHITE,'Manrope',800)
body+=t(96,920,'Code owns road status. Operators own the decision.',39,WHITE,'Manrope',700)+foot('Offline-capable architecture · This video uses live remote vLLM · Real OSM graph, simulated reports')
save('05-system-diagram',body,'SYSTEM / FIELD TO COMMAND')

# Compact, transparent overlays with real safe margins.
lower=[('06-lower-tool-calling','TOOL CALLING','Location → evidence → trust → access'),('07-lower-nemotron','NEMOTRON LIGHTNING','One generative model. Structured tools.'),('08-lower-redhat-vllm','RED HAT vLLM','Integration target · capture uses upstream vLLM'),('09-lower-nemo-gym','NeMo GYM','Official tools + verifier · simulated workflows')]
for name,title,subtitle in lower:
 body='<path d="M96 805 H1234 L1266 837 V984 H96 Z" fill="'+NAVY+'" fill-opacity=".97" stroke="'+LINE+'"/>'
 body+='<path d="M96 805 H1266" stroke="url(#rule)" stroke-width="3"/>'+mark(122,843,53)+t(202,882,title,45,WHITE,'Manrope',800)+t(205,943,subtitle,27,MUTED)
 save(name,body,transparent=True)

body=t(96,245,'RESULTS / FROZEN EVALUATIONS',26,CYAN,'IBM Plex Mono',spacing=1)+t(96,345,'Tested, with the limits in view.',76,WHITE,'Manrope',800)
body+=line('M661 416 V776 M1257 416 V776',LINE,2)
body+=t(96,446,'NeMo GYM',26,CYAN,'IBM Plex Mono')+t(91,578,'15 → 30',102,WHITE,'Manrope',800)+t(100,643,'mean passes / 42',40,WHITE,'Manrope',700)+txt(101,705,['Baseline → grounded_v2','Three repeats. Simulated cases.','Prompt-only: mean 29.67 / 42.'],26,MUTED,step=37)
body+=t(710,446,'LIVE vLLM',26,CYAN,'IBM Plex Mono')+t(704,578,'20/20',112,WHITE,'Manrope',800)+t(713,643,'correct hero outcomes',38,WHITE,'Manrope',700)+t(714,711,'7.912 s median',42,CYAN,'Manrope',800)+txt(716,755,['Text-radio request; excludes ASR','and browser rendering.'],24,MUTED,step=33)
body+=t(1306,446,'BELOW THE CAP',26,CYAN,'IBM Plex Mono')+t(1302,578,'33B',112,WHITE,'Manrope',800)+t(1310,643,'Total parameters:',32,MUTED,'Manrope',700)+t(1308,711,'32,954,738,082',38,CYAN,'IBM Plex Mono',500)+t(1310,755,'ASR + vision included.',25,MUTED)+t(1310,791,'All Nemotron experts counted.',22,MUTED)
body+=line('M96 832 H1824',LINE,1)+t(97,877,'LIMITS',23,CORAL,'IBM Plex Mono')+t(224,877,'12/42 Gym cases still fail per run: missing location and tool failure.',27,WHITE,'Manrope',700)+t(225,920,'Ambiguity: model abstention 1/10; safe guarded state 10/10. Code safeguards remain essential.',25,MUTED)
body+=foot('Sources: GYM_RESULTS.md  /  VLLM_RESULTS.md  /  PARAM_BUDGET.md  ·  Exact source snapshots included')
save('10-results',body,'MEASURED / REPRODUCIBLE')

body=road_map(0,160,1920,780,.29)+'<rect x="0" y="0" width="1920" height="1080" fill="'+BG+'" opacity=".4"/>'
body+=mark(908,193,104)+t(960,529,'SOSora',232,WHITE,'Manrope',800,anchor='middle')+t(960,658,'Keep the rescue map alive.',67,WHITE,'Manrope',700,anchor='middle')+t(960,730,'When towers and roads go down.',36,MUTED,anchor='middle')+t(960,859,'BEACON  /  SOS APP  /  COMMAND',25,CYAN,'IBM Plex Mono',anchor='middle',spacing=2)+foot('Hackathon prototype · Simulated incidents · Decision support, operator review required')
save('11-end-card',body)
print('Rebuilt 11 graphic artboards')
