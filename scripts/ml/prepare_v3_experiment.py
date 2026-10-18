"""Bounded v3 preparation. Final IDs freeze before any train/dev label processing.
No final label/mask preparation, training, model selection or paid infrastructure.
"""
import argparse
import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import io
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request
import numpy as np
from PIL import Image
import rasterio
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling, transform_bounds
from shapely.geometry import box
from shapely import wkt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ml/artifacts/v3_experiment'
CAP = 2*1024**3
RAW_CAP = 1536*1024**2
BASE = 'https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/'
SEED = 'sosora-v3-20261017-fixed'
LOCK = threading.RLock()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')


def used_bytes():
    return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())


def check_budget():
    if used_bytes() > CAP:
        raise ValueError('2 GiB added-storage cap reached; stop without deleting evidence')


def fetch(row, field, folder):
    name = row[field]
    if not name or Path(name).name != name:
        raise ValueError('Invalid public source filename')
    path = OUT/'raw'/name
    receipt = OUT/'raw'/(name+'.receipt.json')
    if path.exists():
        if not receipt.exists():
            raise ValueError('Unrecorded partial source; manual review required')
        recorded = json.loads(receipt.read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != recorded['sha256']:
            raise ValueError('Source integrity mismatch')
        return path
    url = BASE+row['dataset']+'/'+folder+'/'+name
    for attempt in range(4):
        h = hashlib.sha256()
        try:
            with urllib.request.urlopen(url, timeout=40) as response, path.open('xb') as stream:
                while chunk := response.read(262144):
                    with LOCK:
                        raw_bytes = sum(p.stat().st_size for p in (OUT/'raw').iterdir() if p.is_file())
                        if raw_bytes+len(chunk) > RAW_CAP or used_bytes()+len(chunk) > CAP:
                            raise ValueError('Public-data budget exhausted')
                        stream.write(chunk);stream.flush()
                    h.update(chunk)
            receipt.write_text(json.dumps({'url':url,'bytes':path.stat().st_size,'sha256':h.hexdigest()}))
            return path
        except (urllib.error.URLError, TimeoutError, OSError):
            if path.exists():
                path.rename(path.with_name(path.name+f'.partial-{time.time_ns()}'))
            if attempt==3:
                raise
            time.sleep(2**attempt)


def read_allowed_labels(path, allowed):
    """Only admitted train/dev IDs are parsed; final annotations remain unused."""
    labels = defaultdict(list)
    with Path(path).open() as stream:
        header = stream.readline()
        if header.split(',')[0].strip() != 'ImageId':
            raise ValueError('Expected ImageId as the first CSV field for sealed-row filtering')
        for line in stream:
            # Identify the row before interpreting its geometry or flood attribute.
            ident = line.partition(',')[0].strip().strip('"')
            if ident not in allowed:
                continue
            row = next(csv.DictReader([header, line]))
            if row['Object']=='Road' and row['Flooded'] in {'True','False'} and 'EMPTY' not in row['Wkt_Pix']:
                labels[row['ImageId']].append(row)
    return labels


def save_image(image, path):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    content = buffer.getvalue()
    with LOCK:
        # Keep 2 MiB for receipts/manifests; reject before writing an oversized image.
        if used_bytes()+len(content) > CAP-2*1024**2:
            raise ValueError('Derived-image storage budget exhausted')
        Path(path).write_bytes(content)


def make_masks(rows, shape):
    masks=[]
    for state in ['False','True']:
        shapes=[(wkt.loads(r['Wkt_Pix']).buffer(4),1) for r in rows if r['Flooded']==state]
        masks.append(rasterize(shapes,out_shape=shape,fill=0,dtype='uint8') if shapes else np.zeros(shape,dtype=np.uint8))
    target=np.full(shape,255,dtype=np.uint8)
    target[masks[0]>0]=0;target[masks[1]>0]=1
    target[(masks[0]>0)&(masks[1]>0)]=255
    return target


def alignment_screen(before, after):
    """Coarse gradient diagnostic only; never estimates a correction from labels."""
    def edges(rgb):
        gray=np.asarray(Image.fromarray(rgb).convert('L').resize((325,325)),dtype=float)
        gy,gx=np.gradient(gray)
        return np.hypot(gx,gy)
    a,b=edges(before),edges(after);a=a[12:-12,12:-12];a=a-a.mean()
    scores={}
    for dy in range(-4,5):
        for dx in range(-4,5):
            q=b[12+dy:b.shape[0]-12+dy,12+dx:b.shape[1]-12+dx];q=q-q.mean()
            denom=np.sqrt((a*a).sum()*(q*q).sum())
            scores[(dx*4,dy*4)]=float((a*q).sum()/denom) if denom else 0.0
    shift=max(scores,key=scores.get)
    return {'best_shift_source_pixels':list(shift),'gradient_ncc_zero':scores[(0,0)],
            'gradient_ncc_best':scores[shift],
            'manual_review_flag':bool(max(map(abs,shift))>=8 and scores[shift]>.35 and scores[shift]-scores[(0,0)]>.08),
            'interpretation':'Screen only: clouds/flooding/appearance changes can invalidate this match; no correction applied.'}


def rank(row):
    return hashlib.sha256((SEED+row['id']).encode()).hexdigest()


def plan():
    if (OUT/'protocol.json').exists():
        raise ValueError('Protocol already frozen; do not reselect')
    historical = json.loads((ROOT/'ml/artifacts/sn8_pilot/manifest.json').read_text())+json.loads((ROOT/'docs/ml/evidence/frozen_external/manifest.json').read_text())
    anchors={}; old={}
    for row in historical:
        ident=row['source_image_id'];prefix,group,x,y=ident.split('_');key=prefix+'_'+group
        folder='sn8_frozen_external' if prefix=='10500500C4DD7000' else 'sn8_pilot'
        with rasterio.open(ROOT/'ml/artifacts'/folder/(ident+'.tif')) as src:
            b=src.bounds;crs=32632 if prefix=='10500500C4DD7000' else 32615
            old[ident]=(crs,box(*transform_bounds(src.crs,f'EPSG:{crs}',*b)))
            anchor=dict(x=int(x),y=int(y),left=b.left,top=b.top,w=b.right-b.left,h=b.top-b.bottom)
            if key in anchors:
                a=anchors[key]
                if max(abs(b.left-(a['left']+(int(x)-a['x'])*a['w'])),abs(b.top-(a['top']-(int(y)-a['y'])*a['h'])))>1e-7:
                    raise ValueError('Filename grid not supported by existing georeferencing')
            anchors[key]=anchor
    candidates=[]
    for dataset,mapping in [('Louisiana-East_Training_Public',ROOT/'ml/artifacts/sn8_pilot/mapping.csv'),('Germany_Training_Public',ROOT/'ml/artifacts/sn8_frozen_external/Germany_Training_Public_label_image_mapping.csv')]:
        for pair in csv.DictReader(mapping.open()):
            ident=Path(pair['pre-event image']).stem;prefix,group,x,y=ident.split('_');key=prefix+'_'+group;x=int(x);y=int(y);a=anchors[key]
            left=a['left']+(x-a['x'])*a['w'];top=a['top']-(y-a['y'])*a['h']
            bounds=[left,top-a['h'],left+a['w'],top]
            crs=32632 if dataset.startswith('Germany') else 32615
            metric=transform_bounds('EPSG:4326',f'EPSG:{crs}',*bounds)
            candidates.append(dict(id=ident,prefix=key,x=x,y=y,dataset=dataset,crs=crs,bounds_lonlat=bounds,bounds_metric=list(metric),**pair))
    def region(row):return box(*row['bounds_metric'])
    def separated(row,others):
        return all(row['crs']!=other['crs'] or region(row).distance(region(other))>=1000 for other in others)
    old_rows=[dict(crs=c,bounds_metric=list(g.bounds)) for c,g in old.values()]
    def is_final(r):
        return (r['prefix']=='10400100684A4B00_1' and 5<=r['x']<=9 and 95<=r['y']<=99) or (r['prefix']=='10500500C4DD7000_0' and 25<=r['x']<=29 and 65<=r['y']<=69)
    final=[dict(r,split='final_sealed') for r in candidates if is_final(r) and r['id'] not in old and separated(r,old_rows)]
    dev=[]
    for pref,x1,x2,y1,y2 in [('10300100AF395C00_2',15,19,40,44),('10500500C4DD7000_0',40,44,55,59),('10400100684A4B00_1',20,24,75,79)]:
        eligible=[r for r in candidates if r['prefix']==pref and x1<=r['x']<=x2 and y1<=r['y']<=y2 and r['id'] not in old and separated(r,final)]
        dev.extend(dict(r,split='validation') for r in sorted(eligible,key=rank)[:8])
    excluded={r['id'] for r in final+dev}|set(old)
    train=[]
    for pref in sorted(anchors):
        eligible=[r for r in candidates if r['prefix']==pref and r['id'] not in excluded and separated(r,final+dev)]
        train.extend(dict(r,split='train') for r in sorted(eligible,key=rank)[:25])
    rows=train+dev+final
    if not final or len(train)<30 or len(dev)<8:raise ValueError('Insufficient separated metadata candidates')
    print('Metadata candidates',dict((s,sum(r['split']==s for r in rows)) for s in ['train','validation','final_sealed']),flush=True)
    progress=[0]
    def verify(row):
        path=fetch(row,'pre-event image','PRE-event')
        with rasterio.open(path) as src:
            actual=list(transform_bounds(src.crs,'EPSG:4326',*src.bounds))
            if max(abs(a-b) for a,b in zip(actual,row['bounds_lonlat']))>1e-7:
                raise ValueError('Downloaded footprint disagrees with metadata-grid prediction: '+row['id'])
            row['verified_bounds_metric']=list(transform_bounds(src.crs,f"EPSG:{row['crs']}",*src.bounds))
            row['width']=src.width;row['height']=src.height
        with LOCK:
            progress[0]+=1
            if progress[0]%10==0:print('Verified public footprints',progress[0],'/',len(rows),flush=True)
        return row
    with ThreadPoolExecutor(max_workers=4) as pool:
        verified=list(pool.map(verify,rows))
    # Recheck actual footprint distances before committing final IDs.
    for row in verified:
        row['bounds_metric']=row['verified_bounds_metric']
        opposite=[r for r in verified if r['split']!=row['split']]
        if not separated(row,opposite):raise ValueError('Actual geographic split separation failed')
    protocol={'protocol_version':3,'seed':SEED,'minimum_edge_gap_m':1000,'distance_crs':'UTM15N Louisiana / UTM32N Germany','storage_cap_bytes':CAP,'raw_cap_bytes':RAW_CAP,'historical_ids_excluded':sorted(old),'rows':verified,'final_ids':[r['id'] for r in verified if r['split']=='final_sealed'],'label_access':'No new labels processed during plan; final labels/masks must stay sealed until checkpoint/settings selection.','assessment':'New geography within two known events, not unseen-event or official test performance.','selection':'Fixed metadata blocks, deterministic SHA256 rank, no flood prevalence balancing; no replacement based on final outcomes.'}
    protocol['protocol_sha256']=digest(protocol)
    save('protocol.json',protocol)
    print('Frozen protocol',protocol['protocol_sha256'],'bytes',used_bytes(),flush=True)


def prepare():
    protocol=json.loads((OUT/'protocol.json').read_text());claimed=protocol.pop('protocol_sha256')
    if digest(protocol)!=claimed:raise ValueError('Protocol changed')
    seal_path=OUT/'final_seal.json'
    seal={'protocol_sha256':claimed,'final_ids_sha256':digest(protocol['final_ids']),'final_count':len(protocol['final_ids'])}
    if seal_path.exists():
        existing=json.loads(seal_path.read_text())
        if any(existing.get(k)!=v for k,v in seal.items()):raise ValueError('Final seal changed')
    else:
        seal.update({'sealed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_file_created_utc':datetime.datetime.fromtimestamp((OUT/'protocol.json').stat().st_mtime,datetime.timezone.utc).isoformat(),'final_label_processing_performed':False,'note':'Created before train/dev label interpretation; no final masks or model scores may be prepared until checkpoint/settings selection.'})
        seal_path.write_text(json.dumps(seal,indent=2)+'\n')
    rows=[r for r in protocol['rows'] if r['split'] in ['train','validation']]
    allowed={r['id'] for r in rows};labels={}
    for dataset,path in [('Louisiana-East_Training_Public',ROOT/'ml/artifacts/sn8_pilot/reference.csv'),('Germany_Training_Public',ROOT/'ml/artifacts/sn8_frozen_external/Germany_Training_Public_reference.csv')]:
        labels.update(read_allowed_labels(path,{r['id'] for r in rows if r['dataset']==dataset}))
    for d in ['prepared','crops']:(OUT/d).mkdir(exist_ok=True)
    def process(row):
        pre=OUT/'raw'/row['pre-event image']
        with rasterio.open(pre) as ref:
            before=np.moveaxis(ref.read([1,2,3]),0,-1)
            target_base=make_masks(labels.get(row['id'],[]),(ref.height,ref.width))
        options=[]
        for field in ['post-event image 1','post-event image 2']:
            if not row.get(field):continue
            post=fetch(row,field,'POST-event')
            with rasterio.open(pre) as ref,rasterio.open(post) as src:
                if src.count<3 or src.dtypes[:3]!=('uint8','uint8','uint8'):
                    raise ValueError('Expected uint8 public RGB source')
                rgb=np.zeros((3,ref.height,ref.width),dtype='uint8');coverage=np.zeros((ref.height,ref.width),dtype='uint8')
                for b in range(3):reproject(src.read(b+1),rgb[b],src_transform=src.transform,src_crs=src.crs,dst_transform=ref.transform,dst_crs=ref.crs,resampling=Resampling.bilinear)
                reproject(src.dataset_mask(),coverage,src_transform=src.transform,src_crs=src.crs,dst_transform=ref.transform,dst_crs=ref.crs,resampling=Resampling.nearest)
            rgb=np.moveaxis(rgb,0,-1);alignment=alignment_screen(before,rgb)
            target=target_base.copy();target[coverage==0]=255;known=target!=255;n=int(known.sum())
            bright=(rgb.mean(2)>200)&(rgb.max(2).astype(int)-rgb.min(2).astype(int)<25)
            qc={'id':row['id'],'split':row['split'],'post_source':row[field],'known_pixels':n,'flood_pixels':int((target==1).sum()),'coverage_fraction':float((coverage>0).mean()),'bright_neutral_labeled_fraction':float(bright[known].mean()) if n else None,'alignment_screen':alignment}
            reason='no_supervision' if n<64 else 'bright_cloud_screen_manual_review' if qc['bright_neutral_labeled_fraction']>.25 else 'insufficient_post_coverage' if qc['coverage_fraction']<.95 else None
            qc['excluded_reason']=reason
            # Fixed RGB/coverage quality ordering, never model scores or flood prevalence.
            score=(reason is not None,alignment['manual_review_flag'],round(qc['bright_neutral_labeled_fraction'] or 0,2),-alignment['gradient_ncc_zero'])
            options.append((score,rgb,target,qc))
        if not options:raise ValueError('No post-event image')
        chosen=min(options,key=lambda x:x[0]);_,rgb,target,qc=chosen;reason=qc['excluded_reason']
        qc['post_candidates']=[x[3].copy() for x in options]
        qc['post_selection']='Fixed coverage/cloud/alignment RGB screen, no model metrics; both listed post images compared where available.'
        if reason:return None,qc
        image=OUT/'prepared'/(row['id']+'.png');mask=OUT/'prepared'/(row['id']+'_mask.png')
        with LOCK:
            save_image(Image.fromarray(rgb),image);save_image(Image.fromarray(target),mask);check_budget()
        return dict(image=str(image),mask=str(mask),split=row['split'],spatial_group=row['prefix']+f"_block_{row['x']//5}_{row['y']//5}",source_image_id=row['id'],post_source=qc['post_source'],bounds_lonlat=row['bounds_lonlat']),qc
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(process,rows))
    prepared=[r for r,q in results if r];qc=[q for r,q in results]
    save('train_dev_manifest.json',prepared);save('quality_screen.json',qc)
    save('readiness.json',{'status':'manual_quality_review_required','final_labels_sealed':True,'alignment_flagged_ids':[q['id'] for q in qc if q['alignment_screen']['manual_review_flag']],'cloud_screen_excluded_ids':[q['id'] for q in qc if q['excluded_reason']=='bright_cloud_screen_manual_review'],'note':'Do not start full training before reviewing flagged train/dev imagery; final imagery/labels are not reviewed.'})
    from scripts.ml.prepare_road_crops import select_windows
    crops=[]
    for row in prepared:
        rgb=np.asarray(Image.open(row['image']));mask=np.asarray(Image.open(row['mask']))
        for i,(bounds,n0,n1) in enumerate(select_windows(mask,limit=8 if row['split']=='train' else 6)):
            l,t,r,b=bounds;stem=row['source_image_id']+f'_{i:02d}';im=OUT/'crops'/(stem+'.png');ma=OUT/'crops'/(stem+'_mask.png')
            save_image(Image.fromarray(rgb[t:b,l:r]),im);save_image(Image.fromarray(mask[t:b,l:r]),ma);check_budget()
            crops.append(dict(row,image=str(im),mask=str(ma),crop_pixel_bounds=list(bounds),label_counts={'0':n0,'1':n1}))
    save('crop_manifest.json',crops)
    print('Prepared',len(prepared),'tiles;',len(crops),'crops; excluded',sum(q['excluded_reason'] is not None for q in qc),'bytes',used_bytes(),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['plan','prepare']);a=p.parse_args()
    OUT.mkdir(exist_ok=True);(OUT/'raw').mkdir(exist_ok=True)
    if a.phase=='plan':plan()
    else:prepare()
