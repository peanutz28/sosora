"""Prepare once, score v2 and the frozen V3 once, and render saved predictions only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ml.experiments.v3_protocol import (ROOT, FINAL_DEADLINE, preflight,
    committed_selection, validate_final_rows, begin_attempt, finish_attempt, sha256)

EVIDENCE=ROOT/'docs/ml/evidence/v3_2026-10-18'
DATA=ROOT/'ml/artifacts/v3_experiment/final_20261018'
SELECTION=EVIDENCE/'selection.json'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def deadline():
    if datetime.now(timezone.utc)>=FINAL_DEADLINE:
        raise ValueError('Final deadline reached; no further final processing')


def prepare():
    # This guard precedes imports/calls that can read final annotations or imagery.
    selection,commit=committed_selection(SELECTION)
    protocol=preflight()
    request={'phase':'prepare','selection':commit,'source_sha256':sha256(Path(__file__)),
             'protocol_sha256':protocol['protocol_sha256'],'final_ids':protocol['final_ids']}
    ledger=EVIDENCE/'final_preparation_ledger.json'
    state=begin_attempt(ledger,request)
    try:
        import rasterio
        from rasterio.warp import reproject,Resampling
        from scripts.ml.prepare_v3_experiment import (OUT,fetch,read_allowed_labels,
            make_masks,alignment_screen,save_image,check_budget)
        rows=[next(row for row in protocol['rows'] if row['id']==ident) for ident in protocol['final_ids']]
        labels={}
        references={'Louisiana-East_Training_Public':ROOT/'ml/artifacts/sn8_pilot/reference.csv',
                    'Germany_Training_Public':ROOT/'ml/artifacts/sn8_frozen_external/Germany_Training_Public_reference.csv'}
        for dataset,path in references.items():
            labels.update(read_allowed_labels(path,{row['id'] for row in rows if row['dataset']==dataset}))
        DATA.mkdir(parents=True,exist_ok=True)
        manifest=[];quality=[]
        for row in rows:
            deadline()
            with rasterio.open(OUT/'raw'/row['pre-event image']) as reference:
                before=np.moveaxis(reference.read([1,2,3]),0,-1)
                target_base=make_masks(labels.get(row['id'],[]),(reference.height,reference.width))
                options=[]
                for field in ('post-event image 1','post-event image 2'):
                    if not row.get(field):continue
                    post=fetch(row,field,'POST-event')
                    with rasterio.open(post) as source:
                        if source.count<3 or source.dtypes[:3]!=('uint8','uint8','uint8'):
                            raise ValueError('Expected public uint8 RGB source')
                        rgb=np.zeros((3,reference.height,reference.width),dtype='uint8')
                        coverage=np.zeros((reference.height,reference.width),dtype='uint8')
                        for band in range(3):
                            reproject(source.read(band+1),rgb[band],src_transform=source.transform,
                                src_crs=source.crs,dst_transform=reference.transform,dst_crs=reference.crs,resampling=Resampling.bilinear)
                        reproject(source.dataset_mask(),coverage,src_transform=source.transform,
                            src_crs=source.crs,dst_transform=reference.transform,dst_crs=reference.crs,resampling=Resampling.nearest)
                    rgb=np.moveaxis(rgb,0,-1);target=target_base.copy();target[coverage==0]=255
                    known=target!=255;count=int(known.sum());alignment=alignment_screen(before,rgb)
                    bright=(rgb.mean(2)>200)&(rgb.max(2).astype(int)-rgb.min(2).astype(int)<25)
                    cloud=float(bright[known].mean()) if count else 0.0
                    coverage_fraction=float((coverage>0).mean())
                    qc={'post_source':row[field],'known_pixels':count,'coverage_fraction':coverage_fraction,
                        'bright_neutral_labeled_fraction':cloud,'alignment_screen':alignment}
                    # Same fixed RGB/coverage ordering as reviewed train/dev preparation.
                    # No final tile is excluded/replaced, including empty-supervision tiles.
                    flagged=count<64 or cloud>.25 or coverage_fraction<.95
                    rank=(flagged,alignment['manual_review_flag'],round(cloud,2),-alignment['gradient_ncc_zero'])
                    options.append((rank,rgb,target,qc))
            if not options:raise ValueError('Missing mapped post image for '+row['id'])
            _,rgb,target,qc=min(options,key=lambda item:item[0])
            image=DATA/(row['id']+'.png');mask=DATA/(row['id']+'_mask.png')
            save_image(Image.fromarray(rgb),image);save_image(Image.fromarray(target),mask);check_budget()
            manifest.append({'source_image_id':row['id'],'split':'test','spatial_group':row['prefix']+f"_block_{row['x']//5}_{row['y']//5}",
                'dataset':row['dataset'],'image':str(image.relative_to(ROOT)),'mask':str(mask.relative_to(ROOT)),
                'image_sha256':sha256(image),'mask_sha256':sha256(mask),'post_source':qc['post_source'],
                'post_source_url':'https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/'+row['dataset']+'/POST-event/'+qc['post_source']})
            quality.append({'source_image_id':row['id'],'selected':qc,'alternatives':[item[3] for item in options],
                'excluded':False,'rule':'Fixed coverage/cloud/alignment ranking; no model scores, exclusions, or replacements.'})
            print('Prepared sealed tile '+row['id'],flush=True)
        validate_final_rows(manifest,protocol['final_ids'])
        save(DATA/'manifest.json',manifest)
        save(EVIDENCE/'final_preparation.json',{'selection':commit,'manifest_sha256':sha256(DATA/'manifest.json'),
            'tile_count':len(manifest),'quality':quality,'mask_rule':'Four-source-pixel buffered reference roads; overlap and uncovered pixels=255; no correction',
            'no_final_tile_excluded':True,'sources':[{'source_image_id':row['source_image_id'],'post_source_url':row['post_source_url'],'image_sha256':row['image_sha256'],'mask_sha256':row['mask_sha256']} for row in manifest]})
    except BaseException as exc:
        finish_attempt(ledger,state,exc);raise
    finish_attempt(ledger,state)


def evaluate():
    selection,commit=committed_selection(SELECTION)
    protocol=preflight();manifest=DATA/'manifest.json';rows=json.loads(manifest.read_text())
    validate_final_rows(rows,protocol['final_ids'])
    prepared=json.loads((EVIDENCE/'final_preparation.json').read_text())
    if json.loads((EVIDENCE/'final_preparation_ledger.json').read_text())['status']!='complete' or prepared['manifest_sha256']!=sha256(manifest):
        raise ValueError('Final preparation is incomplete or changed')
    request={'phase':'evaluate','selection':commit,'manifest_sha256':sha256(manifest),
        'source_sha256':sha256(Path(__file__)),'metric_source_sha256':sha256(ROOT/'ml/vision/evaluate.py'),
        'tiled_source_sha256':sha256(ROOT/'ml/vision/tiled.py'),'device':'cpu','tile_size':256,'stride':256,'decision':selection['decision']}
    ledger=EVIDENCE/'final_evaluation_ledger.json';state=begin_attempt(ledger,request)
    started=time.perf_counter()
    try:
        import torch
        from transformers import SegformerForSemanticSegmentation,SegformerImageProcessor
        from ml.experiments.v3_models import load_candidate
        from ml.vision.tiled import tiled_probabilities
        from ml.vision.evaluate import binary_metrics
        from ml.vision.provenance import checkpoint_identity
        from scripts.ml.evaluate_road_tiles import aggregate
        torch.set_num_threads(2)
        v2=ROOT/'ml/artifacts/sn8_native_cpu_v2/model'
        if checkpoint_identity(v2)!=selection['v2_checkpoint_id']:raise ValueError('Frozen v2 checkpoint changed')
        results=[{'source_image_id':row['source_image_id'],'dataset':row['dataset'],'metrics':{},'predictions':{}} for row in rows]
        predictions=DATA/('predictions_attempt_'+str(state['attempt']));predictions.mkdir(exist_ok=True)
        parameters={}
        for role in ('v2','v3'):
            deadline()
            if role=='v2':
                model=SegformerForSemanticSegmentation.from_pretrained(v2,local_files_only=True).eval()
                processor=SegformerImageProcessor.from_pretrained(v2,local_files_only=True)
            else:
                base=ROOT/'ml/artifacts/sn8_native_cpu_v2/baseline_model'
                model=load_candidate(selection['architecture'],ROOT/selection['checkpoint'],base)
                processor=SegformerImageProcessor.from_pretrained(base,local_files_only=True)
            parameters[role]=sum(parameter.numel() for parameter in model.parameters())
            for row,item in zip(rows,results):
                deadline()
                if sha256(ROOT/row['image'])!=row['image_sha256'] or sha256(ROOT/row['mask'])!=row['mask_sha256']:
                    raise ValueError('Final pixels changed after preparation')
                with Image.open(ROOT/row['mask']) as source:target=np.asarray(source).copy()
                if target.ndim!=2 or not np.isin(target,[0,1,255]).all():raise ValueError('Invalid final mask')
                tick=time.perf_counter()
                with Image.open(ROOT/row['image']) as image:
                    probabilities=tiled_probabilities(model,processor,image,tile_size=256,stride=256)
                if probabilities.shape!=(2,*target.shape) or not np.isfinite(probabilities).all():raise ValueError('Invalid final predictions')
                prediction=probabilities.argmax(0).astype('uint8')
                path=predictions/(row['source_image_id']+'_'+role+'.png');Image.fromarray(prediction).save(path)
                counts=binary_metrics(prediction,target);counts['tn']=counts['valid_pixels']-counts['tp']-counts['fp']-counts['fn']
                item['metrics'][role]=counts;item['predictions'][role]=str(path.relative_to(ROOT))
                item.setdefault('inference_seconds',{})[role]=time.perf_counter()-tick
                if role=='v2':
                    item['metrics']['all_positive']=binary_metrics(np.ones_like(target),target)
                    item['metrics']['all_negative']=binary_metrics(np.zeros_like(target),target)
                with (EVIDENCE/('final_attempt_'+str(state['attempt'])+'.jsonl')).open('a') as stream:
                    stream.write(json.dumps({'model':role,**item})+'\n')
                print('Scored '+role+' '+row['source_image_id'],flush=True)
            del model,processor
        metrics={role:aggregate([row['metrics'][role] for row in results]) for role in ('v2','v3','all_positive','all_negative')}
        for value in metrics.values():value['tn']=value['valid_pixels']-value['tp']-value['fp']-value['fn']
        if checkpoint_identity(v2)!=selection['v2_checkpoint_id'] or sha256(ROOT/selection['checkpoint'])!=selection['checkpoint_sha256']:
            raise ValueError('Checkpoint identity changed during evaluation')
        result={'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),'selection':commit,'request':request,
            'tile_count':len(rows),'parameters':parameters,'metrics':metrics,'per_tile':results,
            'elapsed_seconds':time.perf_counter()-started,'promote_v3':metrics['v3']['f1'] is not None and metrics['v2']['f1'] is not None and metrics['v3']['f1']>metrics['v2']['f1'],
            'support':'Identical road-mask pixels for both models; unknown255 ignored. Empty-supervision tiles retained with undefined metrics.',
            'caveats':['New geographic blocks within Louisiana/Germany known events; not unseen-event generalization or official SpaceNet test performance.',
                'No Helene accuracy ground truth or road-closure/passability accuracy is measured.',
                'Buffered road labels, registration/cloud errors and class imbalance remain; probabilities are not calibrated safety scores.',
                'Development selection uses correlated crops from19 tiles; final assessment uses38 full tiles once.']}
        save(EVIDENCE/'final_evaluation.json',result)
    except BaseException as exc:
        finish_attempt(ledger,state,exc);raise
    finish_attempt(ledger,state)
    print(json.dumps({'tile_count':result['tile_count'],'metrics':metrics,'promote_v3':result['promote_v3']}),flush=True)


def choose_proof_tiles(results):
    def difference(row):
        before,after=(row['metrics'][role]['f1'] for role in ('v2','v3'))
        return after-before if before is not None and after is not None else None
    paired=[row for row in results if difference(row) is not None]
    worse=[row for row in paired if difference(row)<0]
    criterion='lower F1'
    if worse:
        first=min(worse,key=difference)
    else:
        worse=[row for row in results if row['metrics']['v3']['fp']>row['metrics']['v2']['fp']]
        criterion='more false positives'
        if not worse:
            worse=[row for row in results if row['metrics']['v3']['fn']>row['metrics']['v2']['fn']]
            criterion='more missed flood pixels'
        first=max(worse,key=lambda row:row['metrics']['v3']['fp']+row['metrics']['v3']['fn']) if worse else min(paired or results,key=lambda row:difference(row) if difference(row) is not None else 0)
    chosen=[first]
    remaining=[row for row in results if row['source_image_id']!=first['source_image_id']]
    chosen.append(max(remaining,key=lambda row:difference(row) if difference(row) is not None else float('-inf')))
    remaining=[row for row in remaining if row['source_image_id']!=chosen[1]['source_image_id']]
    other=[row for row in remaining if row['dataset']!=first['dataset']]
    chosen.append(max(other or remaining,key=lambda row:row['metrics']['v2']['valid_pixels']))
    return chosen,{'regression_found':bool(worse),'regression_criterion':criterion if worse else None,
        'rule':'Worst lower F1; otherwise higher FP/FN; then best F1 delta and another-region tile. No regression is fabricated if none exists.'}


def proof():
    result=json.loads((EVIDENCE/'final_evaluation.json').read_text())
    if json.loads((EVIDENCE/'final_evaluation_ledger.json').read_text())['status']!='complete':raise ValueError('No completed final evaluation')
    rows=json.loads((DATA/'manifest.json').read_text());by_id={row['source_image_id']:row for row in rows}
    chosen,choice=choose_proof_tiles(result['per_tile'])
    canvas=Image.new('RGB',(1920,1080),'#101820');draw=ImageDraw.Draw(canvas)
    font=lambda size:ImageFont.load_default(size=size)
    draw.text((32,18),'SOSora V3 | one sealed final evaluation',font=font(30),fill='white')
    draw.text((32,60),'38 full tiles | known Louisiana/Germany events | narrow road labels | no Helene accuracy claim',font=font(18),fill='#b8c8ce')
    for column,name in enumerate(['Image','Ground truth','Native v2','Selected V3']):draw.text((42+column*472,96),name,font=font(22),fill='#ffb183')
    for index,item in enumerate(chosen):
        row=by_id[item['source_image_id']];top=136+index*292
        with Image.open(ROOT/row['image']) as image:rgb=image.convert('RGB').copy()
        with Image.open(ROOT/row['mask']) as image:target=np.asarray(image).copy()
        maps=[rgb]
        for role in (None,'v2','v3'):
            values=target if role is None else np.asarray(Image.open(ROOT/item['predictions'][role]))
            colored=np.zeros((*target.shape,3),dtype='uint8');colored[:]=[31,43,53]
            colored[(target!=255)&(values==0)]=[115,209,175];colored[(target!=255)&(values==1)]=[255,157,105]
            maps.append(Image.fromarray(colored))
        for column,image in enumerate(maps):
            image.thumbnail((442,242),Image.Resampling.NEAREST if column else Image.Resampling.BILINEAR)
            canvas.paste(image,(32+column*472+(442-image.width)//2,top))
        before,after=item['metrics']['v2'],item['metrics']['v3']
        fmt=lambda value:'undefined' if value is None else f'{value:.4f}'
        caption=f"{item['source_image_id']} | v2 F1 {fmt(before['f1'])} | V3 F1 {fmt(after['f1'])} | FP {before['fp']}->{after['fp']} | FN {before['fn']}->{after['fn']}"
        if index==0:caption+=' | V3 worse: '+choice['regression_criterion'] if choice['regression_found'] else ' | No per-tile F1/FP/FN regression found'
        draw.text((32,top+248),caption,font=font(16),fill='#ffc2ae' if index==0 and choice['regression_found'] else '#c3e8d8')
    draw.text((32,1025),'Orange = flooded road | green = non-flooded road | dark = unlabeled, not scored. Panels use saved final predictions; no new inference.',font=font(16),fill='#d2dce0')
    draw.text((32,1050),'Source: SpaceNet 8 / Maxar, CC BY-SA 4.0. Illustrative failure/best/other-region examples; full counts and all tiles are in final_evaluation.json.',font=font(14),fill='#9fb5bf')
    output=ROOT/'docs/screenshots/vision-v3-proof.png';output.parent.mkdir(parents=True,exist_ok=True);canvas.save(output)
    save(EVIDENCE/'proof_selection.json',{**choice,'tile_ids':[row['source_image_id'] for row in chosen],'image_sha256':sha256(output),'size':[1920,1080],'inference_repeated':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','evaluate','proof']);args=parser.parse_args()
    {'prepare':prepare,'evaluate':evaluate,'proof':proof}[args.phase]()
