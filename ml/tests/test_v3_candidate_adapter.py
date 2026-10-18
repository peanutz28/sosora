import torch
from ml.experiments.train_comparator import UNet
from ml.experiments.v3_models import load_candidate


def test_raw_unet_checkpoint_reloads_without_changing_logits(tmp_path):
    torch.set_num_threads(2)
    model=UNet().eval();path=tmp_path/'best.pt';torch.save(model.state_dict(),path)
    restored=load_candidate('unet',path,tmp_path/'unused-base')
    pixels=torch.randn(1,3,32,48)
    with torch.inference_mode():
        assert torch.equal(restored(pixel_values=pixels).logits,model(pixels))
    assert restored.config.sosora_tile_size==256
    assert restored.config.requires_road_roi


def test_wrong_checkpoint_shape_is_rejected(tmp_path):
    import pytest
    path=tmp_path/'wrong.pt';torch.save(UNet(width=2).state_dict(),path)
    with pytest.raises(RuntimeError):load_candidate('unet',path,tmp_path/'unused-base')
