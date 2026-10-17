import pytest
from ml.vision.evaluate import binary_metrics

def test_counts_and_ignore():
    result = binary_metrics([1,1,0,1], [1,0,1,255])
    assert result['tp'] == result['fp'] == result['fn'] == 1
    assert result['iou'] == pytest.approx(1/3)
    assert result['f1'] == 0.5

def test_empty_not_perfect():
    assert binary_metrics([0], [0])['iou'] is None
