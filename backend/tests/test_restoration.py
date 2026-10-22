"""Single restoration-job workflow; synthetic accounts, photos and SQLite only."""
import json
from datetime import timedelta
import pytest
from field_clock import field_today
from test_api import photo_bytes
from test_reporting import setup, submit, assignment
from test_workflow import review, accept, verify


def assigned(setup):
    client,ground,management,_,team,_,ecology,_=setup
    return accept(client,ecology,review(client,management,submit(client,ground).json(),team,work_type='restoration'))


def evidence(setup,report,stage='both',key='restoration_evidence',two=True,**changes):
    client,_,_,_,_,_,ecology,_=setup
    work=report['work_items'][-1];today=str(field_today())
    details={'revision':work['revision'],'request_key':key,'stage':stage,'observed_on':today,
             'notes':'Synthetic restoration evidence','removal_complete':stage in {'both','removal'},
             'removed_on':today if stage in {'both','removal'} else None,
             'planted_on':today if stage in {'both','replanting'} else None,
             'planted_species':work['replacement_species'] if stage in {'both','replanting'} else '',
             'quantity':3 if stage in {'both','replanting'} else None,
             'planting_pending_reason':'Synthetic access delay' if stage=='removal' else '',**changes}
    files={'photo':('synthetic-removal.jpg',photo_bytes(format='JPEG'),'image/jpeg')}
    if stage=='both' and two:files['overview']=('synthetic-planting.jpg',photo_bytes(format='JPEG',color='blue'),'image/jpeg')
    return client.post(f"/reports/{report['id']}/work/{work['id']}/complete",headers=ecology,
                       data={'details':json.dumps(details)},files=files)


@pytest.mark.parametrize('change',[{'confirmed_invasive':False},{'confirmed_species':'Unknown'},
    {'removal_instructions':''},{'replacement_species':''},{'replanting_instructions':''}])
def test_restoration_requires_both_management_approved_plans(setup,change):
    client,ground,management,_,team,*_=setup
    report=submit(client,ground).json()
    response=client.post(f"/reports/{report['id']}/review",headers=management,
        json=assignment(team,report['revision'],work_type='restoration',**change))
    assert response.status_code==422
    assert client.get(f"/reports/{report['id']}",headers=management).json()['work_items']==[]


def test_both_tasks_share_one_job_then_management_schedules_followup(setup):
    client,_,management,*_=setup
    report=assigned(setup);job=report['work_items'][0]['id']
    assert evidence(setup,report,two=False).status_code==422
    assert evidence(setup,report,removal_complete=False).status_code==422
    response=evidence(setup,report);assert response.status_code==200,response.text
    ready=response.json();assert ready['status']=='awaiting_verification'
    assert len(ready['work_items'])==1 and ready['work_items'][0]['id']==job
    assert len(ready['work_items'][0]['completions'][0]['photo_ids'])==2
    retry=evidence(setup,report);assert retry.status_code==200 and len(retry.json()['photos'])==3
    assert evidence(setup,report,notes='Different content').status_code==409
    closed=verify(client,management,ready);assert closed.status_code==200,closed.text
    assert closed.json()['status']=='follow_up' and len(closed.json()['work_items'])==2
    assert closed.json()['work_items'][-1]['followup_of']==job


def test_pending_planting_stays_active_until_the_same_job_is_finished(setup):
    client,_,management,*_=setup
    report=assigned(setup);job=report['work_items'][0]['id']
    assert evidence(setup,report,stage='replanting').status_code==422
    assert evidence(setup,report,stage='removal',planting_pending_reason='').status_code==422
    partial=evidence(setup,report,stage='removal').json()
    assert partial['status']=='in_progress' and partial['work_items'][0]['status']=='in_progress'
    assert verify(client,management,partial).status_code==409
    assert len(partial['work_items'])==1 and partial['work_items'][0]['id']==job
    assert evidence(setup,partial,stage='replanting',key='wrong_replacement',planted_species='Unapproved plant').status_code==422
    assert evidence(setup,partial,stage='replanting',key='wrong_date',planted_on=str(field_today()-timedelta(days=1))).status_code==422
    final=evidence(setup,partial,stage='replanting',key='finish_same_restoration')
    assert final.status_code==200,final.text
    ready=final.json();assert ready['status']=='awaiting_verification'
    assert len(ready['work_items'])==1 and len(ready['work_items'][0]['completions'])==2
    assert verify(client,management,ready).json()['status']=='follow_up'


def test_corrections_preserve_both_photos_and_the_same_assignment(setup):
    client,_,management,*_=setup
    ready=evidence(setup,assigned(setup)).json()
    corrected=verify(client,management,ready,decision='corrections').json()
    assert corrected['work_items'][0]['status']=='correction_requested'
    ready=evidence(setup,corrected,key='corrected_restoration')
    assert ready.status_code==200,ready.text
    assert len(ready.json()['work_items'])==1 and len(ready.json()['photos'])==5
    assert verify(client,management,ready.json()).json()['status']=='follow_up'


def test_partial_evidence_cannot_be_accepted_even_if_stored_status_is_incorrect(setup):
    client,_,management,_,_,api,*_=setup
    partial=evidence(setup,assigned(setup),stage='removal').json()
    work=partial['work_items'][0]
    with api.state.records.connect() as db:
        db.execute("UPDATE work_items SET status='awaiting_verification' WHERE id=?",(work['id'],))
    assert verify(client,management,partial).status_code==422


def test_queued_evidence_from_before_restoration_keeps_its_original_fingerprint(setup):
    from hashlib import sha256
    from test_workflow import evidence as older_evidence
    client,ground,management,_,team,api,ecology,_=setup
    report=accept(client,ecology,review(client,management,submit(client,ground).json(),team))
    submitted=older_evidence(client,ecology,report);assert submitted.status_code==200
    work=submitted.json()['work_items'][0]
    with api.state.records.connect() as db:
        data=json.loads(db.execute('SELECT data FROM work_items WHERE id=?',(work['id'],)).fetchone()[0])
        item=data['completions'][0]
        old_values={k:v for k,v in item.items() if k not in {'digest','submitted_at','submitted_by','photo_ids','planting_pending_reason'}}
        item['digest']=sha256(json.dumps(old_values,sort_keys=True).encode()+sha256(photo_bytes(format='JPEG')).digest()).hexdigest()
        db.execute('UPDATE work_items SET data=? WHERE id=?',(json.dumps(data),work['id']))
    retry=older_evidence(client,ecology,report)
    assert retry.status_code==200,retry.text
    assert len(retry.json()['photos'])==2
