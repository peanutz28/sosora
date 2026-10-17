"""Local SOSora demo: static assets and a fixed loopback ML API proxy.
No routing decisions, training, publishing, or paid infrastructure actions.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
from pathlib import Path
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
VIEWER=ROOT/'docs/ml/viewer'
sys.path.insert(0, str(ROOT))
GET_ROUTES={'/health','/ml/model-info','/ml/images','/ml/metrics','/ml/llm-health'}
POST_ROUTES={'/ml/predict','/ml/incident/parse','/ml/incident/explain'}


def prepare_assets():
    import numpy as np
    from PIL import Image
    import rasterio
    from rasterio.warp import reproject,Resampling,transform_bounds
    from rasterio.transform import from_bounds
    assets=VIEWER/'assets';assets.mkdir(exist_ok=True)
    registrations=json.loads((ROOT/'data/manifests/native_demo.json').read_text())
    sources=[
      ('chimney','noaa_chimney_rock_20241007','Chimney Rock','Main Street, North Carolina','October 7, 2024','Post-storm response','ml/artifacts/demo_noaa_chimney_20241007/prediction.json'),
      ('swannanoa','helene_swannanoa_roads_spring2025','Swannanoa','North Carolina','Spring 2025','Recovery imagery','ml/artifacts/demo_helene_native/prediction.json'),
      ('validation','sn8_road_validation_10400100684A4B00_1_17_85','Louisiana','SpaceNet 8 · Hurricane Ida','2021 · exact date unknown','Validation sample','ml/artifacts/demo_flood_native_validation/prediction.json'),
    ]
    scenes=[]
    for key,image_id,title,subtitle,date,period,prediction_path in sources:
        entry=next(r for r in registrations if r['image_id']==image_id)
        with rasterio.open(ROOT/entry['path']) as src:
            bounds=transform_bounds(src.crs,'EPSG:3857',*src.bounds,densify_pts=21)
            width=min(1500,src.width);height=max(1,round(width*(bounds[3]-bounds[1])/(bounds[2]-bounds[0])))
            transform=from_bounds(*bounds,width,height)
            rgb=np.zeros((3,height,width),dtype='uint8')
            for band in range(3):
                reproject(src.read(band+1),rgb[band],src_transform=src.transform,src_crs=src.crs,dst_transform=transform,dst_crs='EPSG:3857',resampling=Resampling.bilinear)
            Image.fromarray(np.moveaxis(rgb,0,-1)).save(assets/(key+'.jpg'),quality=95)
            roi=np.array(Image.open(ROOT/entry['road_roi_path']))
            warped=np.zeros((height,width),dtype='uint8')
            reproject((roi>0).astype('uint8'),warped,src_transform=src.transform,src_crs=src.crs,dst_transform=transform,dst_crs='EPSG:3857',resampling=Resampling.nearest)
            rgba=np.zeros((height,width,4),dtype='uint8');rgba[warped>0]=[225,242,241,165]
            Image.fromarray(rgba).save(assets/(key+'-roads.png'))
            if key=='validation':
                mask=np.asarray(Image.open(ROOT/'ml/artifacts/sn8_pilot/10400100684A4B00_1_17_85_mask.png'))
                label_warp=np.full((height,width),255,dtype='uint8')
                reproject(mask,label_warp,src_transform=src.transform,src_crs=src.crs,dst_transform=transform,dst_crs='EPSG:3857',resampling=Resampling.nearest)
                labels=np.zeros_like(rgba);labels[label_warp==1]=[255,120,92,230];labels[label_warp==0]=[103,219,173,230]
                Image.fromarray(labels).save(assets/'validation-labels.png')
                error_rgba=np.array(Image.open(VIEWER/'errors.png'))
                errors=np.zeros((height,width,4),dtype='uint8')
                for band in range(4):
                    reproject(error_rgba[:,:,band],errors[:,:,band],src_transform=src.transform,src_crs=src.crs,dst_transform=transform,dst_crs='EPSG:3857',resampling=Resampling.nearest)
                Image.fromarray(errors).save(assets/'validation-errors.png')
        pred=json.loads((ROOT/prediction_path).read_text())
        if pred['inference_mode']!='real':raise ValueError('Only real predictions can be packaged')
        (assets/(key+'-prediction.json')).write_text(json.dumps(pred))
        scenes.append({'key':key,'image_id':image_id,'title':title,'subtitle':subtitle,'date':date,'period':period,'image':f'assets/{key}.jpg','roads':f'assets/{key}-roads.png','saved_prediction':f'assets/{key}-prediction.json','bounds_mercator':list(bounds),'width':width,'height':height,'dataset':entry['dataset'],'source_url':entry['source_url'],'date_evidence_url':entry.get('date_evidence_url'),'capture_date':entry.get('capture_date'),'warnings':entry.get('warnings',[]),'road_source':entry.get('road_roi_source'),'ground_truth_available':key=='validation'})
    external=json.loads((ROOT/'ml/artifacts/sn8_frozen_external/evaluation/evaluation.json').read_text())
    training=json.loads((ROOT/'ml/artifacts/sn8_native_cpu_v2/evaluation_config.json').read_text())
    validation=json.loads((ROOT/'ml/artifacts/sn8_native_cpu_v2_validation/evaluation.json').read_text())
    payload={'scenes':scenes,'external_evaluation':{'dataset':external.get('dataset'),'tile_count':external['tile_count'],'metrics':external['metrics'],'caveats':external['caveats'],'decision':external['decision'],'evaluated_utc':external.get('evaluated_utc')},'training':{'selected_epoch':training['selected_epoch'],'history':training['history'],'crop_count':53,'validation_crops':11,'device':'CPU'},'validation_metrics':validation['metrics'],'checkpoint_id':external['provenance']['checkpoint_id'],'model_name':'SOSora Road Vision','architecture':'SegFormer-B0','task':'Flood state within independently mapped road corridors','version':'native-v2'}
    (VIEWER/'console-data.json').write_text(json.dumps(payload))
    from scripts.ml.build_finetuning_demo import build
    build(VIEWER/'assets/finetuning')
    print('Prepared',len(scenes),'real georeferenced scenes and validation fine-tuning comparison',flush=True)


class ConsoleHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()

    def do_GET(self):
        if self.path.startswith('/api/'):
            return self.proxy('GET')
        if self.path=='/health':
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"status":"ok","service":"sosora-console"}');return
        super().do_GET()

    def do_POST(self):
        if not self.path.startswith('/api/'):
            self.send_error(404);return
        self.proxy('POST')

    def proxy(self,method):
        path=self.path.removeprefix('/api')
        if path not in (GET_ROUTES if method=='GET' else POST_ROUTES):
            self.send_error(404,'Unknown API route');return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=65536:self.send_error(413);return
            body=self.rfile.read(length) if method=='POST' else None
            request=urllib.request.Request('http://127.0.0.1:8002'+path,data=body,method=method,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=110) as upstream:
                result=upstream.read();status=upstream.status
        except urllib.error.HTTPError as exc:
            result=exc.read();status=exc.code
        except (urllib.error.URLError,TimeoutError,OSError):
            result=b'{"detail":"ML service is unavailable. Start the native model service on port 8002."}';status=503
        except ValueError:
            self.send_error(400);return
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(result)));self.end_headers();self.wfile.write(result)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=9030);parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    prepare_assets()
    if args.prepare_only:return
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(ConsoleHandler,directory=str(VIEWER)))
    print(f'SOSora console: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
