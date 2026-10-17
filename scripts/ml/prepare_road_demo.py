"""Register georeferenced RGB and a flood-state-independent annotated-road ROI."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
import rasterio
from rasterio.features import rasterize
from shapely import wkt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=['validation','test'],default='validation')
    parser.add_argument('--output',required=True)
    parser.add_argument('--manifest-output',required=True)
    args=parser.parse_args()
    out=Path(args.output);manifest_out=Path(args.manifest_output)
    if out.exists() or manifest_out.exists():
        raise ValueError('Outputs must be new; never overwrite evidence')
    rows=json.loads(Path('ml/artifacts/sn8_pilot/manifest.json').read_text())
    labels=list(csv.DictReader(open('ml/artifacts/sn8_pilot/reference.csv')))
    images=json.loads(Path('data/manifests/images.json').read_text())
    out.mkdir(parents=True)
    for row in rows:
        if row['split']!=args.split:continue
        image_id=row['source_image_id']
        image=np.asarray(Image.open(row['image']).convert('RGB'))
        pre=Path('ml/artifacts/sn8_pilot')/(image_id+'.tif')
        with rasterio.open(pre) as source:
            profile=dict(driver='GTiff',height=source.height,width=source.width,count=3,dtype='uint8',crs=source.crs,transform=source.transform,compress='deflate')
        geoms=[wkt.loads(r['Wkt_Pix']).buffer(4) for r in labels if r['ImageId']==image_id and r['Object']=='Road' and 'EMPTY' not in r['Wkt_Pix']]
        # Deliberately never read the Flooded field: road locations condition the model,
        # while flood state must come exclusively from the image model.
        roi=rasterize([(g,1) for g in geoms],out_shape=image.shape[:2],fill=0,dtype='uint8')
        tif=out/(image_id+'.tif');roi_path=out/(image_id+'_roads.png')
        with rasterio.open(tif,'w',**profile) as dest:dest.write(np.moveaxis(image,-1,0))
        Image.fromarray(roi).save(roi_path)
        images.append({'image_id':'sn8_road_'+args.split+'_'+image_id,'path':str(tif),'road_roi_path':str(roi_path),'dataset':'SpaceNet 8 Louisiana East','event':'Hurricane Ida 2021 (not Helene)','capture_date':None,'source_url':'https://spacenet-dataset.s3.amazonaws.com/spacenet/SN8_floods/Louisiana-East_Training_Public/POST-event/'+row['post_image'],'license':'CC-BY-SA-4.0','ground_truth':False,'split':args.split,'source_image_id':image_id,'registration':'Post RGB warped to pre-event georeferencing; residual registration error possible','road_roi_source':'Official road centerline geometry buffered 4 source pixels; no Flooded values used','warnings':['Conditioned on annotated road locations; road extraction is not evaluated','Flood labels are not supplied to inference; predictions remain unverified']})
    manifest_out.parent.mkdir(parents=True,exist_ok=True)
    manifest_out.write_text(json.dumps(images,indent=2)+'\n')
    print(json.dumps({'registered':len(images),'manifest':str(manifest_out)}))

if __name__=='__main__':main()
