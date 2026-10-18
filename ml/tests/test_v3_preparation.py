import numpy as np
from scripts.ml.prepare_v3_experiment import read_allowed_labels, make_masks


def test_sealed_ids_are_filtered_before_label_use(tmp_path):
    path=tmp_path/'reference.csv'
    path.write_text('ImageId,Object,Flooded,Wkt_Pix\ntrain,Road,True,"LINESTRING (2 2, 8 2)"\nfinal,Road,False,INVALID_GEOMETRY\n')
    rows=read_allowed_labels(path,{'train'})
    assert set(rows)=={'train'}
    target=make_masks(rows['train'],(16,16))
    assert (target==1).any() and not (target==0).any()


def test_contradictory_buffer_labels_remain_unknown():
    rows=[{'Flooded':state,'Wkt_Pix':'LINESTRING (4 4, 12 4)'} for state in ['True','False']]
    assert np.all(make_masks(rows,(20,20))==255)


def test_alignment_screen_flags_known_shift_without_applying_correction():
    from scripts.ml.prepare_v3_experiment import alignment_screen
    rng=np.random.default_rng(42)
    before=rng.integers(0,256,size=(1300,1300,3),dtype=np.uint8)
    after=np.roll(before,(8,12),axis=(0,1))
    result=alignment_screen(before,after)
    assert result['best_shift_source_pixels']==[12,8]
    assert result['manual_review_flag']
    assert np.array_equal(after,np.roll(before,(8,12),axis=(0,1)))


def test_alignment_screen_does_not_claim_signal_for_blank_images():
    from scripts.ml.prepare_v3_experiment import alignment_screen
    blank=np.zeros((256,256,3),dtype=np.uint8)
    assert not alignment_screen(blank,blank)['manual_review_flag']
