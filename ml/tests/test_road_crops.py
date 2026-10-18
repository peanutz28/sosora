import importlib.util
import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest

spec = importlib.util.spec_from_file_location('road_crops', Path(__file__).resolve().parents[2]/'scripts/ml/prepare_road_crops.py')
crops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crops)


def test_native_pixels_and_untouched_test(tmp_path):
    rng = np.random.default_rng(1)
    rgb = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
    mask = np.full((512, 512), 255, dtype=np.uint8)
    mask[50:58, :] = 0
    mask[400:408, :] = 1
    image_path, mask_path = tmp_path/'rgb.png', tmp_path/'mask.png'
    Image.fromarray(rgb).save(image_path)
    Image.fromarray(mask).save(mask_path)
    rows = [dict(image=str(image_path), mask=str(mask_path), split=s, spatial_group=s, source_image_id=s) for s in ['train', 'validation']]
    # Nonexistent test paths prove test data is not read for crop selection.
    test = dict(image='absent.png', mask='absent-mask.png', split='test', spatial_group='test')
    manifest = tmp_path/'input.json'
    manifest.write_text(json.dumps(rows+[test]))
    result = crops.build(manifest, tmp_path/'output')
    generated = json.loads((tmp_path/'output/manifest.json').read_text())
    assert generated[-1] == test
    for row in generated[:-1]:
        l,t,r,b = row['crop_pixel_bounds']
        np.testing.assert_array_equal(np.asarray(Image.open(row['image'])), rgb[t:b,l:r])
        np.testing.assert_array_equal(np.asarray(Image.open(row['mask'])), mask[t:b,l:r])
        assert row['spatial_group'] == row['split']
        assert sum(row['label_counts'][str(v)] for v in [0,1]) >= 64
    assert result['output_bytes'] < 30*1024*1024
    assert {c[1] > c[2] for c in crops.select_windows(mask)} == {True, False}
    assert crops.select_windows(mask) == crops.select_windows(mask)
    with pytest.raises(ValueError, match='new or empty'):
        crops.build(manifest, tmp_path/'output')


def test_invalid_labels_and_no_padding():
    with pytest.raises(ValueError, match='smaller'):
        crops.select_windows(np.zeros((64,64), dtype=np.uint8))
    with pytest.raises(ValueError, match='labels'):
        crops.select_windows(np.full((256,256), 2, dtype=np.uint8))
    assert crops.select_windows(np.full((256,256), 255, dtype=np.uint8)) == []
