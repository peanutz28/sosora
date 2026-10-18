"""Prepare independently sourced NCDOT road geometry ROI; never flood labels."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
from PIL import Image
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_bounds, transform as transform_coordinates
from shapely.geometry import shape, mapping
from shapely.ops import transform as transform_geometry

SOURCE = 'https://gis11.services.ncdot.gov/arcgis/rest/services/NCDOT_StateMaintainedRoadsQtr/MapServer'
IMAGE = Path('ml/artifacts/images/helene_swannanoa_spring2025.tif')
OUT = Path('ml/artifacts/helene_road_demo')
MANIFEST = Path('data/manifests/helene_road_demo.json')


def main():
    if OUT.exists() or MANIFEST.exists():
        raise ValueError('Outputs must be new; existing evidence is never overwritten')
    with rasterio.open(IMAGE) as src:
        bounds = transform_bounds(src.crs, 'EPSG:4326', *src.bounds)
        width, height, affine, crs = src.width, src.height, src.transform, src.crs
    params = {'f': 'geojson', 'where': '1=1', 'geometry': ','.join(map(str, bounds)),
              'geometryType': 'esriGeometryEnvelope', 'inSR': 4326, 'outSR': 4326,
              'spatialRel': 'esriSpatialRelIntersects', 'outFields': '*',
              'returnGeometry': 'true', 'resultRecordCount': 2000}
    query = SOURCE + '/0/query?' + urlencode(params)
    raw = urlopen(query, timeout=45).read()
    roads = json.loads(raw)
    if roads.get('error') or roads.get('exceededTransferLimit') or not roads.get('features'):
        raise ValueError('Query failed, truncated, or contains no roads: ' + str(roads)[:300])
    metadata = json.load(urlopen(SOURCE + '?f=json', timeout=30))
    to_metric = lambda x, y, z=None: transform_coordinates('EPSG:4326', 'EPSG:32617', x, y)
    to_grid = lambda x, y, z=None: transform_coordinates('EPSG:32617', crs, x, y)
    # Three metres each side is a road corridor convention, not measured road width.
    buffer_metres = 3.0
    corridors = [transform_geometry(to_grid, transform_geometry(to_metric, shape(f['geometry'])).buffer(buffer_metres))
                 for f in roads['features'] if f.get('geometry')]
    roi = rasterize([(g, 1) for g in corridors], out_shape=(height, width), transform=affine,
                    fill=0, dtype='uint8', all_touched=False)
    if not np.any(roi):
        raise ValueError('Independent centerlines do not intersect the image grid')
    OUT.mkdir(parents=True)
    (OUT / 'ncdot_roads.geojson').write_bytes(raw)
    (OUT / 'service_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    roi_path = OUT / 'helene_swannanoa_roads.png'
    Image.fromarray(roi).save(roi_path)
    with rasterio.open(OUT / 'helene_swannanoa_roads.tif', 'w', driver='GTiff', width=width,
                       height=height, count=1, dtype='uint8', crs=crs, transform=affine,
                       compress='deflate') as dst:
        dst.write(roi, 1)
    west, south, east, north = transform_bounds(crs, 'EPSG:32617', *bounds)
    provenance = {'source_url': SOURCE + '/0', 'query_url': query,
                  'retrieved_at': datetime.now(timezone.utc).isoformat(),
                  'source_publication': '2026-06-28 15:11, as reported by service description',
                  'source_copyright': metadata.get('copyrightText'),
                  'source_description': metadata.get('description'),
                  'source_sha256': hashlib.sha256(raw).hexdigest(),
                  'source_features': len(roads['features']), 'source_bytes': len(raw),
                  'query_crs': 'EPSG:4326', 'source_service_crs': metadata.get('spatialReference'),
                  'buffer_crs': 'EPSG:32617', 'buffer_metres_each_side': buffer_metres,
                  'raster_crs': str(crs), 'raster_transform': list(affine),
                  'raster_shape': [height, width], 'bounds_epsg4326': bounds,
                  'approx_pixel_metres': [(east-west)/width, (north-south)/height],
                  'road_pixels': int(roi.sum()), 'road_fraction': float(roi.mean()),
                  'registration': 'Vector coordinates transformed to source raster CRS; rasterized with exactly source transform and shape, pixel-center rule.',
                  'flood_labels_used': False}
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    item = {'image_id': 'helene_swannanoa_roads_spring2025', 'path': str(IMAGE),
            'road_roi_path': str(roi_path), 'dataset': 'NC Helene Orthoimagery 2025',
            'event': 'Helene recovery period; not immediate post-storm',
            'capture_date': 'spring 2025 (source-level; exact date unverified)',
            'source_url': 'https://services.gis.nc.gov/secure/rest/services/Imagery/Orthoimagery_Helene_2025/ImageServer',
            'ground_truth': False, 'split': 'unlabeled_transfer_demo',
            'license': 'Verify NC imagery and NCDOT redistribution terms before publishing',
            'road_roi_source': SOURCE + '/0', 'road_roi_provenance': str(OUT / 'provenance.json'),
            'registration': provenance['registration'],
            'warnings': ['Unlabeled transfer demonstration; no accuracy estimate or verified flood state.',
                         'Spring 2025 recovery imagery is not immediate Helene storm imagery.',
                         'Road geometry published June 2026 may differ from roads at imagery date.',
                         'State-maintained roads only: local/private roads may be absent.',
                         'Three-metre buffer is a corridor convention, not measured pavement width.',
                         'Geographic registration errors between independent sources remain possible.']}
    MANIFEST.write_text(json.dumps([item], indent=2) + '\n')
    print(json.dumps({'manifest': str(MANIFEST), **provenance}, indent=2))


if __name__ == '__main__':
    main()
