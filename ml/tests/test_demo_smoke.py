import importlib.util
from pathlib import Path
import json
import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_geom

script = Path(__file__).resolve().parents[2] / 'scripts/ml/demo_smoke.py'
spec = importlib.util.spec_from_file_location('demo_smoke', script)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_geojson_preserves_geometries_and_provenance():
    geometry = {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
    result = demo.geojson({'crs':'EPSG:4326', 'image_id':'a', 'model_provenance':{'task':'test'},
                          'detections':[{'geometry':geometry, 'class':'road', 'confidence':.8}]})
    assert result['features'][0]['geometry'] == geometry
    assert result['features'][0]['properties']['confidence'] == .8
    assert result['model_provenance']['task'] == 'test'


def test_pixel_predictions_cannot_be_exported_as_georeferenced():
    with pytest.raises(ValueError, match='EPSG:4326'):
        demo.geojson({'crs':'PIXEL'})


def test_overlay_transforms_geometry_back_to_source_crs(tmp_path):
    source = tmp_path / 'source.tif'
    with rasterio.open(source, 'w', driver='GTiff', height=64, width=64, count=3,
                       dtype='uint8', crs='EPSG:3857', transform=from_origin(1000000, 1000000, 10, 10)) as dst:
        dst.write(np.full((3,64,64), 100, dtype='uint8'))
    native = {'type':'Polygon', 'coordinates':[[[1000160,999840], [1000480,999840],
              [1000480,999520], [1000160,999520], [1000160,999840]]]}
    prediction = {'crs':'EPSG:4326', 'image_width':64, 'image_height':64,
                  'detections':[{'class':'flooded_road', 'geometry':transform_geom('EPSG:3857','EPSG:4326',native)}]}
    output = tmp_path / 'overlay.jpg'
    demo.overlay(prediction, source, output)
    pixels = np.asarray(Image.open(output))
    assert pixels[32,32,0] > 150
    assert pixels[32,32,1] < 100
    assert np.all(abs(pixels[4,4].astype(int)-100) < 3)


def test_existing_evidence_is_never_overwritten(tmp_path):
    with pytest.raises(ValueError, match='new directory'):
        demo.run_smoke(None, 'id', tmp_path, tmp_path/'missing.json')


def test_unknown_local_image_is_rejected_before_api_calls(tmp_path):
    manifest = tmp_path/'images.json'
    manifest.write_text(json.dumps([]))
    with pytest.raises(ValueError, match='absent'):
        demo.run_smoke(None, 'id', tmp_path/'new', manifest)


def test_url_mode_cannot_reconfigure_service():
    with pytest.raises(SystemExit):
        demo.main(['--image-id','id','--output','new','--url','http://localhost:8000','--model','other'])
