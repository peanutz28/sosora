import importlib.util
import json
from pathlib import Path
import numpy as np
from PIL import Image
import pytest

spec = importlib.util.spec_from_file_location('native_eval', Path(__file__).resolve().parents[2]/'scripts/ml/evaluate_road_tiles.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_same_native_support_and_ignored_pixels(tmp_path):
    target = np.array([[0,1,255],[1,0,255]], dtype=np.uint8)
    image, mask = tmp_path/'image.png', tmp_path/'mask.png'
    Image.fromarray(np.zeros((2,3,3),dtype=np.uint8)).save(image)
    Image.fromarray(target).save(mask)
    manifest = tmp_path/'manifest.json'
    manifest.write_text(json.dumps([dict(image=str(image), mask=str(mask), split='validation', spatial_group='v')]))
    calls=[]
    def infer(model, processor, image):
        calls.append((model,image.size))
        prediction = np.array([[0,1,1],[0,1,1]]) if model=='tuned' else np.ones((2,3),dtype=int)
        return np.stack([prediction==0, prediction==1]).astype(float)
    result = evaluation.evaluate(manifest,'tuned',tmp_path/'result',baseline_model='baseline',
                                 loader=lambda path:(path,None), infer=infer)
    assert calls == [('tuned',(3,2)),('baseline',(3,2))]
    tuned = result['metrics']['tuned']
    assert (tuned['tp'],tuned['fp'],tuned['fn'],tuned['valid_pixels']) == (1,1,1,4)
    assert tuned['f1'] == 0.5
    assert result['metrics']['baseline'] == result['metrics']['all_positive']
    assert result['metrics']['all_negative']['fn'] == 2
    assert all(m['valid_pixels']==4 for m in result['metrics'].values())
    assert json.loads((tmp_path/'result/evaluation.json').read_text())['scale']=='original_native_resolution'
    with pytest.raises(ValueError, match='new or empty'):
        evaluation.evaluate(manifest,'tuned',tmp_path/'result')


def test_aggregate_counts_before_ratio():
    result=evaluation.aggregate([dict(tp=1,fp=0,fn=1,valid_pixels=2),dict(tp=0,fp=9,fn=0,valid_pixels=9)])
    assert result['f1']==2/12
    assert result['valid_pixels']==11
