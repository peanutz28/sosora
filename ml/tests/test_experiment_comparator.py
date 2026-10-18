import pytest
import torch
from ml.experiments.train_comparator import UNet, validate_manifest


def test_unet_output_and_ignored_loss():
    model=UNet(width=2)
    x=torch.randn(1,3,32,32)
    y=torch.full((1,32,32),255,dtype=torch.long); y[:,0,:]=1
    out=model(x)
    assert out.shape==(1,2,32,32)
    loss=torch.nn.functional.cross_entropy(out,y,ignore_index=255)
    loss.backward()
    assert torch.isfinite(loss)


def test_final_rejected_before_opening():
    with pytest.raises(ValueError,match='rejects final/test'):
        validate_manifest([dict(split='final',spatial_group='sealed',image='/nonexistent',mask='/nonexistent')])


def test_spatial_leakage_rejected():
    rows=[dict(split=s,spatial_group='same',image=s,mask=s+'mask') for s in ['train','validation']]
    with pytest.raises(ValueError,match='Spatial group leakage'): validate_manifest(rows)


def test_unet_four_downsampling_stages_and_capacity():
    model=UNet()
    assert sum(p.numel() for p in model.parameters()) == 1962642
    assert model(torch.zeros(1,3,32,48)).shape == (1,2,32,48)


def test_unreviewed_preparation_blocks_full_training_but_allows_benchmark(tmp_path):
    import json
    from ml.experiments.train_comparator import require_quality_review
    manifest=tmp_path/'crop_manifest.json'
    (tmp_path/'readiness.json').write_text(json.dumps({'status':'manual_quality_review_required'}))
    require_quality_review(manifest,True)
    with pytest.raises(ValueError,match='quality review'):
        require_quality_review(manifest,False)
    (tmp_path/'readiness.json').write_text(json.dumps({'status':'manual_quality_review_completed'}))
    require_quality_review(manifest,False)
