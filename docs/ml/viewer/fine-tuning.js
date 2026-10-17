'use strict';
const byId = id => document.getElementById(id);
const base = 'assets/finetuning/';
const fmt = n => n === null || n === undefined ? 'undefined' : Number(n).toFixed(4);
let experiment;
function metricsTable(metrics){
  const table=document.createElement('table');
  const head=table.createTHead().insertRow();
  for(const title of ['Model / control','Flood F1','Flood IoU','Precision','Recall']){const th=document.createElement('th');th.textContent=title;head.appendChild(th);}
  const body=table.createTBody();
  for(const [key,label] of [['baseline','Saved initialization · random binary head'],['tuned','Fine-tuned · epoch 9'],['all_positive','Every labeled road flooded']]){
    const m=metrics[key];const row=body.insertRow();if(key==='tuned')row.className='tuned';
    for(const value of [label,...['f1','iou','precision','recall'].map(k=>fmt(m[k]))]){const cell=row.insertCell();cell.textContent=value;}
  }
  return table;
}
function selectScene(){
  const scene=experiment.scenes[Number(byId('sceneSelect').value)];
  document.querySelectorAll('.source').forEach(img=>img.src=base+scene.prefix+'-source.jpg');
  document.querySelectorAll('.roi').forEach(img=>img.src=base+scene.prefix+'-roi.png');
  for(const [id,suffix] of [['referenceImage','reference'],['baselineImage','baseline'],['tunedImage','tuned']])byId(id).src=base+scene.prefix+'-'+suffix+'.png';
  byId('sceneNote').textContent=`SpaceNet 8 Louisiana East · Hurricane Ida 2021 · validation tile ${scene.id} · ${scene.size.join(' × ')} original pixels. Exact capture date unknown.`;
  byId('sourceUrl').href=scene.source_url;
  const m=scene.metrics.tuned;
  byId('imageSupport').textContent=`${m.valid_pixels.toLocaleString()} known road-label pixels; ${(m.tp+m.fn).toLocaleString()} flooded. Identical support, 256px native windows and binary argmax for baseline, tuned and constant control. ${scene.roi_labeled_coverage.toLocaleString()} scored pixels lie inside the displayed independent ROI. No polygon filtering or adjustable threshold changes these saved scores.`;
  const b=scene.metrics.baseline;
  byId('imageSupport').textContent+=` False-positive pixels: ${b.fp.toLocaleString()} before → ${m.fp.toLocaleString()} after; missed flooded pixels: ${b.fn.toLocaleString()} before → ${m.fn.toLocaleString()} after.`;
  byId('imageMetrics').replaceChildren(metricsTable(scene.metrics));
}
async function load(){
  try{
    const response=await fetch(base+'experiment.json',{cache:'no-store'});if(!response.ok)throw new Error('Comparison assets unavailable. Rebuild privately from the saved checkpoints.');experiment=await response.json();
    experiment.scenes.forEach((scene,i)=>{const option=document.createElement('option');option.value=i;option.textContent=`${i+1} · ${scene.metrics.tuned.tp+scene.metrics.tuned.fn?'Flood-positive':'Dry'} validation tile · ${scene.id.split('_').slice(-2).join('_')}`;byId('sceneSelect').appendChild(option);});
    byId('sceneSelect').addEventListener('change',selectScene);selectScene();
    byId('validationMetrics').replaceChildren(metricsTable(experiment.validation_metrics));
    byId('externalMetrics').replaceChildren(metricsTable(experiment.external_metrics));
    byId('checkpointDetails').textContent=`Tuned checkpoint: ${experiment.hashes.tuned}. Saved initialization: ${experiment.hashes.baseline}. Run: ${experiment.experiment.run_id}.`;
  }catch(error){byId('loadError').textContent=error.message;byId('loadError').hidden=false;}
}
byId('alpha').addEventListener('input',e=>document.documentElement.style.setProperty('--overlay',Number(e.target.value)/100));
byId('roiToggle').addEventListener('change',e=>document.querySelectorAll('.roi').forEach(img=>img.hidden=!e.target.checked));
load();
