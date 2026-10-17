"""Small labeled road-corridor flood segmentation pilot, no synthetic labels.
Official reference centerlines: buffer 4 source pixels. Unlabeled pixels ignored.
Post-event RGB is geospatially warped onto pre-event pixel grid; residual
registration errors are not corrected. Three acquisition groups split apart.
"""
import csv
import json
import random
import urllib.request
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from PIL import Image
import rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.features import rasterize
from shapely import wkt

BASE='https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Louisiana-East_Training_Public/'

def fetch(url,path):
    if not path.exists(): urllib.request.urlretrieve(url,path)
    return path

def main():
    out=Path('ml/artifacts/sn8_pilot');out.mkdir(parents=True,exist_ok=True)
    reference=fetch(BASE+'Louisiana-East_Training_Public_reference.csv',out/'reference.csv')
    mapping=fetch(BASE+'Louisiana-East_Training_Public_label_image_mapping.csv',out/'mapping.csv')
    labels=defaultdict(list)
    for row in csv.DictReader(reference.open()):
        if row['Object']=='Road' and row['Flooded'] in {'True','False'} and 'EMPTY' not in row['Wkt_Pix']:
            labels[row['ImageId']].append(row)
    pairs={Path(r['pre-event image']).stem:r for r in csv.DictReader(mapping.open())}
    selected=[]; occupied=[]; rng=random.Random(42)
    for group,split,count in [('0','train',8),('1','validation',2),('2','test',4)]:
        candidates=[k for k in sorted(labels) if k.split('_')[1]==group and k in pairs]
        positive=[k for k in candidates if any(r['Flooded']=='True' for r in labels[k])]
        negative=[k for k in candidates if not any(r['Flooded']=='True' for r in labels[k])]
        rng.shuffle(positive);rng.shuffle(negative)
        kept=Counter()
        for image_id in positive+negative:
            kind='positive' if image_id in positive else 'negative'
            quota=count//2
            if kept[kind]>=quota:continue
            pair=pairs[image_id]
            pre=fetch(BASE+'PRE-event/'+pair['pre-event image'],out/pair['pre-event image'])
            with rasterio.open(pre) as src:
                bounds=transform_bounds(src.crs,'EPSG:3857',*src.bounds)
                # Avoid cross-split footprints with 250m buffers in Web Mercator.
                if any(other!=split and not (bounds[2]+250 < b[0] or b[2]+250 < bounds[0] or bounds[3]+250 < b[1] or b[3]+250 < bounds[1]) for other,b in occupied):continue
                crs,transform,width,height=src.crs,src.transform,src.width,src.height
            post_name=pair['post-event image 1']
            if not post_name:continue
            post=fetch(BASE+'POST-event/'+post_name,out/post_name)
            with rasterio.open(post) as src:
                aligned=np.zeros((3,height,width),dtype=np.uint8)
                for band in range(3):
                    reproject(src.read(band+1),aligned[band],src_transform=src.transform,src_crs=src.crs,dst_transform=transform,dst_crs=crs,resampling=Resampling.bilinear)
                coverage=np.zeros((height,width),dtype=np.uint8)
                reproject(src.dataset_mask(),coverage,src_transform=src.transform,src_crs=src.crs,dst_transform=transform,dst_crs=crs,resampling=Resampling.nearest)
            # Mark overlapping contradictory road corridors unknown.
            masks=[]
            for flooded in ['False','True']:
                geoms=[wkt.loads(r['Wkt_Pix']).buffer(4) for r in labels[image_id] if r['Flooded']==flooded]
                masks.append(rasterize([(g,1) for g in geoms],out_shape=(height,width),fill=0,dtype='uint8') if geoms else np.zeros((height,width),dtype=np.uint8))
            mask=np.full((height,width),255,dtype=np.uint8)
            mask[masks[0]>0]=0;mask[masks[1]>0]=1
            mask[((masks[0]>0)&(masks[1]>0)) | (coverage==0)]=255
            image_path=out/(image_id+'.png'); mask_path=out/(image_id+'_mask.png')
            Image.fromarray(np.moveaxis(aligned,0,-1)).save(image_path)
            Image.fromarray(mask).save(mask_path)
            selected.append({'image':str(image_path),'mask':str(mask_path),'split':split,'spatial_group':'acquisition_'+group,'source_image_id':image_id,'post_image':post_name,'bounds_epsg3857':bounds,'label_counts':dict(Counter(int(v) for v in mask.flatten()))})
            occupied.append((split,bounds));kept[kind]+=1
            print(split,image_id,dict(kept),flush=True)
            if sum(kept.values())==count:break
        if sum(kept.values())<count:raise RuntimeError(f'Insufficient separated samples for {split}: {kept}')
    (out/'manifest.json').write_text(json.dumps(selected,indent=2))
    (out/'methodology.json').write_text(json.dumps({'dataset':'SpaceNet 8 Louisiana East','license':'CC-BY-SA-4.0','seed':42,'task':'flood state on labeled road corridors only','road_buffer_source_pixels':4,'background_and_unknown':255,'registration':'georeferencing-based rasterio bilinear warp; residual misregistration uncorrected','split':'three pre-event acquisition groups; cross-split footprints separated by 250m in Web Mercator; 8 train,2 validation,4 test, half flood-positive tiles','limitations':['tiny pilot, not representative event-level validation','test same event as training','Web Mercator distances approximate','road corridor width convention is derived, not official segmentation labels','not all-image flood segmentation; outside labeled roads ignored']},indent=2))
if __name__=='__main__': main()
