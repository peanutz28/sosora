"""Build an offline validation-only snapshot from saved real training/inference evidence."""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom

ROOT=Path(__file__).resolve().parents[2]


def chart(series, title, selected, bounded=False):
    width,height=600,220
    maximum=1 if bounded else max(value for _,values,_ in series for value in values)*1.1
    maximum=max(maximum,.01)
    count=len(series[0][1]); x=lambda i:45+i*520/max(count-1,1)
    y=lambda v:180-v/maximum*140
    out=[f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{title}"><title>{title}</title>']
    for value in [0,maximum/2,maximum]:
        out.append(f'<path d="M45 {y(value)} H575" stroke="#354455"/><text x="5" y="{y(value)+4}" fill="#a8b8c8" font-size="12">{value:.2f}</text>')
    out.append(f'<path d="M{x(selected-1)} 30 V180" stroke="#ffffff" stroke-dasharray="4 4" opacity=".5"/>')
    for name,values,color in series:
        points=' '.join(f'{x(i):.1f},{y(v):.1f}' for i,v in enumerate(values))
        out.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
    for i in range(count):
        out.append(f'<text x="{x(i)}" y="202" text-anchor="middle" fill="#a8b8c8" font-size="12">{i+1}</text>')
    out.append('</svg>')
    return ''.join(out)


def build(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    pred=json.loads((ROOT/'ml/artifacts/demo_flood_native_validation/prediction.json').read_text())
    rows=json.loads((ROOT/'data/manifests/road_demo_validation.json').read_text())
    row=next(r for r in rows if r['image_id']==pred['image_id'])
    if row.get('split')!='validation': raise ValueError('Viewer permits validation imagery only')
    cfg=json.loads((ROOT/'ml/artifacts/sn8_native_cpu_v2/evaluation_config.json').read_text())
    evaluation=json.loads((ROOT/'ml/artifacts/sn8_native_cpu_v2_validation/evaluation.json').read_text())
    if evaluation['split']!='validation': raise ValueError('Validation metrics required')
    if pred['model_provenance']['checkpoint_id']!=evaluation['provenance']['checkpoint_id']:
        raise ValueError('Prediction/evaluation checkpoints differ')
    mask=np.asarray(Image.open(ROOT/'ml/artifacts/sn8_pilot/10400100684A4B00_1_17_85_mask.png'))
    with rasterio.open(ROOT/row['path']) as src:
        rgb=np.moveaxis(src.read([1,2,3]),0,-1)
        if mask.shape!=rgb.shape[:2]: raise ValueError('Reference and raster dimensions differ')
        polygons=[(transform_geom(pred['crs'],src.crs,d['geometry']),1) for d in pred['detections'] if d['class']=='flooded_road']
        flooded=rasterize(polygons,out_shape=mask.shape,transform=src.transform,dtype='uint8').astype(bool) if polygons else np.zeros(mask.shape,bool)
    Image.fromarray(rgb).save(output/'source.jpg',quality=92)
    reference=np.zeros((*mask.shape,4),dtype='uint8')
    reference[mask==0]=[45,220,130,225]; reference[mask==1]=[255,75,85,235]
    Image.fromarray(reference).save(output/'reference.png')
    valid=mask!=255
    tp=valid & (mask==1) & flooded; fp=valid & (mask==0) & flooded; fn=valid & (mask==1) & ~flooded
    errors=np.zeros_like(reference); errors[tp]=[45,220,130,245]; errors[fp]=[255,185,40,245]; errors[fn]=[185,105,255,245]
    Image.fromarray(errors).save(output/'errors.png')
    shutil.copyfile(ROOT/'ml/artifacts/demo_flood_native_validation/overlay.jpg',output/'prediction.jpg')
    counts={k:int(v.sum()) for k,v in [('tp',tp),('fp',fp),('fn',fn)]}
    history=cfg['history']; selected=cfg['selected_epoch']; chosen=next(r for r in history if r['epoch']==selected)
    loss=chart([('Training',[r['train_loss'] for r in history],'#54c8ff'),('Validation',[r['validation']['loss'] for r in history],'#ffbe55')],'Loss by epoch',selected)
    f1=chart([('Validation crop F1',[r['validation']['f1'] for r in history],'#6ee7ad')],'Validation crop F1 by epoch',selected,True)
    provenance=pred['model_provenance']; when=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    cards=''
    for title,note,foreground in [('Aerial source','Validation tile · Hurricane Ida 2021 · 1300 × 1300',None),('Reference labels','Green non-flooded road · red flooded road · unlabeled pixels transparent','reference.png'),('Actual model prediction','Saved native tiled prediction · red flooded road · green non-flooded road','prediction.jpg'),('Prediction errors','Green correct flood · amber false alarm · purple missed flood','errors.png')]:
        extra=f'<img class="layer" src="{foreground}" alt="{title} overlay">' if foreground else ''
        cards+=f'<article><h2>{title}</h2><p>{note}</p><div class="scene"><img src="source.jpg" alt="Aerial validation source">{extra}</div></article>'
    helene=next(r for r in rows if r['image_id']=='helene_swannanoa_spring2025')
    with rasterio.open(ROOT/helene['path']) as src:
        preview=Image.fromarray(np.moveaxis(src.read([1,2,3]),0,-1))
        preview.thumbnail((1300,1300)); preview.save(output/'helene_preview.jpg',quality=90)
    helene_prediction_path=ROOT/'ml/artifacts/demo_helene_native/prediction.json'
    helene_transfer=''
    if helene_prediction_path.is_file():
        transfer=json.loads(helene_prediction_path.read_text())
        if transfer.get('inference_mode')!='real': raise ValueError('Helene snapshot must be real inference')
        shutil.copyfile(ROOT/'ml/artifacts/demo_helene_native/overlay.jpg',output/'helene_prediction.jpg')
        class_counts={label:sum(d['class']==label for d in transfer['detections']) for label in sorted({d['class'] for d in transfer['detections']})}
        detail=html.escape(', '.join(f'{count} {label}' for label,count in class_counts.items()) or 'No detections')
        transfer_provenance=transfer['model_provenance']
        helene_transfer=f'<h2>Actual Helene zero-shot transfer snapshot</h2><p>{detail}. Model: <code>sn8_native_cpu_v2</code> · run <code>{html.escape(transfer_provenance["run_id"])}</code>. This is the same selected model, applied without Helene fine-tuning.</p><img src="helene_prediction.jpg" alt="Real unverified flood-model transfer overlay on spring 2025 Helene recovery imagery" style="width:100%;max-width:650px;border-radius:8px"><p><b>No flood ground truth and no Helene accuracy measurement.</b> The spring 2025 imagery service describes no unusual flooding. Model positives may be false alarms and are not proof of storm damage, road closure, or current flooding.</p>'
    source_url=html.escape(row['source_url'],quote=True)
    helene_url=html.escape(helene['source_url'],quote=True)
    provenance_card=f'<div class="panel"><h2>Which storm and imagery?</h2><p><b>Main validation view: SpaceNet 8 Louisiana East · Hurricane Ida 2021, NOT Helene.</b> Exact tile capture date is unverified. <a href="{source_url}">Original SpaceNet source raster</a> · CC-BY-SA-4.0. ADE20K names the scene model’s pretraining dataset, not the aerial imagery source; the separate ADE demo also uses SpaceNet Ida imagery.</p><h2 id="swannanoa">Available Helene recovery imagery</h2><p>Swannanoa, North Carolina · NC Helene Orthoimagery 2025 · spring 2025 recovery period, NOT immediate September 2024 storm imagery. Exact tile capture date is unverified. Bounding box: −82.323, 35.603 to −82.313, 35.613. <a href="{helene_url}">NC imagery source service</a>. Confirm NC redistribution terms before publishing. <a href="https://www.nconemap.gov/maps/06367a1aa3c044b890ca21cdbb2804e2/about">NCOneMap source item</a> states that individual pixel values in the spring 2025 service may have been adjusted: it is intended for visual interpretation and general mapping, and detailed pixel-value analysis is not recommended. Treat model transfer on this imagery with that radiometric limitation.</p><img src="helene_preview.jpg" alt="Swannanoa spring 2025 recovery aerial imagery, no model overlay or ground-truth labels" style="width:100%;max-width:650px;border-radius:8px"><p>No flood ground truth is available for this Helene image. The prior ADE scene model produced zero detections on this asset; that is a separate historical scene-model result and does not mean no flood impact.</p>{helene_transfer}</div>'
    external_path=ROOT/'ml/artifacts/sn8_frozen_external/evaluation/evaluation.json'
    evaluation_context=''
    if external_path.is_file():
        external=json.loads(external_path.read_text())
        em=external['metrics']['tuned']; eb=external['metrics']['baseline']
        positive_share=(em['tp']+em['fn'])/em['valid_pixels']
        evaluation_context=f'<div class="panel" style="border-color:#aa8050"><h2>Latest frozen external evaluation · Germany</h2><p><b>F1 {em["f1"]:.4f} · IoU {em["iou"]:.4f}</b> versus same-initialization baseline F1 {eb["f1"]:.4f}. Six tiles selected without inspecting flood labels; model, configuration, and 0.5 binary decision threshold were frozen before new labels were inspected. Precision {em["precision"]:.3f} · recall {em["recall"]:.3f} · flood-positive share {positive_share:.1%} of labeled road pixels. False alarms and missed floods remain substantial.</p><p>The reused Louisiana four-tile F1 of 0.6742 is <b>not a pristine holdout</b>: earlier results and images informed diagnosis. Germany results are not Helene accuracy and do not support a broad deployment claim. Images and error maps below remain validation-only; no external evaluation imagery is displayed.</p></div>'
    noaa_card=''
    noaa_prediction=ROOT/'ml/artifacts/demo_noaa_chimney_20241007/prediction.json'
    if noaa_prediction.is_file():
        noaa=json.loads(noaa_prediction.read_text())
        if noaa.get('inference_mode')!='real': raise ValueError('NOAA snapshot must be real inference')
        noaa_row=json.loads((ROOT/'data/manifests/noaa_chimney_mainst_20241007.json').read_text())[0]
        shutil.copyfile(ROOT/'ml/artifacts/noaa_chimney_mainst_20241007/source_preview.jpg',output/'noaa_source.jpg')
        shutil.copyfile(ROOT/'ml/artifacts/demo_noaa_chimney_20241007/overlay.jpg',output/'noaa_prediction.jpg')
        noaa_counts={label:sum(d['class']==label for d in noaa['detections']) for label in sorted({d['class'] for d in noaa['detections']})}
        noaa_detail=html.escape(', '.join(f'{count} {label}' for label,count in noaa_counts.items()))
        noaa_run=html.escape(noaa['model_provenance']['run_id'])
        noaa_card=f'<section id="chimney" class="panel"><h2>Chimney Rock Main Street · NOAA · October 7, 2024</h2><p>Actual Hurricane Helene response imagery, NOAA NGS layer <code>{html.escape(noaa_row["source_layer"])}</code>. The dated layer is October 7, 2024; exact flight time is unknown. <a href="{html.escape(noaa_row["date_evidence_url"],quote=True)}">Official NOAA date evidence</a> · <a href="{html.escape(noaa_row["source_url"],quote=True)}">NOAA imagery service</a>. Four processed XYZ tiles mosaicked into a 512 × 512 EPSG:3857 image; this is visual mapping imagery, not raw sensor radiometry.</p><div class="grid"><article><h2>Actual source</h2><img src="noaa_source.jpg" alt="NOAA October 7 2024 Chimney Rock Main Street imagery" style="width:100%;border-radius:8px"></article><article><h2>Actual model transfer overlay</h2><img src="noaa_prediction.jpg" alt="Real unverified frozen-model transfer predictions on Chimney Rock" style="width:100%;border-radius:8px"></article></div><p>{noaa_detail}. Same frozen <code>sn8_native_cpu_v2</code> model; run <code>{noaa_run}</code>. Red indicates predicted flooded road; green predicted non-flooded road. The independent state-maintained-road ROI uses current NCDOT geometry from June 2026, which may differ from October 2024 roads.</p><p><b>No flood ground truth or accuracy measurement exists for this image.</b> The 27 flood-positive polygons are unverified transfer predictions and may be false positives. They are not proof of closure, damage, or safe travel. Louisiana satellite-to-NOAA aerial domain shift, processed image radiometry, missing roads, and the road-data temporal mismatch can produce false alarms or misses.</p></section>'
    content=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SOSora · Training snapshot</title>
<style>:root{{--opacity:.85;color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#101923;color:#e6edf5;font:15px/1.55 system-ui,sans-serif}}main{{max-width:1450px;margin:auto;padding:30px}}.eyebrow{{color:#6ee7ad;letter-spacing:.12em;font-size:12px;text-transform:uppercase}}h1{{font-size:36px;line-height:1.15;margin:8px 0}}p{{color:#aebdcd;margin:6px 0 16px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}article,.panel{{background:#192532;border:1px solid #314151;border-radius:14px;padding:18px;margin:0 0 18px}}h2{{font-size:19px;margin:0 0 5px}}.scene{{position:relative;line-height:0}}.scene img{{width:100%;border-radius:8px}}.scene .layer{{position:absolute;inset:0;opacity:var(--opacity)}}.stats{{display:flex;gap:18px;flex-wrap:wrap;margin:22px 0}}.stat{{padding:14px 20px;border-radius:12px;background:#203140;min-width:180px}}strong{{font-size:27px;display:block;color:#f5f8fb}}small{{color:#aebdcd}}code{{overflow-wrap:anywhere;color:#8ed9ff}}a{{color:#8ed9ff}}label{{display:block;margin:12px 0}}svg{{width:100%}}.good{{color:#6ee7ad}}.amber{{color:#ffbe55}}.purple{{color:#c38cff}}@media(max-width:750px){{.grid{{grid-template-columns:1fr}}main{{padding:16px}}h1{{font-size:28px}}}}</style>
<main><div class="eyebrow">SOSora / validation workspace</div><h1>See what the model learned</h1><p>Saved snapshot · built {when} · rebuild to refresh. Real saved predictions; this page is not a live training feed.</p>
<nav class="panel"><a href="#validation">Validation comparisons</a> &nbsp; · &nbsp; <a href="#swannanoa">Swannanoa 2025</a> &nbsp; · &nbsp; <a href="#chimney">Chimney Rock Oct 2024</a> &nbsp; · &nbsp; <a href="#curves">Training curves</a></nav>{evaluation_context}<div class="stats"><div class="stat"><small>Selected checkpoint</small><strong>Epoch {selected} / {cfg['epochs']}</strong><small>Chosen using crop validation F1</small></div><div class="stat"><small>Selected crop validation F1</small><strong>{chosen['validation']['f1']:.3f}</strong><small>Native 256 px validation crops</small></div><div class="stat"><small>Full-tile validation F1</small><strong>{evaluation['metrics']['tuned']['f1']:.3f}</strong><small>Two validation tiles · argmax</small></div><div class="stat"><small>Reference-labeled pixels</small><strong>{int(valid.sum()):,}</strong><small>Shown tile only; unknown pixels ignored</small></div></div>
<div class="panel"><h2>How to read this view</h2><p>Reference labels show flood state along annotated roads. Prediction uses an independent road geometry ROI, without flood labels. A false alarm means the model predicted flood on a labeled non-flooded road; a missed flood means a labeled flooded road was not predicted flooded. Unknown pixels are excluded. Residual image/label alignment errors remain possible.</p><label>Overlay opacity <input aria-label="Overlay opacity" type="range" min="0" max="1" step=".05" value=".85" oninput="document.documentElement.style.setProperty('--opacity',this.value)"></label><span class="good">● Correct flood: {counts['tp']:,}</span> &nbsp; <span class="amber">● False alarm: {counts['fp']:,}</span> &nbsp; <span class="purple">● Missed flood: {counts['fn']:,}</span><p><small>Error counts above use the saved thresholded polygon snapshot on this one tile. The full-tile score above uses argmax on both validation tiles, so these are different measurements.</small></p></div>
<div id="validation" class="grid">{cards}</div>{provenance_card}{noaa_card}<div id="curves" class="grid"><article><h2>Loss over training</h2><p><span style="color:#54c8ff">Blue: training</span> · <span class="amber">Amber: crop validation</span> · lower is better</p>{loss}</article><article><h2>Validation crop F1</h2><p>Green: F1 · dashed line: selected epoch · higher is better</p>{f1}</article></div>
<div class="panel"><h2>Checkpoint and interpretation</h2><p>Run: <code>{html.escape(provenance['run_id'])}</code><br>Model: <code>sn8_native_cpu_v2</code><br>Checkpoint: <code>{html.escape(provenance['checkpoint_id'])}</code><br>Task: <code>{html.escape(provenance['task'])}</code><br>Validation image: <code>{html.escape(pred['image_id'])}</code></p><p>Class 0 means non-flooded road, not generic background or verified passability. Class 1 means flooded road. These predictions remain unverified and do not establish road closure or safety. This tiny same-event validation set is development evidence. Crop validation and full-tile validation measure different inputs and support; neither is a deployment guarantee.</p></div></main></html>'''
    (output/'training.html').write_text(content)
    (output/'snapshot.json').write_text(json.dumps({'built_at':when,'split':'validation','image_id':pred['image_id'],'selected_epoch':selected,'crop_validation_f1':chosen['validation']['f1'],'full_tile_validation_f1':evaluation['metrics']['tuned']['f1'],'snapshot_error_pixels':counts,'provenance':provenance},indent=2))
    print(json.dumps({'output':str(output),'snapshot_error_pixels':counts,'selected_epoch':selected},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,default=ROOT/'docs/ml/viewer')
    build(parser.parse_args().output)
