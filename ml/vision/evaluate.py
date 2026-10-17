"""Pixel-level binary metrics with explicit undefined denominators."""
import numpy as np

def binary_metrics(prediction, target, ignore_index=255):
    prediction, target = np.asarray(prediction), np.asarray(target)
    if prediction.shape != target.shape:
        raise ValueError('Prediction/target shapes differ')
    valid = target != ignore_index
    if not np.isin(target[valid], [0,1]).all():
        raise ValueError('Targets must be binary or ignore_index')
    p, t = prediction[valid].astype(bool), target[valid].astype(bool)
    tp, fp, fn = int((p&t).sum()), int((p&~t).sum()), int((~p&t).sum())
    def ratio(a,b):
        return a/b if b else None
    return {'tp':tp,'fp':fp,'fn':fn,'valid_pixels':int(valid.sum()),'iou':ratio(tp,tp+fp+fn),'precision':ratio(tp,tp+fp),'recall':ratio(tp,tp+fn),'f1':ratio(2*tp,2*tp+fp+fn)}
