"""Build docs/gym/index.html: a visual, click-through view of the sealed NeMo Gym
fresh exam 2 (baseline vs grounded_v2 vs grounded_v2 + argument repair).
Reads only saved evidence; numbers are computed from the rollouts, not typed in.
Usage: python3 scripts/demo/build_gym_page.py
"""
import json, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[2]
EV = ROOT / "ml/nemo_gym/evidence/test_fresh2_relaunch_2026-10-18"
DATA = ROOT / "ml/nemo_gym/data/test_fresh2.jsonl"
OUT = ROOT / "docs/gym/index.html"
ARMS = [("baseline", "Baseline Lightning", "original system prompt + tool descriptions"),
        ("grounded_v2", "+ Rewritten system prompt", "grounded_v2 instructions, same model"),
        ("grounded_v2_nullable", "+ Argument repair", "grounded_v2 + audited nullable adapter")]

def clip(s, n=700):
    s = s if isinstance(s, str) else json.dumps(s)
    return s if len(s) <= n else s[:n] + " …"

scen = {}
for line in DATA.read_text().splitlines():
    r = json.loads(line); s = r["scenario"]
    scen[r["scenario_id"]] = {"family": s.get("family", "?"), "edges": s.get("edges", []),
                             "rescue": s.get("rescue_node"), "incident": s.get("incident_node"),
                             "report": s.get("report", ""), "failed_tools": s.get("failed_tools", [])}

repairs = json.loads((EV / "adapter_repairs.json").read_text())["edits"]
rep_idx = collections.defaultdict(list)
for e in repairs:
    rep_idx[(e["run"], e["scenario_id"])].append(e)

runs = {}
for arm, _, _ in ARMS:
    for k in (1, 2, 3):
        name = f"{arm}_r{k}"
        f = EV / name / "raw/rollouts.jsonl"
        out = {}
        for line in f.read_text().splitlines():
            r = json.loads(line)
            steps = []
            for t in r.get("trajectory", []):
                if t.get("type") == "function_call":
                    steps.append({"k": "call", "name": t.get("name"), "args": clip(t.get("arguments", ""))})
                elif t.get("type") == "function_call_output":
                    steps.append({"k": "out", "text": clip(t.get("output", ""), 400)})
            out[r["scenario_id"]] = {"reward": r.get("reward", 0), "issues": r.get("issues", []),
                                     "error": r.get("error_type"), "steps": steps,
                                     "repairs": rep_idx.get((name, r["scenario_id"]), [])}
        runs[name] = out

summary = json.loads((EV / "summary.json").read_text())
seal = json.loads((EV / "seal.json").read_text()) if (EV / "seal.json").exists() else {}
order = ["bridge_closed", "two_roads_closed", "alternate_route", "isolated",
         "conflicting_evidence", "tool_failure", "missing_location"]
ids = sorted(scen, key=lambda i: (order.index(scen[i]["family"]) if scen[i]["family"] in order else 99, len(scen[i]["edges"]), i))
payload = {"arms": ARMS, "ids": ids, "scen": scen, "runs": runs,
           "seal": {k: seal[k] for k in list(seal)[:6]} if isinstance(seal, dict) else {},
           "summary_policies": [{"arm": p["arm"], "passes": p.get("passes_per_complete_run")} for p in summary.get("policies", [])]}

html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SOSora · NeMo Gym exam</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Manrope:wght@700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#090b0e;--s:#0e1b25;--e:#152631;--c:#182f3c;--ink:#f4f7f8;--mu:#b4c7d0;--fa:#7d95a2;--line:#29404c;--ac:#3ee0cf;--crit:#ff6d78;--warn:#f0b429}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 'DM Sans',sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:32px 24px 64px}
.eyebrow{font:500 12px 'IBM Plex Mono';letter-spacing:.18em;color:var(--fa);text-transform:uppercase}
h1{font:800 40px/1.1 Manrope;margin:6px 0 8px}h2{font:700 20px Manrope;margin:36px 0 12px}
.sub{color:var(--mu);max-width:820px}
.hero{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:24px}
.card{background:var(--s);border:1px solid var(--line);border-radius:16px;padding:18px 20px}
.big{font:800 56px/1 Manrope;font-variant-numeric:tabular-nums}.lab{color:var(--mu);margin-top:6px}.note{color:var(--fa);font-size:13px}
.arrow{color:var(--fa)}
.gridwrap{display:grid;grid-template-columns:minmax(0,1fr) 440px;gap:20px;align-items:start}
table{border-collapse:separate;border-spacing:3px;width:100%}
th{font:500 11px 'IBM Plex Mono';color:var(--fa);text-align:center;padding:4px 0}
td.fam{font:500 11px 'IBM Plex Mono';color:var(--mu);white-space:nowrap;padding-right:8px;text-align:right}
td.c{height:18px;border-radius:4px;cursor:pointer;min-width:26px;transition:transform .1s}
td.c:hover{transform:scale(1.25);outline:2px solid var(--ink)}
td.pass{background:#1fae8f}td.fail{background:#c2414d}td.err{background:#6b4a14}td.sel{outline:2px solid var(--warn)}
td.gap{width:10px}
.famrow td{padding-top:10px}
.panel{position:sticky;top:16px;background:var(--s);border:1px solid var(--line);border-radius:16px;padding:16px;max-height:92vh;overflow:auto}
.mono{font:12px/1.45 'IBM Plex Mono'}
.step{border-left:2px solid var(--line);padding:4px 0 4px 10px;margin:6px 0}
.step.call{border-color:var(--ac)}.step .n{color:var(--ac);font-weight:500}
.step.out{color:var(--mu)}
.rep{background:rgba(240,180,41,.12);border:1px solid var(--warn);border-radius:8px;padding:6px 8px;margin:6px 0;color:var(--warn)}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font:500 11px 'IBM Plex Mono';margin-right:4px}
.okp{color:#1fae8f;border-color:#1fae8f}.badp{color:var(--crit);border-color:var(--crit)}
.legend span{display:inline-flex;align-items:center;gap:6px;margin-right:14px;color:var(--mu);font-size:13px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
footer{margin-top:40px;color:var(--fa);font-size:13px}
code{font:12px 'IBM Plex Mono';background:var(--e);padding:2px 6px;border-radius:6px}
@media(max-width:1000px){.gridwrap{grid-template-columns:1fr}.hero{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<div class="eyebrow">NVIDIA NeMo Gym · sealed fresh exam 2 · simulated scenarios</div>
<h1>Same model. Same 42 unseen tasks. Red to green.</h1>
<p class="sub">Each square is one graded attempt by Nemotron 3.5 Lightning (served on vLLM) on a rescue scenario it had never seen. The NeMo Gym verifier scores every attempt. Columns change one thing at a time, three runs each. Click any square to see the actual tool calls.</p>
<div class="hero" id="hero"></div>
<h2>Every attempt</h2>
<div class="legend"><span><i class="sw" style="background:#1fae8f"></i>passed verifier</span><span><i class="sw" style="background:#c2414d"></i>failed</span><span><i class="sw" style="background:#6b4a14"></i>provider error</span><span><i class="sw" style="outline:2px solid #f0b429"></i>selected</span></div>
<div class="gridwrap"><div><table id="grid"></table></div><div class="panel" id="panel"><div class="eyebrow">Attempt detail</div><p class="note">Click a square. Tip: compare a red baseline square with the same row's green squares.</p></div></div>
<footer id="foot"></footer>
</div>
<script>const D=__DATA__;
const arms=D.arms, ids=D.ids;
function rate(a){let p=0,n=0;for(let k=1;k<=3;k++){const r=D.runs[a+'_r'+k];for(const id of ids){n++;if(r[id]&&r[id].reward>=1)p++}}return [p,n]}
const hero=document.getElementById('hero');
arms.forEach(([a,label,desc],i)=>{const [p,n]=rate(a);const pct=Math.round(100*p/n);
hero.insertAdjacentHTML('beforeend',`<div class="card"><div class="eyebrow">${i?'step '+i:'start'}</div><div class="big" style="color:${i==2?'#3ee0cf':i==1?'#f4f7f8':'#ff6d78'}">${pct}%</div><div class="lab">${label}</div><div class="note">${desc} · ${p}/${n} attempts</div></div>`)});
const g=document.getElementById('grid');
let h='<tr><th></th>';arms.forEach(([a,l])=>{h+=`<th colspan="3">${l}</th><th class="gap"></th>`});h+='</tr>';
let fam=null;
ids.forEach(id=>{const s=D.scen[id];if(s.family!==fam){fam=s.family;h+=`<tr class="famrow"><td class="fam" style="color:#f4f7f8">${fam.replace(/_/g,' ')}</td></tr>`}
h+=`<tr><td class="fam">${(s.edges||[]).length} roads</td>`;
arms.forEach(([a])=>{for(let k=1;k<=3;k++){const r=D.runs[a+'_r'+k][id];const cls=!r?'err':r.error?'err':(r.reward>=1?'pass':'fail');h+=`<td class="c ${cls}" data-id="${id}" data-run="${a}_r${k}" title="${a} run ${k}"></td>`}h+='<td class="gap"></td>'});h+='</tr>'});
g.innerHTML=h;
function esc(t){return String(t).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function graph(s){const nodes=[...new Set(s.edges.flatMap(e=>[e.source,e.target]))];const N=nodes.length,W=400,H=180;
const pos={};nodes.forEach((n,i)=>{const t=i/(Math.max(N-1,1));pos[n]=[20+t*(W-40),H/2+Math.sin(i*1.3)*55]});
let svg=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="background:#0b151d;border-radius:10px">`;
s.edges.forEach(e=>{const [x1,y1]=pos[e.source],[x2,y2]=pos[e.target];const c=e.status==='closed'?'#ff3b30':e.status==='open'?'#3ee0cf':'#f0b429';svg+=`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${e.status==='closed'?3:1.6}" ${e.status==='closed'?'stroke-dasharray="4 3"':''} opacity=".9"/>`});
nodes.forEach(n=>{const [x,y]=pos[n];const f=n===s.rescue?'#f4f7f8':n===s.incident?'#ff6d78':'#29404c';svg+=`<circle cx="${x}" cy="${y}" r="${n===s.rescue||n===s.incident?6:3.5}" fill="${f}"/>`});
return svg+`</svg><div class="note">white = rescue base · red dot = incident${s.incident?'':' (location missing)'} · red dashed = closed road</div>`}
g.addEventListener('click',ev=>{const td=ev.target.closest('td.c');if(!td)return;document.querySelectorAll('td.sel').forEach(x=>x.classList.remove('sel'));td.classList.add('sel');
const id=td.dataset.id,run=td.dataset.run,s=D.scen[id],r=D.runs[run][id];
let p=`<div class="eyebrow">${run.replace(/_r(\\d)$/,' · run $1')}</div><h2 style="margin:6px 0">${s.family.replace(/_/g,' ')}</h2><div class="mono note">${id}</div>`;
p+=`<p><span class="pill ${r&&r.reward>=1?'okp':'badp'}">reward ${r?r.reward:'n/a'}</span>${(r&&r.issues||[]).map(i=>`<span class="pill badp">${esc(i)}</span>`).join('')}${r&&r.error?`<span class="pill">${esc(r.error)}</span>`:''}</p>`;
p+=`<p class="note">${esc(s.report)}${s.failed_tools.length?' · simulated outage: '+s.failed_tools.join(', '):''}</p>`+graph(s);
if(r&&r.repairs.length){r.repairs.forEach(e=>{p+=`<div class="rep mono">argument repair on ${esc(e.tool)}: ${esc(e.field)} "${esc(e.before)}" → ${JSON.stringify(e.after)}</div>`})}
p+='<h2 style="font-size:15px">Tool calls</h2>';
(r?r.steps:[]).forEach(st=>{p+=st.k==='call'?`<div class="step call mono"><span class="n">${esc(st.name)}</span>(${esc(st.args)})</div>`:`<div class="step out mono">→ ${esc(st.text)}</div>`});
document.getElementById('panel').innerHTML=p});
document.getElementById('foot').innerHTML=`Evidence: <code>ml/nemo_gym/evidence/test_fresh2_relaunch_2026-10-18/</code> · protocol, seal and caveats in <code>docs/GYM_RESULTS.md</code>. Scenarios are synthetic (CC0, generator <code>ml/nemo_gym/scenarios.py</code>). The argument repair is a compatibility fix (string "None" → null), not model training. Page built by <code>scripts/demo/build_gym_page.py</code> from saved rollouts.`;
</script></body></html>"""
OUT.write_text(html.replace("__DATA__", json.dumps(payload, separators=(",", ":"))))
for a, l, _ in ARMS:
    p = sum(1 for k in (1, 2, 3) for i in ids if runs[f"{a}_r{k}"].get(i, {}).get("reward", 0) >= 1)
    print(a, p, "/", 3 * len(ids))
print("wrote", OUT, OUT.stat().st_size // 1024, "KB")
