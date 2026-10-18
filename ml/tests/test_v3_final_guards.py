from datetime import datetime,timedelta,timezone
import json
import subprocess
import pytest
from ml.experiments import v3_protocol as protocol


def git(root,*args):
    return subprocess.run(['git',*args],cwd=root,capture_output=True,text=True,check=True)


@pytest.fixture
def committed(tmp_path,monkeypatch):
    git(tmp_path,'init');git(tmp_path,'checkout','-b','integration')
    monkeypatch.setattr(protocol,'FINAL_DEADLINE',datetime.now(timezone.utc)+timedelta(days=1))
    monkeypatch.setattr(protocol,'SELECTION_DEADLINE',datetime.now(timezone.utc)+timedelta(days=1))
    monkeypatch.setattr('ml.vision.provenance.checkpoint_identity',lambda path:'frozen-v2')
    checkpoint=tmp_path/'winner.pt';checkpoint.write_bytes(b'local-test-checkpoint')
    metrics={'epoch':2,'complete':True,'tp':3,'fp':1,'fn':2,'tn':8,'f1':6/9}
    run={'selected_epoch':2,'checkpoint_sha256':protocol.sha256(checkpoint),
         'settings':{'architecture':'segformer','learning_rate':0.00005},'history':[metrics]}
    run_path=tmp_path/'run.json';run_path.write_text(json.dumps(run))
    for name in protocol.FROZEN_SOURCES:
        source=tmp_path/name;source.parent.mkdir(parents=True,exist_ok=True);source.write_text('# unit test source\n')
    selection={'manifest_sha256':protocol.MANIFEST_SHA256,'protocol_sha256':protocol.PROTOCOL_SHA256,
        'final_ids_sha256':protocol.FINAL_IDS_SHA256,'checkpoint':'winner.pt','checkpoint_sha256':protocol.sha256(checkpoint),
        'decision':'binary argmax, fixed threshold 0.5','tile_size':256,'stride':256,
        'architecture':'segformer','learning_rate':0.00005,'selected_epoch':2,'dev_metrics':metrics,
        'winner_run_json':'run.json','winner_run_json_sha256':protocol.sha256(run_path),'v2_checkpoint_id':'frozen-v2',
        'initialization_checkpoint_id':'frozen-v2','frozen_source_sha256':{name:protocol.sha256(tmp_path/name) for name in protocol.FROZEN_SOURCES}}
    path=tmp_path/'selection.json';path.write_text(json.dumps(selection))
    git(tmp_path,'add','selection.json','run.json',*protocol.FROZEN_SOURCES)
    git(tmp_path,'-c','user.name=V3 test','-c','user.email=test@example.invalid','commit','-m','Freeze test selection')
    return tmp_path,path


def test_committed_selection_required_before_final_data(tmp_path):
    from scripts.ml import run_v3_final
    marker=tmp_path/'must-not-exist'
    def blocked(path):raise ValueError('not committed')
    from unittest.mock import patch
    with patch.object(run_v3_final,'committed_selection',blocked),patch.object(run_v3_final,'DATA',marker):
        with pytest.raises(ValueError,match='not committed'):run_v3_final.prepare()
    assert not marker.exists()


def test_committed_selection_and_dev_provenance_verified(committed):
    root,path=committed
    selection,receipt=protocol.committed_selection(path,root)
    assert receipt['selection_commit']==git(root,'rev-parse','HEAD').stdout.strip()
    assert selection['dev_metrics']['f1']==6/9


def test_uncommitted_selection_edit_refused(committed):
    root,path=committed;path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError,match='committed unchanged'):protocol.committed_selection(path,root)


def test_selected_weights_cannot_change(committed):
    root,path=committed;(root/'winner.pt').write_bytes(b'changed')
    with pytest.raises(ValueError,match='checkpoint changed'):protocol.committed_selection(path,root)


def test_development_evidence_cannot_change(committed):
    root,path=committed;(root/'run.json').write_text('{}')
    with pytest.raises(ValueError,match='Development evidence changed'):protocol.committed_selection(path,root)


def test_final_method_cannot_change_after_selection(committed):
    root,path=committed;(root/'ml/vision/evaluate.py').write_text('# changed scoring\n')
    with pytest.raises(ValueError,match='Frozen evaluation method changed'):protocol.committed_selection(path,root)


def test_completed_final_stage_refuses_rerun(tmp_path):
    path=tmp_path/'ledger.json';state=protocol.begin_attempt(path,{'command':'fixed'})
    protocol.finish_attempt(path,state)
    with pytest.raises(ValueError,match='no second evaluation'):protocol.begin_attempt(path,{'command':'fixed'})


def test_only_logged_identical_failure_can_retry(tmp_path):
    path=tmp_path/'ledger.json';state=protocol.begin_attempt(path,{'command':'fixed'})
    protocol.finish_attempt(path,state,RuntimeError('crash recorded'))
    with pytest.raises(ValueError,match='changed final command'):protocol.begin_attempt(path,{'command':'changed'})
    retry=protocol.begin_attempt(path,{'command':'fixed'})
    assert retry['attempt']==2 and retry['previous_failure']['failure']['message']=='crash recorded'


def test_final_membership_and_order_fixed_before_opening():
    ids=[str(index) for index in range(38)]
    rows=[{'source_image_id':ident,'split':'test'} for ident in ids]
    protocol.validate_final_rows(rows,ids)
    with pytest.raises(ValueError,match='frozen order'):protocol.validate_final_rows(rows[::-1],ids)
    rows[0]['crop_pixel_bounds']=[0,0,256,256]
    with pytest.raises(ValueError,match='complete original'):protocol.validate_final_rows(rows,ids)
