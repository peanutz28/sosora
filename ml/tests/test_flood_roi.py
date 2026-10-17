"""Offline guard tests: invalid road ROIs must never reach model inference."""
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
import rasterio
from rasterio.transform import from_origin
import torch
from ml.vision import predict as vision


@pytest.fixture
def inference(monkeypatch, tmp_path):
    path = tmp_path / 'image.tif'
    with rasterio.open(path, 'w', driver='GTiff', width=4, height=4,
                       count=3, dtype='uint8', transform=from_origin(1, 5, 1, 1)) as dst:
        dst.write(np.ones((3, 4, 4), dtype='uint8'))
    class Model:
        config = SimpleNamespace(id2label={0: 'background', 1: 'flooded_road'})
        _sosora_provenance = dict(model_id='loaded', checkpoint_id='checkpoint', run_id='run',
                                  task='flooded_road_segmentation', requires_road_roi=True,
                                  label_map={'0': 'background', '1': 'flooded_road'}, identity_status='verified')
        calls = 0
        def __call__(self, **kwargs):
            self.calls += 1
            logits = torch.zeros((1, 2, 4, 4))
            logits[:, 1] = 10
            return SimpleNamespace(logits=logits)
    model = Model()
    monkeypatch.setattr(vision, 'load_model', lambda: ('loaded', model, lambda **kwargs: {}))
    return model, {'image_id': 'sample', 'path': str(path)}, tmp_path


@pytest.mark.parametrize('name', ['flooded_road', 'road flooded', 'road-flooded', 'non_flooded_road'])
def test_flood_labels_require_roi(inference, name):
    model, entry, _ = inference
    model._sosora_provenance['requires_road_roi'] = False
    model.config = SimpleNamespace(id2label={0: 'background', 1: name})
    with pytest.raises(ValueError, match='requires road_roi_path'):
        vision.predict(entry, 0.5)
    assert model.calls == 0


@pytest.mark.parametrize('kind', ['missing', 'rgb', 'shape', 'fractional', 'nonfinite', 'empty', 'mixed_binary'])
def test_invalid_roi_stops_before_forward(inference, kind):
    model, entry, tmp_path = inference
    roi = np.ones((4, 4), dtype='uint8')
    if kind == 'rgb': roi = np.ones((4, 4, 3), dtype='uint8')
    if kind == 'shape': roi = np.ones((3, 4), dtype='uint8')
    if kind == 'fractional': roi = np.full((4, 4), 0.5, dtype='float32')
    if kind == 'nonfinite': roi = np.full((4, 4), np.nan, dtype='float32')
    if kind == 'empty': roi[:] = 0
    if kind == 'mixed_binary': roi[0, 0] = 255
    path = tmp_path / 'roi.tif'
    if kind != 'missing': Image.fromarray(roi).save(path)
    entry['road_roi_path'] = str(path)
    with pytest.raises(ValueError, match='Road ROI'):
        vision.predict(entry, 0.5)
    assert model.calls == 0


@pytest.mark.parametrize('value', [1, 255])
def test_valid_binary_roi_and_loaded_provenance(inference, monkeypatch, value):
    model, entry, tmp_path = inference
    roi = np.zeros((4, 4), dtype='uint8')
    roi[:2] = value
    path = tmp_path / 'roi.png'
    Image.fromarray(roi).save(path)
    entry['road_roi_path'] = str(path)
    monkeypatch.setenv('VISION_MODEL', 'changed-after-load')
    result = vision.predict(entry, 0.5)
    assert model.calls == 1
    assert result['model_provenance']['model_id'] == 'loaded'
    assert {item['class'] for item in result['detections']} == {'flooded_road'}
    assert result['detections'][0]['geometry']['coordinates'][0] == [(0., 0.), (0., 2.), (4., 2.), (4., 0.), (0., 0.)]


def test_ade_baseline_without_roi(inference):
    model, entry, _ = inference
    model.config = SimpleNamespace(id2label={0: 'road', 1: 'water'})
    model._sosora_provenance['requires_road_roi'] = False
    assert vision.predict(entry, 0.5)['detections']
    assert model.calls == 1


def test_roi_requires_valid_data_intersection(inference):
    model, entry, tmp_path = inference
    with rasterio.open(entry['path'], 'r+') as dst:
        mask = np.zeros((4, 4), dtype='uint8')
        mask[:2] = 255
        dst.write_mask(mask)
    roi = np.zeros((4, 4), dtype='uint8')
    roi[2:] = 1
    path = tmp_path / 'roi.png'
    Image.fromarray(roi).save(path)
    entry['road_roi_path'] = str(path)
    with pytest.raises(ValueError, match='intersect valid'):
        vision.predict(entry, 0.5)
    assert model.calls == 0
