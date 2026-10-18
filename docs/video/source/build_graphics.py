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

BG='#090b0e'; SURFACE='#0e1b25'; INK='#f4f7f8'; MUTED='#b4c7d0'; FAINT='#7d95a2'; LINE='#29404c'; TEAL='#3ee0cf'; RED='#ff6d78'; GOLD='#f0b429'
def text(x,y,content,size=32,color=INK,font='DM Sans',weight=400,spacing=None):
    extra = f' letter-spacing="{spacing}"' if spacing is not None else ''
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{color}"{extra}>{escape(content)}</text>'
def lines(x,y,content,size=36,color=INK,font='DM Sans',weight=400,step=None):
    return ''.join(text(x,y+i*(step or size*1.35),v,size,color,font,weight) for i,v in enumerate(content))
def rect(x,y,w,h,color=SURFACE,r=24,stroke=LINE,extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}" stroke="{stroke}" {extra}/>'
def path(d,color=TEAL,width=3,extra=''):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def logo(x=96,y=80,scale=1):
    return f'<g transform="translate({x} {y}) scale({scale})">'+rect(0,0,64,64,TEAL,18,TEAL)+''.join(path(f'M18 {v} Q25 {v-5} 32 {v} T46 {v}', '#08252a',3) for v in (25,33,41))+'</g>'
def brand():
    return logo()+text(182,124,'SOSora',38,font='Manrope',weight=800)+text(1510,117,'RESCUE INTELLIGENCE',18,FAINT,'IBM Plex Mono',spacing=2)
def terrain():
    out=''
    for i in range(14):
        x=1020+i*42; y=90+i*48
        out+=path(f'M{x} -40 C {x-350} {y+70}, {x+420} {y+160}, {x+90} {y+350} S {x-480} {y+700}, {x+460} 1130',LINE,1.4,extra='opacity=".48"')
    return out

def frame(content,transparent=False):
    bg='' if transparent else f'<rect width="1920" height="1080" fill="{BG}"/>'+terrain()+brand()
    return '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1920" height="1080" viewBox="0 0 1920 1080"><defs><style>'+''.join(font_css)+'</style><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10" fill="'+TEAL+'"/></marker></defs>'+bg+content+'</svg>'
def save(name,content,transparent=False):
    (OUT / (name+'.svg')).write_text(frame(content,transparent))
def footer(label):
    return path('M96 964 H1824',LINE,1)+text(96,1016,label,21,FAINT,'IBM Plex Mono')

save('01-title',text(96,330,'WHEN TOWERS AND ROADS FAIL',23,TEAL,'IBM Plex Mono',spacing=3)+text(86,530,'SOSora',178,font='Manrope',weight=800)+lines(96,644,['Keep the rescue map alive.','Know who needs help. Know how to reach them.'],44,MUTED,step=65)+''.join(rect(x,826,w,62,'#152631',12)+text(x+24,868,label,22,TEAL,'IBM Plex Mono') for x,w,label in [(96,300,'BEACON INTAKE'),(420,290,'RESIDENT SOS'),(734,340,'COMMAND MAP')])+footer('HACKATHON PROTOTYPE  /  SIMULATED INCIDENTS · REAL ROAD GRAPH'))

sources={
'cell_sites': {'url':'https://docs.fcc.gov/public/attachments/DOC-405893A1.pdf','corroboration':'https://wirelessestimator.com/wp-content/uploads/2024/09/Hurricane.Helene.Cell_.Tower_.Status.pdf','note':'FCC Sep 28 2024, 9 AM EDT, 21-county NC reporting area; rounded to 74%. Sep 29 report p16 corroborates prior 74.3%; direct primary fetch was blocked.'},
'damaged_sites': {'url':'https://www.ncdot.gov/news/press-releases/Pages/2024/2024-11-01-this-week-ncdot-now.aspx','note':'More than 8,100 damaged sites, not distinct roads; Nov 1 2024.'},
'72_hours': {'url':'https://www.ncdps.gov/tropical-storm-helene-after-action-review','note':'NCEM/McChrystal Group recommendation for local emergency managers, not a demonstrated SOSora runtime.'}}

def stat(name,kicker,number,unit,headline,detail,source,decoration):
    body=text(96,270,kicker,23,TEAL,'IBM Plex Mono',spacing=3)+text(82,540,number,218,font='Manrope',weight=800)+text(105,613,unit,28,TEAL,'IBM Plex Mono',spacing=2)+lines(96,730,headline,49,INK,'Manrope',700,step=65)+lines(96,884,detail,27,MUTED,step=39)+decoration+footer(source)
    save(name,body)
# An honest 100-cell visual: 74 outages, 26 service cells.
grid=''.join(rect(1394+(i%10)*32,326+(i//10)*32,19,19,RED if i<74 else '#29404c',4,RED if i<74 else '#29404c') for i in range(100))
stat('02-stat-cell-sites','HELENE / COMMUNICATIONS','74%','CELL SITES OUT OF SERVICE',['When the signal disappears,','so does the rescue picture.'],['21-county North Carolina reporting area.','Snapshot: September 28, 2024 · 9 AM EDT.'],'SOURCE: FCC · COMMUNICATIONS STATUS REPORT · SEP 28, 2024',grid)
road=path('M1370 742 L1460 620 L1430 514 L1552 410 L1660 308',FAINT,8)+path('M1430 514 L1545 560 L1660 515',FAINT,8)+path('M1491 462 L1537 427',RED,12)+text(1370,833,'ACCESS DISRUPTED',20,RED,'IBM Plex Mono')
stat('03-stat-damaged-sites','HELENE / ROAD ACCESS','8,100+','DAMAGED SITES',['Road damage turns','nearby into unreachable.'],['Road, bridge and culvert damage sites in western NC.','Reported by NCDOT on November 1, 2024.'],'SOURCE: NCDOT · HELENE RECOVERY UPDATE · NOV 1, 2024',road)
clock='<circle cx="1540" cy="484" r="148" fill="none" stroke="'+LINE+'" stroke-width="3"/>'+path('M1540 365 V484 L1630 533',TEAL,8)+''.join(path(f'M1540 322 V344',FAINT,4,extra=f'transform="rotate({a} 1540 484)"') for a in range(0,360,30))
stat('04-stat-72-hours','READINESS / THE OPERATING REQUIREMENT','72','HOURS WITHOUT COMMUNICATIONS',['Prepare to keep working','when networks cannot.'],['NCEM after-action recommendation for local emergency managers.','A readiness target, not a measured SOSora endurance claim.'],'SOURCE: NCEM / McCHRYSTAL GROUP · HELENE AFTER-ACTION REVIEW',clock)

body=text(96,260,'FIELD EVIDENCE → SHARED SITUATIONAL AWARENESS',23,TEAL,'IBM Plex Mono',spacing=2)
body+=rect(96,365,365,235)+logo(125,398,.7)+text(190,439,'BEACON',32,font='Manrope',weight=800)+lines(126,499,['Voice + water sensor','Known crossing location','Durable outbox'],24,MUTED,step=36)
body+=rect(96,638,365,225)+text(126,697,'SOS APP',32,font='Manrope',weight=800)+lines(126,753,['Resident request + GPS','Queues without signal','Sends when a link returns'],24,MUTED,step=36)
body+=path('M461 482 H528 V600 H606',TEAL,3,'marker-end="url(#arrow)"')+path('M461 750 H528 V600',TEAL,3)
body+=rect(620,340,660,554,'#152631',28,TEAL)+text(662,406,'COMMAND',43,font='Manrope',weight=800)+text(662,456,'NEMOTRON LIGHTNING ON vLLM',24,TEAL,'IBM Plex Mono')
for y,num,label,desc in [(502,'01','Resolve the road','Real OSM segment IDs'),(611,'02','Apply the trust rule','Road status is enforced in code'),(720,'03','Recompute road access','Graph reachability from rescue base')]:
    body+=text(666,y+39,num,25,FAINT,'IBM Plex Mono')+text(724,y+26,label,31,font='Manrope',weight=700)+text(724,y+65,desc,23,MUTED)
body+=path('M1280 600 H1377',TEAL,3,'marker-end="url(#arrow)"')+rect(1392,365,432,498)+text(1426,425,'LIVE RESCUE MAP',29,font='Manrope',weight=800)
body+=path('M1429 684 L1508 577 L1591 630 L1675 513 L1788 580',LINE,10)+path('M1429 684 L1508 577 L1591 630',TEAL,5)+path('M1615 596 L1649 548',RED,9)
for x,y in [(1647,485),(1731,513),(1773,470)]: body+=f'<circle cx="{x}" cy="{y}" r="12" fill="{RED}"/><circle cx="{x}" cy="{y}" r="23" fill="none" stroke="{RED}" opacity=".5"/>'
body+=lines(1426,755,['SOS pins + access status','Evidence + operator review'],24,MUTED,step=42)+footer('OFFLINE-CAPABLE ARCHITECTURE  /  CAPTURE USES LIVE REMOTE vLLM · SIMULATED REPORTS')
save('05-system-diagram',body)

lower=[('06-lower-tool-calling','TOOL CALLING','Resolve location. Check evidence. Recompute access.'),('07-lower-nemotron','NEMOTRON LIGHTNING','The only generative model in SOSora.'),('08-lower-redhat-vllm','RED HAT vLLM','Integration target · this capture runs upstream vLLM.'),('09-lower-nemo-gym','NeMo GYM','Official resource tools + verifier · simulated workflow evaluation.')]
for name,title,desc in lower:
    save(name,rect(96,800,1728,184,'#0e1b25',18,LINE,extra='fill-opacity=".96"')+f'<rect x="96" y="800" width="7" height="184" rx="3" fill="{TEAL}"/>'+text(136,875,title,49,font='Manrope',weight=800)+text(139,933,desc,28,MUTED)+text(1592,853,'SOSora',24,TEAL,'Manrope',800),True)

body=text(96,260,'MEASURED. REPRODUCIBLE. BOUNDED.',51,font='Manrope',weight=800)
for x in [96,680,1264]: body+=rect(x,318,560,505)
body+=text(126,374,'NeMo GYM / FRESH EXAM',20,TEAL,'IBM Plex Mono')+text(126,476,'15 → 30',73,font='Manrope',weight=800)+lines(126,529,['Mean passes out of 42','Baseline → grounded_v2'],27,MUTED,step=43)+lines(126,640,['Three repeats per frozen policy.','Prompt-only: mean 29.67 / 42.','Simulated workflow cases.'],23,MUTED,step=39)
body+=text(710,374,'LIVE vLLM / HERO FLOW',20,TEAL,'IBM Plex Mono')+text(710,476,'20 / 20',73,font='Manrope',weight=800)+lines(710,529,['Correct bridge + exact','five-incident access loss'],27,MUTED,step=43)+text(710,669,'7.912 s',57,TEAL,'Manrope',800)+lines(710,716,['Median text-radio request.','Excludes ASR + browser rendering.'],22,MUTED,step=35)
body+=text(1294,374,'SERVED PARAMETER BUDGET',20,TEAL,'IBM Plex Mono')+text(1294,459,'32,954,738,082',39,font='IBM Plex Mono',weight=500)+lines(1294,519,['Exact model parameters','including Whisper tiny.en'],27,MUTED,step=43)+text(1294,661,'45,261,918',43,TEAL,'IBM Plex Mono',500)+lines(1294,707,['parameters below the 33B cap.','All Nemotron experts + MTP counted.'],22,MUTED,step=35)
body+=lines(96,885,['Limits: grounded_v2 still fails 12/42 cases per run (missing location / tool failure).','Ambiguity: safe final state 10/10; strict model abstention only 1/10. Safeguards matter.'],23,FAINT,step=37)+footer('SOURCES: docs/GYM_RESULTS.md · docs/VLLM_RESULTS.md · docs/PARAM_BUDGET.md')
save('10-results',body)
save('11-end-card',text(96,327,'WHEN THE NETWORK FAILS,',25,TEAL,'IBM Plex Mono',spacing=3)+lines(96,465,['Keep the rescue','map alive.'],108,INK,'Manrope',800,step=130)+text(101,760,'SOSora',67,TEAL,'Manrope',800)+text(102,823,'Beacon + SOS app + Command',35,MUTED)+footer('HACKATHON PROTOTYPE  /  DECISION SUPPORT · OPERATOR REVIEW BEFORE RESPONSE'))
(ROOT/'docs/video/evidence/graphic_sources.json').write_text(json.dumps({'stats':sources,'results':['docs/GYM_RESULTS.md','docs/VLLM_RESULTS.md','docs/PARAM_BUDGET.md'],'fonts':fonts,'palette_source':'frontend/app/globals.css','serving_qualification':'Red Hat vLLM is an integration target; actual capture uses upstream vLLM.'},indent=2)+'\n')
print('Built',len(list(OUT.glob('*.svg'))),'SVGs')
