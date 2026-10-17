'use strict';
const $ = id => document.getElementById(id);
const svgIcon = name => `<svg class="icon"><use href="#i-${name}"/></svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = value => `${(Number(value) * 100).toFixed(1)}%`;
const number = value => new Intl.NumberFormat('en-US').format(value);
const state = {data:null, scene:null, prediction:null, filter:'flooded_road', selected:null, zoom:1, panX:0, panY:0, baseWidth:500, compare:false, live:false, requestId:0, incident:null, provider:false, busy:false};
let toastTimer;
function toast(message){ $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4500); }
async function api(path,body){
  const response = await fetch(`/api${path}`, body === undefined ? {cache:'no-store'} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let result; try {result = await response.json();} catch {throw new Error('The local model connection is unavailable.');}
  if(!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : `Request failed (${response.status}).`);
  return result;
}
function setView(view){
  for(const name of ['operations','evidence','incidents']) $(name+'View').hidden = name !== view;
  document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('active',button.dataset.view===view));
  $('viewTitle').textContent = {operations:'Imagery operations', evidence:'Model evidence', incidents:'Incident desk'}[view];
  if(view==='operations') requestAnimationFrame(fitMap);
}
function setHash(value){ if(location.hash !== '#'+value) history.replaceState(null,'','#'+value); }
async function selectScene(key){
  const scene = state.data.scenes.find(s=>s.key===key) || state.data.scenes[0];
  state.scene = scene; $('observationsPanel').classList.remove('mobile-open'); state.requestId++; state.busy = false; state.live=false; state.selected=null;
  $('mapBusy').hidden=true; $('analyzeButton').disabled=false;
  state.zoom=1; state.panX=0; state.panY=0;
  $('threshold').value=50; $('thresholdValue').textContent='50%';
  $('analysisCaption').textContent='Uses the trained model on your machine';
  $('mapTitle').textContent=scene.title; $('mapSubtitle').textContent=scene.subtitle;
  $('mapImage').src=scene.image; $('mapImage').alt=`${scene.dataset}: ${scene.title}, ${scene.date}`;
  $('roadLayer').src=scene.roads;
  $('referenceLayer').src='assets/validation-labels.png';
  $('referenceToggleRow').hidden=!scene.ground_truth_available;
  $('errorsToggleRow').hidden=!scene.ground_truth_available;
  $('referenceToggle').checked=scene.ground_truth_available;
  $('errorsToggle').checked=false; $('errorsLayer').hidden=true;
  $('predictionsToggle').checked=true;
  $('imageryTag').textContent=scene.key==='chimney'?'NOAA NGS · OCT 07, 2024':scene.key==='swannanoa'?'NC ORTHOIMAGERY · SPRING 2025':'SPACENET 8 · IDA 2021 · VALIDATION';
  $('mapEvidenceBadge').textContent=scene.ground_truth_available?'KNOWN LABELS · CHECK PREDICTIONS':'UNVERIFIED HELENE TRANSFER';
  $('mapEvidenceBadge').classList.toggle('labeled',scene.ground_truth_available);
  $('sceneContext').textContent=scene.key==='chimney'?'Historical NOAA response imagery. These are unverified model guesses, not known damage. Check the labeled validation sample to see what the model gets right and wrong.':scene.key==='swannanoa'?'Spring 2025 recovery imagery, not immediate storm imagery. Processed pixel values limit analysis; model transfer is unverified.':'Known flood labels are available here. Compare the reference labels with predictions and inspect the false alarms and missed floods.';
  $('reviewNotice').innerHTML=svgIcon('info')+`<span>${scene.ground_truth_available?'Compare with known labels. Model mistakes are visible.':'Unverified guesses · no damage ground truth here.'}</span>`;
  $('resultMode').textContent='Saved real inference';
  $('mapDimensions').textContent=`${scene.width} × ${scene.height}`;
  $('coordinateReadout').textContent='WGS84 · EPSG:4326';
  document.querySelectorAll('.scene-option').forEach(button=>button.classList.toggle('selected',button.dataset.scene===scene.key));
  setHash(scene.key); setView('operations');
  state.compare=scene.ground_truth_available; updateCompare();
  const response=await fetch(scene.saved_prediction); const prediction=await response.json();
  if(state.scene.key!==scene.key)return;
  state.prediction=prediction; renderPrediction();fitMap();
}
function renderScenes(){
  $('sceneList').innerHTML=state.data.scenes.map(scene=>`<button class="scene-option" data-scene="${esc(scene.key)}" aria-label="Select ${esc(scene.title)} imagery"><img src="${esc(scene.image)}" alt=""><span class="scene-text"><b>${esc(scene.title)}</b><small>${esc(scene.date)}</small><small>${scene.ground_truth_available?'Known labels · check the model':scene.key==='chimney'?'Helene · unverified transfer':'Recovery · unverified transfer'}</small></span><span class="radio-mark"></span></button>`).join('');
  $('sceneList').addEventListener('click',e=>{const button=e.target.closest('[data-scene]');if(button)selectScene(button.dataset.scene).catch(error=>toast(error.message));});
}
function mercator(lon,lat){return [lon*20037508.342789244/180, Math.log(Math.tan((90+Math.max(-85.0511,Math.min(85.0511,lat)))*Math.PI/360))*20037508.342789244/Math.PI];}
function lngLat(x,y){return [x/20037508.342789244*180,(2*Math.atan(Math.exp(y/20037508.342789244*Math.PI))-Math.PI/2)*180/Math.PI];}
function pixelPoint(coordinates){const [x,y]=mercator(...coordinates);const b=state.scene.bounds_mercator;return [(x-b[0])/(b[2]-b[0])*state.scene.width,(b[3]-y)/(b[3]-b[1])*state.scene.height];}
function polygonPath(geometry){
  const polygons=geometry.type==='MultiPolygon'?geometry.coordinates:[geometry.coordinates];
  return polygons.map(polygon=>polygon.map(ring=>ring.map((point,index)=>`${index?'L':'M'}${pixelPoint(point).map(v=>v.toFixed(2)).join(' ')}`).join(' ')+'Z').join(' ')).join(' ');
}
function centerOf(detection){
  const ring=detection.geometry.type==='MultiPolygon'?detection.geometry.coordinates[0][0]:detection.geometry.coordinates[0];
  const points=ring.slice(0,-1);return points.reduce((sum,p)=>[sum[0]+p[0]/points.length,sum[1]+p[1]/points.length],[0,0]);
}
function renderPrediction(){
  if(!state.prediction)return;
  const detections=state.prediction.detections;
  const flooded=detections.filter(d=>d.class==='flooded_road');
  $('floodCount').textContent=flooded.length; $('otherCount').textContent=detections.length-flooded.length; $('totalCount').textContent=detections.length;
  const paths=detections.map(d=>`<path class="detection ${d.id===state.selected?'selected':''}" data-detection="${esc(d.id)}" d="${polygonPath(d.geometry)}" fill="${d.class==='flooded_road'?'#ff8069':'#72cfb1'}" fill-rule="evenodd" fill-opacity="${Number($('opacity').value)/100}" stroke="${d.id===state.selected?'#f9e6bd':d.class==='flooded_road'?'#ff9d87':'#98dfc5'}" stroke-width="${d.id===state.selected?2.5:1.1}" vector-effect="non-scaling-stroke"><title>${esc(d.class.replaceAll('_',' '))} · ${pct(d.confidence)} class probability · unverified</title></path>`).join('');
  $('predictionLayer').setAttribute('viewBox',`0 0 ${state.scene.width} ${state.scene.height}`);
  $('predictionLayer').innerHTML=`<defs><clipPath id="predictionClip"><rect id="clipRect" x="0" y="0" width="${state.scene.width}" height="${state.scene.height}"/></clipPath></defs><g clip-path="url(#predictionClip)">${paths}</g>`;
  const list=detections.filter(d=>state.filter==='all'||d.class===state.filter).sort((a,b)=>b.confidence-a.confidence);
  $('detectionList').innerHTML=list.length?list.map((d,i)=>{
    const center=centerOf(d);const selected=d.id===state.selected;
    return `<button class="detection-card ${selected?'selected':''} ${d.class==='flooded_road'?'':'is-other'}" data-detection="${esc(d.id)}" aria-pressed="${selected}"><span class="detection-number">${String(i+1).padStart(2,'0')}</span><span class="detection-card-body"><b>${d.class==='flooded_road'?'Possible road flooding':'Predicted non-flooded road'}</b><span class="candidate-meta"><span>Needs review</span><span>${pct(d.confidence)} probability</span></span>${selected?`<small>${esc(d.id)}<br>${center[1].toFixed(5)}°, ${center[0].toFixed(5)}°<br>Not matched to a road segment.<br>No closure decision.</small>`:''}</span></button>`;
  }).join(''):`<div class="empty-detections">No ${state.filter==='all'?'retained observations':'flood candidates'} in this result.<br>This does not confirm road accessibility.</div>`;
  $('mapEmpty').hidden=detections.length>0;
  $('exportButton').disabled=!detections.length;
  updateLayers();updateCompare();
}
function selectDetection(id){
  const detection=state.prediction?.detections.find(d=>d.id===id);if(!detection)return;
  state.selected=id;renderPrediction();
  const position=pixelPoint(centerOf(detection));
  state.zoom=Math.max(state.zoom,1.7); const factor=state.baseWidth/state.scene.width;
  state.panX=-(position[0]-state.scene.width/2)*factor*state.zoom;
  state.panY=-(position[1]-state.scene.height/2)*factor*state.zoom;
  updateTransform();
}
function updateLayers(){
  $('predictionLayer').style.display=$('predictionsToggle').checked&&!$('errorsToggle').checked?'':'none';
  $('roadLayer').hidden=!$('roadsToggle').checked;
  $('referenceLayer').hidden=!state.scene?.ground_truth_available||!$('referenceToggle').checked||$('errorsToggle').checked;
  $('errorsLayer').hidden=!state.scene?.ground_truth_available||!$('errorsToggle').checked;
  const errors=state.scene?.ground_truth_available&&$('errorsToggle').checked;
  $('mapLegend').innerHTML=errors?'<span><i class="layer-dot mint"></i> Correct flood</span><span><i class="layer-dot amber"></i> False alarm</span><span><i class="layer-dot purple"></i> Missed flood</span>':'<span><i class="layer-dot coral"></i> Flood candidate</span><span><i class="layer-dot mint"></i> Predicted non-flooded</span>';
  if(state.prediction)$('resultMode').textContent=errors?'Saved validation error map · snapshot':state.live?`Live real inference · ${(state.prediction.latency_ms/1000).toFixed(2)} s`:'Saved real inference';
  if(state.scene?.ground_truth_available)$('mapEvidenceBadge').textContent=errors?'KNOWN LABELS · SAVED ERRORS':'KNOWN LABELS · CHECK PREDICTIONS';
}
function updateCompare(){
  const show=state.compare&&!$('errorsToggle').checked;
  $('compareButton').setAttribute('aria-pressed',String(show));
  $('compareButton').disabled=$('errorsToggle').checked;
  $('compareControl').hidden=!show;$('compareDivider').hidden=!show;
  const percent=show?Number($('compareSlider').value):0;
  const clip=$('clipRect');if(clip&&state.scene){clip.setAttribute('x',state.scene.width*percent/100);clip.setAttribute('width',state.scene.width*(1-percent/100));}
  $('compareDivider').style.left=`${percent}%`;
  $('referenceLayer').style.clipPath=show?`inset(0 ${100-percent}% 0 0)`:'none';
  $('compareLeftLabel').textContent=state.scene?.ground_truth_available?'Known labels':'Source';
  $('compareRightLabel').textContent='AI overlay';
}
function fitMap(){
  if(!state.scene)return;
  const viewport=$('mapViewport');const aspect=state.scene.width/state.scene.height;
  state.baseWidth=Math.min(viewport.clientWidth*.91,viewport.clientHeight*.9*aspect);
  $('mapStage').style.width=state.baseWidth+'px';updateTransform();
}
function updateTransform(){
  $('mapStage').style.transform=`translate(-50%,-50%) translate(${state.panX}px,${state.panY}px) scale(${state.zoom})`;
  if(!state.scene)return;
  const b=state.scene.bounds_mercator;const centerLat=lngLat((b[0]+b[2])/2,(b[1]+b[3])/2)[1];
  const metersPerPixel=(b[2]-b[0])*Math.cos(centerLat*Math.PI/180)/(state.baseWidth*state.zoom);
  const ideal=60*metersPerPixel;const factor=10**Math.floor(Math.log10(ideal));const value=[1,2,5,10].map(n=>n*factor).find(n=>n>=ideal)||ideal;
  $('scaleLine').style.width=`${Math.min(110,value/metersPerPixel)}px`;$('mapScaleLabel').textContent=value>=1000?`${(value/1000).toFixed(1)} km`:`${Math.round(value)} m`;
}
function zoomBy(factor){state.zoom=Math.max(.5,Math.min(7,state.zoom*factor));updateTransform();}
async function analyze(){
  if(state.busy||!state.scene)return;
  const request=++state.requestId;const scene=state.scene;
  state.busy=true;$('analyzeButton').disabled=true;$('mapBusy').hidden=false;
  $('analysisCaption').textContent='Processing the actual georeferenced image…';
  try{
    const prediction=await api('/ml/predict',{image_id:scene.image_id,threshold:Number($('threshold').value)/100});
    if(request!==state.requestId)return;
    if(prediction.inference_mode!=='real'||prediction.crs!=='EPSG:4326')throw new Error('The service did not return a real georeferenced prediction.');
    state.prediction=prediction;state.live=true;state.selected=null;
    $('errorsToggle').checked=false;
    $('resultMode').textContent=`Live real inference · ${(prediction.latency_ms/1000).toFixed(2)} s`;
    $('analysisCaption').textContent=`Complete · ${prediction.detections.length} polygons · ${(prediction.latency_ms/1000).toFixed(2)} seconds`;
    renderPrediction();toast('Real inference complete. Every candidate still requires review.');
  }catch(error){if(request===state.requestId){toast(error.message);$('analysisCaption').textContent='Request failed · showing the last successful result';}}
  finally{if(request===state.requestId){state.busy=false;$('analyzeButton').disabled=false;$('mapBusy').hidden=true;}}
}
function download(name,payload){const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function exportGeoJSON(){
  if(!state.prediction)return;
  const features=state.prediction.detections.map(d=>({type:'Feature',id:d.id,geometry:d.geometry,properties:{class:d.class,confidence:d.confidence,review_status:d.review_status,road_segment_ids:d.road_segment_ids,image_id:state.prediction.image_id,model_version:state.prediction.model_version,checkpoint_id:state.prediction.model_provenance?.checkpoint_id,inference_mode:state.prediction.inference_mode,source:state.prediction.source}}));
  download(`sosora-${state.scene.key}-unverified.geojson`,{type:'FeatureCollection',features});toast('Exported actual WGS84 polygons with source and review metadata.');
}
function showSource(about=false){
  const scene=state.scene;const prediction=state.prediction;
  $('sourceContent').innerHTML=about?`<h2>When roads disappear,<br>rescue can’t stop.</h2><p>SOSora connects specialized disaster-imagery analysis with rescue-planning workflows.</p><h3>What this workspace does</h3><p>A real fine-tuned SegFormer model processes georeferenced aerial imagery and returns possible flooded-road polygons within independently mapped road corridors. Export these observations for your routing application.</p><h3>How do we know what is right?</h3><p>Select <b>Louisiana · known labels</b> to compare predictions with actual flood labels and inspect mistakes. The Germany evaluation uses six new, label-blind tiles. The Helene images do not have flood labels: their overlays are unverified transfer guesses.</p><h3>Current integrations</h3><p>Vision runs locally. Nemotron parses reports with a real provider when configured. Evidence briefs count supplied region records with a deterministic template. Predictions do not create authoritative road closures or rescue routes.</p><a href="training.html">Open the detailed validation snapshot ↗</a>`:
    `<h2>${esc(scene.title)}</h2><p>${esc(scene.subtitle)} · ${esc(scene.period)}</p><div class="source-fact"><span>Imagery date</span><b>${esc(scene.date)}</b></div><div class="source-fact"><span>Dataset</span><b>${esc(scene.dataset)}</b></div><div class="source-fact"><span>Flood ground truth</span><b>${scene.ground_truth_available?'Available · validation labels':'Unavailable · unverified transfer'}</b></div><div class="source-fact"><span>Inference</span><b>${state.live?'Live':'Saved'} · real model</b></div><h3>Source</h3><p><a href="${esc(scene.source_url)}" target="_blank" rel="noopener noreferrer">Official imagery source ↗</a>${scene.date_evidence_url?`<br><a href="${esc(scene.date_evidence_url)}" target="_blank" rel="noopener noreferrer">Capture-date evidence ↗</a>`:''}</p><h3>Interpretation limits</h3><ul>${scene.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}<li>Model probabilities are not calibrated safety scores. No road closure or safe route is established.</li></ul><h3>Checkpoint identity</h3><code>${esc(prediction?.model_provenance?.checkpoint_id||state.data.checkpoint_id)}</code><h3>Image registration</h3><code>${esc(scene.image_id)}</code>`;
  $('sourceDialog').showModal();
}
function lineChart(series,bounded=false){
  const w=550,h=210,left=36,right=530,top=20,bottom=174;const count=series[0].values.length;
  const max=bounded?1:Math.max(...series.flatMap(s=>s.values))*1.15;
  const x=i=>left+i*(right-left)/(count-1);const y=v=>bottom-v/max*(bottom-top);
  let html=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Saved training measurements by epoch">`;
  for(const v of [0,max/2,max])html+=`<path d="M${left} ${y(v)}H${right}" stroke="#2e414c"/><text x="0" y="${y(v)+4}" fill="#6e8c9e" font-size="9">${v.toFixed(2)}</text>`;
  const selected=state.data.training.selected_epoch-1;
  html+=`<path d="M${x(selected)} ${top}V${bottom}" stroke="#b2c3bc66" stroke-dasharray="3 4"/>`;
  for(const s of series)html+=`<polyline points="${s.values.map((v,i)=>`${x(i)},${y(v)}`).join(' ')}" fill="none" stroke="${s.color}" stroke-width="2.2"/>`;
  for(let i=0;i<count;i++)html+=`<text x="${x(i)}" y="196" fill="#7592a3" font-size="9" text-anchor="middle">${i+1}</text>`;
  return html+'</svg>';
}
function renderEvidence(){
  const evaluation=state.data.external_evaluation;const m=evaluation.metrics.tuned;const b=evaluation.metrics.baseline;
  $('evidenceCards').innerHTML=[['External F1',m.f1.toFixed(3),'Frozen model · Germany'],['Intersection over union',m.iou.toFixed(3),'Identical labeled road pixels'],['Previously untouched tiles',evaluation.tile_count,'Label-blind sample selection'],['Labeled pixels',number(m.valid_pixels),'Known road flood state only']].map(([label,value,note])=>`<article class="evidence-stat"><small>${esc(label)}</small><strong>${esc(value)}</strong><span>${esc(note)}</span></article>`).join('');
  $('comparisonChart').innerHTML=[['Saved initialization',b.f1,false],['Fine-tuned SOSora',m.f1,true]].map(([label,value,tuned])=>`<div class="comparison-row ${tuned?'tuned':''}"><div><span>${label}</span><b>F1 ${value.toFixed(3)}</b></div><div class="bar-track"><div class="bar-fill" style="width:${value*100}%"></div></div></div>`).join('');
  $('metricsTable').innerHTML=`<table><thead><tr><th>Model</th><th>Precision</th><th>Recall</th><th>IoU</th></tr></thead><tbody><tr><td>Initialization</td><td>${b.precision.toFixed(3)}</td><td>${b.recall.toFixed(3)}</td><td>${b.iou.toFixed(3)}</td></tr><tr><td>Fine-tuned</td><td>${m.precision.toFixed(3)}</td><td>${m.recall.toFixed(3)}</td><td>${m.iou.toFixed(3)}</td></tr></tbody></table>`;
  $('confusionMatrix').innerHTML=[[m.tp,'Correctly predicted flood','good'],[m.fp,'False flood alarms','bad'],[m.fn,'Missed flooded pixels','bad'],[m.tn,'Correct non-flooded pixels','good']].map(([n,label,cls])=>`<div class="confusion-cell ${cls}"><strong>${number(n)}</strong><small>${label}</small></div>`).join('');
  const history=state.data.training.history;
  $('f1Chart').innerHTML=lineChart([{values:history.map(e=>e.validation.f1),color:'#8ed5b7'}],true);
  $('lossChart').innerHTML=lineChart([{values:history.map(e=>e.train_loss),color:'#7cbfd1'},{values:history.map(e=>e.validation.loss),color:'#ffa86e'}]);
}
async function checkConnections(){
  try{await api('/health');$('systemState').innerHTML='<i class="status-dot"></i> Local model connected';}
  catch{$('systemState').innerHTML='<i class="status-dot offline"></i> Model offline · saved evidence';}
  try{
    const result=await api('/ml/llm-health');state.provider=!!result.configured;
    $('llmState').textContent=state.provider?'PROVIDER CONFIGURED':'PROVIDER NOT CONNECTED';
    $('llmState').classList.toggle('mint-chip',state.provider);
  }catch{$('llmState').textContent='PROVIDER UNAVAILABLE';}
}
function renderIncident(incident){
  const tags=values=>values.length?`<div class="fact-tags">${values.map(v=>`<span>${esc(v)}</span>`).join('')}</div>`:'<p>Not reported</p>';
  $('incidentResult').className='';$('incidentResult').innerHTML=`<div class="incident-fact"><label>Reported location · not geocoded</label><p>${esc(incident.location_text||'Location not provided')}</p></div><div class="incident-fact"><label>Reported people</label><p>${incident.people_count===null?'Not reported':esc(incident.people_count)}</p></div><div class="incident-fact"><label>Reported needs</label>${tags(incident.needs)}</div><div class="incident-fact"><label>Reported hazards</label>${tags(incident.hazards)}</div><div class="incident-fact"><label>Still missing</label>${tags(incident.missing_information)}</div><div class="incident-fact"><label>Summary · requires review</label><p>${esc(incident.summary)}</p></div>`;
  $('exportIncident').hidden=false;$('explainIncident').disabled=false;
}
async function parseIncident(){
  const report=$('incidentReport').value.trim();if(!report){toast('Enter an emergency report first.');$('incidentReport').focus();return;}
  $('parseIncident').disabled=true;$('incidentNotice').hidden=true;
  try{const result=await api('/ml/incident/parse',{report});state.incident=result.incident;renderIncident(result.incident);toast(`Real ${result.provider} inference completed. Review the extracted facts.`);}
  catch(error){$('incidentNotice').textContent=error.message.includes('not configured')?'Nemotron is not connected yet. Configure the provider key in the local ML service, then retry. This report has not been processed by the model.':error.message;$('incidentNotice').hidden=false;}
  finally{$('parseIncident').disabled=false;}
}
async function explainIncident(){
  if(!state.prediction)return;
  const evidence=state.prediction.detections.slice(0,12).map(d=>({evidence_id:d.id,prediction_class:d.class,observation:`Unverified model prediction of ${d.class.replaceAll('_',' ')} on ${state.scene.title} imagery dated ${state.scene.date}; not an authoritative road closure.`,source:state.scene.dataset,confidence:d.confidence}));
  if(!evidence.length){toast('Select imagery with model observations first.');return;}
  $('explainIncident').disabled=true;
  try{const result=await api('/ml/incident/explain',{incident:state.incident,road_evidence:evidence});$('briefResult').hidden=false;$('briefResult').textContent=result.explanation.explanation;const note=document.createElement('small');note.textContent=`Deterministic brief · supplied records only · unverified · evidence: ${result.explanation.evidence_ids.join(', ')} · ${result.explanation.uncertainty.join(' ')}`;$('briefResult').appendChild(note);}
  catch(error){toast(error.message);}
  finally{$('explainIncident').disabled=false;}
}
function attachEvents(){
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{setView(button.dataset.view);setHash(button.dataset.view==='operations'?state.scene.key:button.dataset.view);}));
  $('analyzeButton').addEventListener('click',analyze);
  $('threshold').addEventListener('input',e=>{$('thresholdValue').textContent=e.target.value+'%';$('analysisCaption').textContent='Run analysis to apply the updated threshold';});
  for(const id of ['predictionsToggle','roadsToggle','referenceToggle','errorsToggle'])$(id).addEventListener('change',()=>{updateLayers();updateCompare();if(id==='errorsToggle'&&$(id).checked)toast('Saved validation errors: green correct flood, amber false alarm, purple missed flood.');});
  $('opacity').addEventListener('input',()=>{$('predictionLayer').querySelectorAll('path.detection').forEach(p=>p.setAttribute('fill-opacity',Number($('opacity').value)/100));});
  $('compareButton').addEventListener('click',()=>{state.compare=!state.compare;updateCompare();});
  $('compareSlider').addEventListener('input',updateCompare);
  document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{state.filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b===button));renderPrediction();}));
  $('detectionList').addEventListener('click',e=>{const button=e.target.closest('[data-detection]');if(button)selectDetection(button.dataset.detection);});
  $('predictionLayer').addEventListener('click',e=>{const path=e.target.closest('[data-detection]');if(path)selectDetection(path.dataset.detection);});
  $('exportButton').addEventListener('click',exportGeoJSON);
  for(const id of ['sourceDetails','provenanceTop'])$(id).addEventListener('click',()=>showSource());
  $('helpButton').addEventListener('click',()=>showSource(true));$('closeSource').addEventListener('click',()=>$('sourceDialog').close());
  $('sourceDialog').addEventListener('click',e=>{if(e.target===$('sourceDialog')){$('sourceDialog').close();}});
  $('zoomIn').addEventListener('click',()=>zoomBy(1.25));$('zoomOut').addEventListener('click',()=>zoomBy(.8));
  const reset=()=>{state.zoom=1;state.panX=0;state.panY=0;fitMap();};$('resetMap').addEventListener('click',reset);$('fitButton').addEventListener('click',reset);
  $('mapImage').addEventListener('load',fitMap);new ResizeObserver(fitMap).observe($('mapViewport'));
  $('mapViewport').addEventListener('wheel',e=>{e.preventDefault();zoomBy(e.deltaY<0?1.08:1/1.08);},{passive:false});
  let drag=null;
  $('mapViewport').addEventListener('pointerdown',e=>{if(e.target.closest('button,input,.compare-control,[data-detection]'))return;drag={x:e.clientX,y:e.clientY,px:state.panX,py:state.panY};$('mapViewport').setPointerCapture(e.pointerId);$('mapViewport').classList.add('dragging');});
  $('mapViewport').addEventListener('pointermove',e=>{
    if(drag){state.panX=drag.px+e.clientX-drag.x;state.panY=drag.py+e.clientY-drag.y;updateTransform();}
    if(!state.scene)return;
    const rect=$('mapStage').getBoundingClientRect();const fx=(e.clientX-rect.left)/rect.width,fy=(e.clientY-rect.top)/rect.height;
    if(fx>=0&&fx<=1&&fy>=0&&fy<=1){const b=state.scene.bounds_mercator;const p=lngLat(b[0]+fx*(b[2]-b[0]),b[3]-fy*(b[3]-b[1]));$('coordinateReadout').textContent=`${p[1].toFixed(5)}°, ${p[0].toFixed(5)}°`;}
  });
  for(const event of ['pointerup','pointercancel'])$('mapViewport').addEventListener(event,()=>{drag=null;$('mapViewport').classList.remove('dragging');});
  $('mapViewport').addEventListener('keydown',e=>{if(e.key==='+')zoomBy(1.25);if(e.key==='-')zoomBy(.8);if(e.key==='Enter')analyze();});
  $('mobileObservations').addEventListener('click',()=>$('observationsPanel').classList.toggle('mobile-open'));
  $('goValidation').addEventListener('click',()=>selectScene('validation'));
  $('incidentReport').addEventListener('input',()=>{$('reportCount').textContent=`${number($('incidentReport').value.length)} / 12,000`;});
  $('loadExample').addEventListener('click',()=>{$('incidentReport').value='Three people are stranded near Main Street in Chimney Rock. One needs insulin. Water is rising outside. We have no vehicle.';$('incidentReport').dispatchEvent(new Event('input'));toast('Loaded an illustrative report. This is not a real emergency message.');});
  $('parseIncident').addEventListener('click',parseIncident);$('explainIncident').addEventListener('click',explainIncident);
  $('exportIncident').addEventListener('click',()=>download('sosora-incident-unverified.json',{incident:state.incident,review_status:'unverified'}));
  window.addEventListener('hashchange',()=>{const key=location.hash.slice(1);if(['evidence','incidents'].includes(key))setView(key);else if(state.data.scenes.some(s=>s.key===key)){if(state.scene.key!==key)selectScene(key);else setView('operations');}});
}
async function init(){
  try{
    const response=await fetch('console-data.json',{cache:'no-store'});if(!response.ok)throw new Error('The imagery catalog is unavailable.');state.data=await response.json();
    renderScenes();attachEvents();renderEvidence();
    const initial=location.hash.slice(1);await selectScene(state.data.scenes.some(s=>s.key===initial)?initial:'chimney');
    if(['evidence','incidents'].includes(initial)){setView(initial);setHash(initial);}checkConnections();setInterval(checkConnections,20000);
  }catch(error){toast(error.message);console.error(error);}
}
init();
