"""Run from repository root: python -m scripts.ml.baseline."""
import json
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
import rasterio
import numpy as np
from rasterio.warp import transform_geom
from ml.inference.app import images
from ml.vision.predict import predict

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image-id', default='sn8_louisiana_post_0_10_2')
    args = parser.parse_args()
    entry = next(row for row in images() if row['image_id'] == args.image_id)
    prefix = 'baseline' if args.image_id == 'sn8_louisiana_post_0_10_2' else args.image_id
    result = predict(entry, 0.3)
    out = Path('ml/artifacts'); out.mkdir(exist_ok=True)
    (out/(prefix+'_prediction.json')).write_text(json.dumps(result, indent=2))
    with rasterio.open(entry['path']) as src:
        image = Image.fromarray(np.moveaxis(src.read([1,2,3]),0,-1)).convert('RGBA')
        overlay = Image.new('RGBA', image.size)
        draw = ImageDraw.Draw(overlay)
        for detection in result['detections']:
            geom = transform_geom('EPSG:4326',src.crs,detection['geometry']) if src.crs else detection['geometry']
            if geom['type'] != 'Polygon':
                continue
            points = [(~src.transform)*(x,y) for x,y in geom['coordinates'][0]]
            draw.polygon(points, fill=(255,60,30,90), outline=(255,60,30,255))
        Image.alpha_composite(image, overlay).convert('RGB').save(out/(prefix+'_overlay.jpg'))
    print(json.dumps({'detections':len(result['detections']),'latency_ms':result['latency_ms'],'crs':result['crs']}))
if __name__ == '__main__':
    main()
