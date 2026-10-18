"""Prepare a frozen, label-blind, geographically separated SpaceNet8 evaluation."""
import csv,datetime,hashlib,json,random,urllib.request
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image
import rasterio
from rasterio.features import rasterize
from rasterio.warp import reproject,Resampling,transform_bounds
from shapely import wkt
from ml.vision.provenance import checkpoint_identity

ROOT=Path('ml/artifacts/sn8_frozen_external')
BASE='https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Germany_Training_Public/'

def main():
    freeze=json.loads((ROOT/'freeze.json').read_text())
    if (ROOT/'manifest.json').exists() or (ROOT/'selection.json').exists():raise ValueError('Frozen preparation already started; never overwrite or reselect')
    assert checkpoint_identity(freeze['model'])==freeze['checkpoint_id']
    sources=[];failures=[];downloaded=0
    def save(name,data):
        (ROOT/name).write_text(json.dumps(data,indent=2))
    def fetch(name,subdir=''):
        nonlocal downloaded
        if Path(name).name!=name:raise ValueError('Unexpected source filename')
        url=BASE+subdir+name;path=ROOT/name
        if path.exists():raise ValueError('Refuse to reuse unrecorded source')
        digest=hashlib.sha256();size=0
        with urllib.request.urlopen(url,timeout=30) as response,path.open('wb') as target:
            while chunk:=response.read(1024*1024):
                downloaded+=len(chunk);size+=len(chunk)
                if downloaded>freeze['download_budget_bytes']:raise RuntimeError('Download budget exhausted')
                digest.update(chunk);target.write(chunk)
        sources.append({'url':url,'path':str(path),'bytes':size,'sha256':digest.hexdigest(),'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        save('sources.json',sources)
        return path
    mapping=fetch('Germany_Training_Public_label_image_mapping.csv')
    pairs=sorted(csv.DictReader(mapping.open()),key=lambda r:r['pre-event image'])
    random.Random(17017).shuffle(pairs)
    previous=json.loads(Path('ml/artifacts/sn8_pilot/manifest.json').read_text())
    prior_bounds=[r['bounds_epsg3857'] for r in previous]
    inventory={p.name for p in Path('ml/artifacts').rglob('*.tif') if ROOT not in p.parents}
    def gap(a,b):
        dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0)
        return (dx*dx+dy*dy)**.5
    selected=[]
    for pair in pairs:
        pre_name=pair['pre-event image'];image_id=Path(pre_name).stem
        if pre_name in inventory:
            failures.append({'phase':'selection','image_id':image_id,'reason':'Previously downloaded imagery excluded'});continue
        try:
            pre=fetch(pre_name,'PRE-event/')
            with rasterio.open(pre) as source:
                bounds=list(transform_bounds(source.crs,'EPSG:3857',*source.bounds))
            if any(gap(bounds,r['bounds_epsg3857'])<500 for r in selected):continue
            if any(gap(bounds,b)<5000 for b in prior_bounds):raise ValueError('Too close to earlier pilot')
            selected.append({'source_image_id':image_id,'pair':pair,'pre':str(pre),'bounds_epsg3857':bounds,'minimum_previous_bbox_gap_epsg3857_m':min(gap(bounds,b) for b in prior_bounds)})
            print('selected_without_labels',image_id,flush=True)
            if len(selected)==freeze['count']:break
        except Exception as exc:
            failures.append({'phase':'selection','image_id':image_id,'reason':type(exc).__name__+': '+str(exc)})
            if downloaded>=freeze['download_budget_bytes']:break
    save('selection.json',{'selected_without_label_access':selected,'previous_source_ids':[r['source_image_id'] for r in previous],'previous_tif_inventory':sorted(inventory),'label_access_started':False,'selection_failures':failures})
    # Only now access flood-state reference labels. No replacements from this point.
    reference=fetch('Germany_Training_Public_reference.csv')
    labels=defaultdict(list)
    for row in csv.DictReader(reference.open()):
        if row['Object']=='Road' and row['Flooded'] in {'True','False'} and 'EMPTY' not in row['Wkt_Pix']:labels[row['ImageId']].append(row)
    manifest=[]
    for item in selected:
        image_id=item['source_image_id']
        try:
            post_name=item['pair']['post-event image 1']
            if not post_name:raise ValueError('No first post-event image')
            post=fetch(post_name,'POST-event/')
            with rasterio.open(item['pre']) as pre,rasterio.open(post) as source:
                if source.dtypes[:3]!=('uint8','uint8','uint8'):raise ValueError('Expected uint8RGB; no new radiometric tuning')
                height,width=pre.height,pre.width;aligned=np.zeros((3,height,width),dtype=np.uint8)
                for b in range(3):reproject(source.read(b+1),aligned[b],src_transform=source.transform,src_crs=source.crs,dst_transform=pre.transform,dst_crs=pre.crs,resampling=Resampling.bilinear)
                coverage=np.zeros((height,width),dtype=np.uint8)
                reproject(source.dataset_mask(),coverage,src_transform=source.transform,src_crs=source.crs,dst_transform=pre.transform,dst_crs=pre.crs,resampling=Resampling.nearest)
                geo={'crs':str(pre.crs),'transform':list(pre.transform),'width':width,'height':height}
            masks=[]
            for flooded in ['False','True']:
                geoms=[wkt.loads(r['Wkt_Pix']).buffer(4) for r in labels[image_id] if r['Flooded']==flooded]
                masks.append(rasterize([(g,1) for g in geoms],out_shape=(height,width),dtype='uint8') if geoms else np.zeros((height,width),dtype=np.uint8))
            target=np.full((height,width),255,dtype=np.uint8);target[masks[0]>0]=0;target[masks[1]>0]=1
            target[((masks[0]>0)&(masks[1]>0))|(coverage==0)]=255
            if not np.any(target!=255):raise ValueError('No valid road supervision; count as preparation failure')
            image=ROOT/(image_id+'.png');mask=ROOT/(image_id+'_mask.png')
            Image.fromarray(np.moveaxis(aligned,0,-1)).save(image);Image.fromarray(target).save(mask)
            manifest.append({'image':str(image),'mask':str(mask),'split':'test','spatial_group':'Germany_external_'+image_id,'source_image_id':image_id,'post_image':post_name,'bounds_epsg3857':item['bounds_epsg3857'],'minimum_previous_bbox_gap_epsg3857_m':item['minimum_previous_bbox_gap_epsg3857_m'],'label_counts':{str(k):int(v) for k,v in zip(*np.unique(target,return_counts=True))},'georeferencing':geo})
            print('prepared',image_id,flush=True)
        except Exception as exc:failures.append({'phase':'preparation','image_id':image_id,'reason':type(exc).__name__+': '+str(exc)})
    save('manifest.json',manifest);save('failures.json',failures)
    save('methodology.json',{'freeze':freeze,'selected_count':len(selected),'prepared_count':len(manifest),'download_bytes':downloaded,'license':'CC-BY-SA-4.0','official_catalog':'https://spacenet.ai/sn8-challenge/','registration':'PostRGB bilinear warped to pre grid; uncorrected residual offsets','labels':'Official reference Wkt_Pix road centerlines buffered4 source pixels; conflicts/unknown/no coverage ignored255','selection_label_blind':True,'label_access_started_after_selection_written':True,'replacement_after_label_access':False,'footprint_gap_units':'EPSG3857 metres (not geodesic; different continent demonstrates separation)','new_evaluation_only_no_tuning':True})
    print(json.dumps({'selected':len(selected),'prepared':len(manifest),'download_bytes':downloaded,'failures':failures},indent=2))

if __name__=='__main__':main()
