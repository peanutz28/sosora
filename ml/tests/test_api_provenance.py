import importlib
import json
import pytest

api = importlib.import_module('ml.inference.app')

@pytest.fixture
def evaluation(tmp_path, monkeypatch):
    monkeypatch.setenv('ML_METRICS_PATH', str(tmp_path))
    (tmp_path / 'final_metrics.json').write_text(json.dumps({'f1': .04, 'provenance': identity()}))
    return tmp_path


def identity(**updates):
    result = dict(model_id='pilot', checkpoint_id='sha256:abc', run_id='run1',
                  task='flood_state_on_road_corridors', identity_status='verified')
    return {**result, **updates}


def test_legacy_metrics_never_apply(evaluation, monkeypatch):
    monkeypatch.setattr(api, 'served_metadata', lambda: identity())
    result = api.metrics()
    assert result['status'] == 'pilot_evaluated'
    assert result['fine_tuned']['f1'] == .04
    assert result['baseline'] is None
    assert result['evaluated_model']['identity_status'] == 'unverified'
    assert result['metrics_apply_to_served_model'] is False


def test_verified_match_and_model_info(evaluation, monkeypatch):
    (evaluation / 'run_metadata.json').write_text(json.dumps(identity()))
    monkeypatch.setattr(api, 'checkpoint_identity', lambda path: 'sha256:abc')
    monkeypatch.setattr(api, 'served_metadata', lambda: identity())
    assert api.metrics()['metrics_apply_to_served_model'] is True
    info = api.model_info()
    assert info['metrics_status'] == api.metrics()['status']
    assert info['metadata_scope'] == 'configured_model_not_loaded'
    assert info['status'] == 'configured'


@pytest.mark.parametrize('field,value', [('checkpoint_id','sha256:other'), ('model_id','other'),
    ('run_id','other'), ('task','other'), ('identity_status','legacy_unverified')])
def test_mismatched_identity_never_applies(evaluation, monkeypatch, field, value):
    (evaluation / 'run_metadata.json').write_text(json.dumps(identity()))
    monkeypatch.setattr(api, 'checkpoint_identity', lambda path: 'sha256:abc')
    monkeypatch.setattr(api, 'served_metadata', lambda: identity(**{field:value}))
    assert api.metrics()['metrics_apply_to_served_model'] is False


def test_changed_evaluated_weights_are_unverified(evaluation, monkeypatch):
    (evaluation / 'run_metadata.json').write_text(json.dumps(identity()))
    monkeypatch.setattr(api, 'checkpoint_identity', lambda path: 'sha256:changed')
    monkeypatch.setattr(api, 'served_metadata', lambda: identity())
    result = api.metrics()
    assert result['evaluated_model']['identity_status'] == 'unverified'
    assert result['metrics_apply_to_served_model'] is False


def test_metadata_delegates_configuration_without_loading(monkeypatch):
    monkeypatch.setenv('VISION_MODEL', 'configured-id')
    monkeypatch.setenv('VISION_REVISION', 'revision')
    calls = []
    monkeypatch.setattr(api, 'model_metadata', lambda *args: calls.append(args) or identity())
    api.served_metadata()
    assert calls == [('configured-id', 'revision')]


@pytest.mark.parametrize('provenance', [None, {'model_id': 'different'}])
def test_missing_or_mismatched_metric_provenance(evaluation, monkeypatch, provenance):
    (evaluation / 'run_metadata.json').write_text(json.dumps(identity()))
    (evaluation / 'final_metrics.json').write_text(json.dumps({'f1': .04, 'provenance': provenance}))
    monkeypatch.setattr(api, 'checkpoint_identity', lambda path: 'sha256:abc')
    monkeypatch.setattr(api, 'served_metadata', lambda: identity())
    assert api.metrics()['metrics_apply_to_served_model'] is False


def test_loaded_identity_survives_environment_change(monkeypatch):
    from types import SimpleNamespace
    from functools import lru_cache
    calls = []
    @lru_cache(maxsize=1)
    def loader():
        calls.append(True)
        return ('pilot', SimpleNamespace(_sosora_provenance=identity()), None)
    loader()
    monkeypatch.setitem(api.sys.modules, 'ml.vision.predict', SimpleNamespace(load_model=loader))
    monkeypatch.setenv('VISION_MODEL', 'different-model')
    monkeypatch.setattr(api, 'model_metadata', lambda *args: pytest.fail('must use loaded model identity'))
    assert api.served_metadata()['model_id'] == 'pilot'
    assert api.served_metadata()['metadata_scope'] == 'loaded_model'
    assert len(calls) == 1


def test_uncached_loader_is_never_called(monkeypatch):
    from types import SimpleNamespace
    class Loader:
        def cache_info(self):
            return SimpleNamespace(currsize=0)
        def __call__(self):
            pytest.fail('must not load model')
    monkeypatch.setitem(api.sys.modules, 'ml.vision.predict', SimpleNamespace(load_model=Loader()))
    monkeypatch.setattr(api, 'model_metadata', lambda *args: identity())
    assert api.served_metadata()['metadata_scope'] == 'configured_model_not_loaded'



def test_skip_test_run_is_not_reported_as_evaluated(evaluation, monkeypatch):
    (evaluation / 'run_metadata.json').write_text(json.dumps(identity()))
    (evaluation / 'baseline_metrics.json').write_text(json.dumps({'split':'validation', 'metrics':{'f1':.1}}))
    (evaluation / 'final_metrics.json').write_text(json.dumps({'status':'not_evaluated',
        'reason':'Held-out test intentionally skipped', 'provenance':identity()}))
    monkeypatch.setattr(api, 'checkpoint_identity', lambda path: 'sha256:abc')
    monkeypatch.setattr(api, 'served_metadata', lambda: identity())
    result = api.metrics()
    assert result['status'] == 'not_evaluated'
    assert result['fine_tuned'] is None
    assert result['baseline']['split'] == 'validation'
    assert result['metrics_apply_to_served_model'] is False
    assert result['reason'] == 'Held-out test intentionally skipped'
    assert api.model_info()['metrics_status'] == 'not_evaluated'
