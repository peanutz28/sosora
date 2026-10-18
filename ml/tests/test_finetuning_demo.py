import numpy as np
import pytest
from scripts.ml.build_finetuning_demo import class_overlay, verify_counts


def test_palette_and_support_are_shared_without_unknown_predictions():
    labels = np.array([[0, 1, 255], [1, 0, 255]])
    reference = class_overlay(labels, labels != 255)
    prediction = class_overlay(np.array([[0, 1, 1], [1, 0, 0]]), labels != 255)
    assert np.array_equal(reference, prediction)
    assert reference[0, 0].tolist() == [103, 219, 173, 230]
    assert reference[0, 1].tolist() == [255, 120, 92, 230]
    assert not reference[:, 2].any()


def test_bad_classes_and_misaligned_support_fail():
    with pytest.raises(ValueError):
        class_overlay(np.array([[255]]), np.array([[True]]))
    with pytest.raises(ValueError):
        class_overlay(np.zeros((2, 2)), np.ones((1, 2), dtype=bool))


def test_new_assets_must_reproduce_saved_counts():
    counts = dict(tp=3, fp=2, fn=1, valid_pixels=9)
    verify_counts(counts, counts)
    with pytest.raises(ValueError, match='saved validation'):
        verify_counts(dict(counts, fp=3), counts)
