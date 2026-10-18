from scripts.ml.run_v3_final import choose_proof_tiles


def row(ident,before,after,fp0=0,fp1=0,region='Louisiana'):
    return {'source_image_id':ident,'dataset':region,'metrics':{
        'v2':{'f1':before,'fp':fp0,'fn':2,'valid_pixels':100},
        'v3':{'f1':after,'fp':fp1,'fn':1,'valid_pixels':100}}}


def test_proof_includes_worst_failure_and_other_region():
    chosen,metadata=choose_proof_tiles([row('a',.8,.2),row('b',.1,.9),row('c',.5,.6,region='Germany')])
    assert [item['source_image_id'] for item in chosen]==['a','b','c']
    assert metadata['regression_found'] and metadata['regression_criterion']=='lower F1'


def test_undefined_f1_can_still_show_real_false_positive_regression():
    chosen,metadata=choose_proof_tiles([row('a',None,0,0,3),row('b',.1,.9),row('c',.5,.6)])
    assert chosen[0]['source_image_id']=='a'
    assert metadata['regression_criterion']=='more false positives'


def test_no_fake_failure_when_v3_dominates():
    chosen,metadata=choose_proof_tiles([row('a',.1,.5),row('b',.2,.8),row('c',.5,.7)])
    assert not metadata['regression_found'] and len({item['source_image_id'] for item in chosen})==3
