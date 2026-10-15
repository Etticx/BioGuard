import json
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app import create_app
from test_api import Predictor, photo_bytes


@pytest.fixture
def setup(tmp_path):
    api = create_app(Predictor, data_dir=tmp_path, seed_accounts=False)
    with TestClient(api) as client:
        records = api.state.records
        team = records.add_user("grounds", "ground-test-password", "Ground team", "ground")
        other = records.add_user("other", "other-test-password", "Other team", "ground")
        records.add_user("ecology", "officer-test-password", "Ecology officer", "officer")
        def login(username, password):
            response = client.post("/auth/login", json={"username":username,"password":password})
            assert response.status_code == 200
            return {"Authorization":"Bearer " + response.json()["token"]}
        ground = login("grounds", "ground-test-password")
        officer = login("ecology", "officer-test-password")
        outsider = login("other", "other-test-password")
        client.cookies.clear()
        yield client, ground, officer, outsider, team, api


def details(**changes):
    return {"site":"Block B", "landmark":"Beside playground drain", "extent":"patch",
            "observed_on":date.today().isoformat(),"notes":"A test sighting", "request_key":"submission_test_123", **changes}


def submit(client, ground, **changes):
    return client.post("/reports", headers=ground, data={"details":json.dumps(details(**changes))},
                       files={"photo":("plant.jpg",photo_bytes(format="JPEG"),"image/jpeg")})


def assignment(team, revision=1, **changes):
    return {"revision":revision,"decision":"assign","due_on":date.today().isoformat(),"confirmed_species":"Leucaena leucocephala",
            "confirmed_invasive":True,"notes":"Verified by ecology officer", "assigned_team_id":team,
            "removal_instructions":"Approved site-specific removal instructions",
            "replacement_species":"Officer-selected replacement",
            "replanting_instructions":"Approved site-specific replanting instructions", **changes}


def test_identification_does_not_persist_a_report(setup):
    client, ground, officer, _, _, _ = setup
    assert client.post('/identify',content=photo_bytes(),headers={'Content-Type':'image/png'}).status_code==200
    assert client.get('/reports',headers=officer).json()==[]


def test_submit_persists_evidence_and_model_provenance(setup):
    client,ground,officer,_,_,api=setup
    response=submit(client,ground)
    assert response.status_code==201,response.text
    report=response.json()
    assert report['status']=='submitted' and report['review'] is None
    assert report['prediction']['predicted_species']=='Mimosa pudica'
    assert report['model']['architecture']=='EfficientNetV2B0'
    assert report['reporter_name']=='Ground team'
    assert client.get('/reports',headers=officer).json()[0]['id']==report['id']
    photo=client.get(report['photos'][0]['url'],headers=officer)
    assert photo.content==photo_bytes(format='JPEG')
    assert photo.headers['content-type']=='image/jpeg'
    assert 'no-store' in photo.headers['cache-control']
    # The report survives a new store connection, not just application memory.
    from records import Records
    reopened=Records(api.state.records.directory)
    user=api.state.records.session_user(ground['Authorization'][7:])
    assert reopened.get_report(report['id'],user)['site']=='Block B'


def test_roles_and_photo_access_are_enforced(setup):
    client,ground,officer,outsider,team,_=setup
    assert submit(client,{}).status_code==401
    assert submit(client,officer).status_code==403
    report=submit(client,ground).json()
    assert client.get('/reports').status_code==401
    assert client.get('/reports',headers=outsider).json()==[]
    assert client.get('/reports/'+report['id'],headers=outsider).status_code==404
    assert client.get(report['photos'][0]['url'],headers=outsider).status_code==404
    assert client.get(report['photos'][0]['url']).status_code==401
    assert client.post('/reports/'+report['id']+'/review',headers=ground,json=assignment(team)).status_code==403
    assert client.get('/teams',headers=ground).status_code==403


def test_submission_retry_is_idempotent_and_changed_payload_conflicts(setup):
    client,ground,*_=setup
    first=submit(client,ground).json()
    assert submit(client,ground).json()['id']==first['id']
    assert len(client.get('/reports',headers=ground).json())==1
    assert submit(client,ground,notes='Changed').status_code==409


@pytest.mark.parametrize('change',[{'site':' '},{'landmark':''},{'extent':'huge'},
    {'observed_on':(date.today()+timedelta(days=1)).isoformat()},
    {'prediction':{'sdp_listed_invasive':False}}, {'notes':'x'*1201}])
def test_invalid_or_forged_details_are_rejected(setup,change):
    client,ground,*_=setup
    assert submit(client,ground,**change).status_code==422
    assert client.get('/reports',headers=ground).json()==[]


@pytest.mark.parametrize('change',[{'confirmed_species':'Unknown'},{'confirmed_invasive':False},
    {'replacement_species':''},{'removal_instructions':''},{'replanting_instructions':''},{'assigned_team_id':None}])
def test_approval_needs_officer_confirmation_and_complete_work_plan(setup,change):
    client,ground,officer,_,team,_=setup
    report=submit(client,ground).json()
    assert client.post('/reports/'+report['id']+'/review',headers=officer,json=assignment(team,**change)).status_code==422
    assert client.get('/reports/'+report['id'],headers=officer).json()['status']=='submitted'


def test_assignment_preserves_model_suggestion_and_reaches_team(setup):
    client,ground,officer,_,team,_=setup
    report=submit(client,ground).json()
    response=client.post('/reports/'+report['id']+'/review',headers=officer,json=assignment(team))
    assert response.status_code==200,response.text
    approved=response.json()
    assert approved['status']=='assigned' and approved['revision']==2
    assert approved['prediction']['predicted_species']=='Mimosa pudica'
    assert approved['review']['confirmed_species']=='Leucaena leucocephala'
    assert approved['review']['replacement_species']=='Officer-selected replacement'
    assert client.get('/reports',headers=ground).json()[0]['assigned_team_id']==team
    assert client.post('/reports/'+report['id']+'/review',headers=officer,json=assignment(team)).status_code==409


def test_request_information_reply_and_close(setup):
    client,ground,officer,outsider,_,_=setup
    report=submit(client,ground).json()
    review={'revision':1,'decision':'request_info','notes':'Please add a closer leaf photo.'}
    response=client.post('/reports/'+report['id']+'/review',headers=officer,json=review)
    assert response.status_code==200,response.text
    assert response.json()['status']=='needs_info'
    def reply(headers,revision):
        return client.post('/reports/'+report['id']+'/information',headers=headers,
            data={'revision':str(revision),'notes':'Closer photo attached'},
            files={'photo':('extra.jpg',photo_bytes(format='JPEG'),'image/jpeg')})
    assert reply(outsider,2).status_code==404
    assert reply(ground,1).status_code==409
    result=reply(ground,2)
    assert result.status_code==200,result.text
    assert result.json()['status']=='submitted' and len(result.json()['photos'])==2
    assert result.json()['prediction']==report['prediction']
    closed=client.post('/reports/'+report['id']+'/review',headers=officer,
                       json={'revision':3,'decision':'no_action','confirmed_species':'Unknown','notes':'No approved removal needed.'})
    assert closed.status_code==200 and closed.json()['status']=='closed'


def test_bad_photo_does_not_save_any_report(setup):
    client,ground,*_=setup
    response=client.post('/reports',headers=ground,data={'details':json.dumps(details())},
                        files={'photo':('bad.jpg',b'not an image','image/jpeg')})
    assert response.status_code==422
    assert client.get('/reports',headers=ground).json()==[]


def test_logout_and_expired_sessions_are_revoked(setup):
    client,ground,officer,_,_,api=setup
    assert client.post('/auth/logout',headers=ground).status_code==204
    assert client.get('/reports',headers=ground).status_code==401
    with api.state.records.connect() as db:
        db.execute('UPDATE sessions SET expires_at=0')
    assert client.get('/reports',headers=officer).status_code==401
