"""Small official NOAA October2024 NC tile mosaic and independent NCDOT road ROI."""
import datetime,hashlib,io,json,math,urllib.request
from pathlib import Path
from urllib.parse import urlencode
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from rasterio.features import rasterize
from rasterio.warp import transform as transform_coordinates,transform_bounds
from shapely.geometry import shape
from shapely.ops import transform as transform_geometry

OUT=Path('ml/artifacts/noaa_chimney_mainst_20241007')
MANIFEST=Path('data/manifests/noaa_chimney_mainst_20241007.json')
CATALOG='https://storms.ngs.noaa.gov/storms/helene/services/index.json'
LAYER='20241007a_RGB'
ROAD='https://gis11.services.ncdot.gov/arcgis/rest/services/NCDOT_StateMaintainedRoadsQtr/MapServer/0'

def main():
    if OUT.exists() or MANIFEST.exists():raise ValueError('Do not overwrite existing artifacts')
    OUT.mkdir(parents=True)
    sources=[];total=0
    def fetch(url,name):
        nonlocal total
        with urllib.request.urlopen(url,timeout=30) as response:
            b=response.read(4000001)
        total+=len(b)
        if len(b)>4000000 or total>12000000:raise ValueError('Small-sample download budget exceeded')
        (OUT/name).write_bytes(b);sources.append({'url':url,'path':str(OUT/name),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
        return b
    catalog=json.loads(fetch(CATALOG,'noaa_catalog.json'));layer=next(r for r in catalog if r['name']==LAYER)
    metadata=json.loads(fetch(layer['tiles'][0].split('{z}')[0]+'metadata.json','noaa_layer_metadata.json'))
    lon,lat=-82.24771166228379,35.43956319111714;zoom=18;n=2**zoom
    xf=(lon+180)/360*n;yf=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
    x0=math.floor(xf)-(1 if xf%1<.5 else 0);y0=math.floor(yf)-(1 if yf%1<.5 else 0)
    mosaic=Image.new('RGBA',(512,512));tiles=[]
    for dy in range(2):
        for dx in range(2):
            x,y=x0+dx,y0+dy;url=layer['tiles'][0].format(z=zoom,x=x,y=y)
            b=fetch(url,f'tile_{zoom}_{x}_{y}.image');im=Image.open(io.BytesIO(b)).convert('RGBA')
            if im.size!=(256,256):raise ValueError('Unexpected NOAA tile dimensions')
            mosaic.paste(im,(dx*256,dy*256));tiles.append({'z':zoom,'x':x,'y':y,'url':url})
    rgba=np.asarray(mosaic);valid=rgba[:,:,3]>0
    if valid.mean()<.5:raise ValueError(f'Insufficient real imagery coverage: {valid.mean()}')
    resolution=2*math.pi*6378137/(256*n);origin=math.pi*6378137
    affine=from_origin(-origin+x0*256*resolution,origin-y0*256*resolution,resolution,resolution)
    image_path=OUT/'noaa_chimney_20241007.tif'
    with rasterio.open(image_path,'w',driver='GTiff',width=512,height=512,count=3,dtype='uint8',crs='EPSG:3857',transform=affine,compress='deflate') as dest:
        dest.write(np.moveaxis(rgba[:,:,:3],-1,0));dest.write_mask(valid.astype('uint8')*255)
    Image.fromarray(rgba[:,:,:3]).save(OUT/'source_preview.jpg',quality=94)
    with rasterio.open(image_path) as source:bounds=transform_bounds(source.crs,'EPSG:4326',*source.bounds)
    query=ROAD+'/query?'+urlencode({'f':'geojson','where':'1=1','geometry':','.join(map(str,bounds)),'geometryType':'esriGeometryEnvelope','inSR':4326,'outSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'*','returnGeometry':'true','resultRecordCount':2000})
    roads=json.loads(fetch(query,'ncdot_roads.geojson'))
    if roads.get('error') or roads.get('exceededTransferLimit') or not roads.get('features'):raise ValueError('No complete independent road query')
    to_metric=lambda x,y,z=None:transform_coordinates('EPSG:4326','EPSG:32617',x,y)
    to_grid=lambda x,y,z=None:transform_coordinates('EPSG:32617','EPSG:3857',x,y)
    geoms=[transform_geometry(to_grid,transform_geometry(to_metric,shape(f['geometry'])).buffer(3)) for f in roads['features'] if f.get('geometry')]
    roi=rasterize([(g,1) for g in geoms],out_shape=(512,512),transform=affine,fill=0,dtype='uint8');roi[~valid]=0
    if not roi.any():raise ValueError('Road geometry does not intersect valid imagery')
    roi_path=OUT/'independent_roads.png';Image.fromarray(roi).save(roi_path)
    provenance={'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'location':'Chimney Rock, North Carolina','requested_center_lonlat':[lon,lat],'bounds_epsg4326':list(bounds),'layer':layer,'layer_metadata':metadata,'tiles':tiles,'tile_scheme':'XYZ WebMercator, consistent with official MapLibre layer configuration','crs':'EPSG:3857','transform':list(affine),'shape':[512,512],'webmercator_pixel_metres':resolution,'capture_date':'2024-10-07 (NOAA dated layer; exact flight time unverified)','date_evidence':'https://oceanservice.noaa.gov/news/sep24/ngs-storm-imagery-helene.html','coverage_fraction':float(valid.mean()),'road_source':ROAD,'road_source_publication':'2026-06-28 per source service; temporal mismatch','road_features':len(roads['features']),'road_buffer_metres_each_side':3,'road_buffer_crs':'EPSG:32617','road_pixels':int(roi.sum()),'flood_labels_used':False,'download_bytes':total,'sources':sources,'warnings':['NOAA informational/planning imagery, no guarantee of completeness or accuracy','Mosaicked visual tiles are processed imagery, not raw sensor radiometry','Independent June2026 road geometry may differ from October2024 roads; state-maintained roads only','No flood truth or accuracy measurement for this image','Model trained on Louisiana satellite imagery; transfer/domain shift may cause false positives or misses']}
    (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2))
    item={'image_id':'noaa_chimney_rock_20241007','path':str(image_path),'road_roi_path':str(roi_path),'dataset':'NOAA NGS Hurricane Helene emergency response imagery','event':'Hurricane Helene aftermath, Chimney Rock NC','capture_date':provenance['capture_date'],'source_url':CATALOG,'date_evidence_url':provenance['date_evidence'],'source_layer':LAYER,'source_tiles':tiles,'license':'NOAA attribution; inspect source license disclaimer before redistribution. No publication performed.','ground_truth':False,'split':'unlabeled_transfer_demo','road_roi_source':ROAD,'registration':'Georeference derived from documented XYZ WebMercator grid; road vectors transformed to exact raster grid','warnings':provenance['warnings']}
    MANIFEST.write_text(json.dumps([item],indent=2)+'\n')
    print(json.dumps({'manifest':str(MANIFEST),'capture_date':item['capture_date'],'bounds':bounds,'download_bytes':total,'road_pixels':int(roi.sum()),'coverage_fraction':float(valid.mean())},indent=2))

if __name__=='__main__':main()
