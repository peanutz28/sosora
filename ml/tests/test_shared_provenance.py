import json
from ml.vision.provenance import checkpoint_identity, model_metadata, FLOOD_TASK, DEFAULT_MODEL


def test_legacy_flood_checkpoint_still_requires_roi(tmp_path):
    (tmp_path/'config.json').write_text(json.dumps({'id2label': {'0':'background','1':'flooded_road'}}))
    (tmp_path/'model.safetensors').write_bytes(b'fake weights')
    info=model_metadata(str(tmp_path))
    assert info['requires_road_roi'] is True
    assert info['task']==FLOOD_TASK
    assert info['label_map']['0']=='background'
    assert info['run_id'] is None
    assert info['identity_status']=='legacy_unverified'


def test_checkpoint_and_preprocessing_tamper_invalidates_identity(tmp_path):
    (tmp_path/'config.json').write_text(json.dumps({'id2label': {'0':'non_flooded_road','1':'flooded_road'}}))
    (tmp_path/'model.safetensors').write_bytes(b'fake weights')
    (tmp_path/'preprocessor_config.json').write_text('{}')
    identity=checkpoint_identity(tmp_path)
    (tmp_path/'run_metadata.json').write_text(json.dumps({'model_id':str(tmp_path),'checkpoint_id':identity,'run_id':'run-1','task':FLOOD_TASK,'requires_road_roi':True}))
    assert model_metadata(str(tmp_path))['identity_status']=='verified'
    (tmp_path/'preprocessor_config.json').write_text('{"size":256}')
    info=model_metadata(str(tmp_path))
    assert info['identity_status']=='legacy_unverified'
    assert info['checkpoint_id']!=identity
    assert info['requires_road_roi'] is True


def test_unpinned_and_unknown_models_are_not_verified():
    assert model_metadata(DEFAULT_MODEL,revision='main')['identity_status']!='verified'
    assert model_metadata('other/model')['requires_road_roi'] is True
