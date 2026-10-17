from types import SimpleNamespace
import numpy as np
import torch
from PIL import Image
from ml.vision.tiled import tiled_probabilities


def test_tiling_preserves_extent_and_probability_across_edges():
    class Model:
        def __call__(self,**batch):
            return SimpleNamespace(logits=torch.tensor([[[[0.]],[[2.]]]]))
    processor=lambda **kwargs:{'pixel_values':torch.zeros(1,3,32,32)}
    p=tiled_probabilities(Model(),processor,Image.new('RGB',(75,45)),tile_size=32,stride=24)
    assert p.shape==(2,45,75)
    assert np.isfinite(p).all()
    assert np.allclose(p.sum(axis=0),1)
    assert np.allclose(p[1],torch.sigmoid(torch.tensor(2.)).item())
