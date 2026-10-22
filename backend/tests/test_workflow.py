import json
import pytest
from datetime import date,timedelta
from fastapi.testclient import TestClient
from app import create_app
from records import Records
from field_clock import field_today
from test_api import Predictor,photo_bytes
from test_reporting import setup,submit,assignment,details


def review(client,management,report,team,**change):
 response=client.post(f"/reports/{report['id']}/review",headers=management,json=assignment(team,report['revision'],**change));assert response.status_code==200,response.text;return response.json()
def accept(client,ecology,report):
 work=report['work_items'][-1]
 response=client.post(f"/reports/{report['id']}/work/{work['id']}/progress",headers=ecology,json={'revision':work['revision'],'action':'accept'})
 assert response.status_code==200,response.text
 return response.json()
def evidence(client,ecology,report,**change):
 work=report['work_items'][-1];stage={'inspection':'observation','removal':'removal','replanting':'replanting'}.get(work['work_type'],'observation')
 values={'revision':work['revision'],'request_key':'evidence_test_123','stage':stage,'observed_on':str(field_today()),'notes':'DEMO evidence','removal_complete':stage=='removal','removed_on':str(field_today()) if stage=='removal' else None,'planted_on':str(field_today()) if stage=='replanting' else None,'planted_species':'Management-selected replacement' if stage=='replanting' else '', 'quantity':2 if stage=='replanting' else None,'suggested_species':'Unknown','recommended_action':'none',**change}
 return client.post(f"/reports/{report['id']}/work/{work['id']}/complete",headers=ecology,data={'details':json.dumps(values)},files={'photo':('evidence.jpg',photo_bytes(format='JPEG'),'image/jpeg')})
def verify(client,management,report,**change):
 work=report['work_items'][-1]
 return client.post(f"/reports/{report['id']}/work/{work['id']}/verify",headers=management,json={'revision':work['revision'],'decision':'accept','notes':'DEMO reviewed',**change})
def test_explicit_removal_then_approved_planting_and_closure(setup):
 client,ground,management,_,team,_,ecology,other_ecology=setup
 r=accept(client,ecology,review(client,management,submit(client,ground).json(),team))
 response=evidence(client,ecology,r);assert response.status_code==200,response.text;r=response.json()
 assert r['status']=='awaiting_verification'
 next_plan=assignment(team,r['revision'],work_type='replanting')
 assert verify(client,management,r,next_plan={**next_plan,'replacement_species':''}).status_code==422
 response=verify(client,management,r,next_plan=next_plan);assert response.status_code==200,response.text;r=response.json()
 assert r['work_items'][-1]['work_type']=='replanting' and r['status']=='assigned'
 r=accept(client,ecology,r)
 r=evidence(client,ecology,r,request_key='planting_test_123').json()
 response=verify(client,management,r);assert response.status_code==200,response.text;r=response.json()
 assert r['status']=='follow_up' and len(r['work_items'])==3
 assert r['work_items'][-1]['followup_of']==r['work_items'][-2]['id']
 assert len(r['photos'])==3 and all(w['status']=='verified' for w in r['work_items'][:-1]) and r['work_items'][-1]['status']=='assigned'
 assert len(r['history'])>=6


def test_completion_is_idempotent_and_management_only_verification(setup):
 client,ground,management,outsider,team,_,ecology,other_ecology=setup
 assigned=accept(client,ecology,review(client,management,submit(client,ground).json(),team))
 assert evidence(client,other_ecology,assigned).status_code==404
 assert evidence(client,ground,assigned).status_code==403
 assert evidence(client,management,assigned).status_code==403
 response=evidence(client,ecology,assigned);r=response.json();assert response.status_code==200,response.text
 assert evidence(client,ecology,assigned).json()['id']==r['id']
 assert len(evidence(client,ecology,assigned).json()['photos'])==2
 assert evidence(client,ecology,assigned,notes='Changed evidence').status_code==409
 assert verify(client,ecology,r).status_code==403
 assert verify(client,management,assigned).status_code==409
 assert verify(client,management,r).json()['status']=='completed'


def test_corrections_preserve_previous_evidence(setup):
 client,ground,management,_,team,_,ecology,other_ecology=setup
 r=accept(client,ecology,review(client,management,submit(client,ground).json(),team));r=evidence(client,ecology,r).json()
 r=verify(client,management,r,decision='corrections',notes='Add clearer photo.').json();assert r['work_items'][-1]['status']=='correction_requested'
 r=evidence(client,ecology,r,request_key='corrected_test_123').json();assert len(r['work_items'][-1]['completions'])==2
 assert len(r['photos'])==3


def test_historical_followup_with_regrowth_is_retained_readonly(setup):
 client,ground,management,_,team,api,ecology,other_ecology=setup
 r=review(client,management,submit(client,ground).json(),team,work_type='inspection',confirmed_species='Unknown',confirmed_invasive=None,removal_instructions='',replacement_species='',replanting_instructions='')
 work=r['work_items'][0]
 with api.state.records.connect() as db:
  data=json.loads(db.execute('SELECT data FROM work_items WHERE id=?',(work['id'],)).fetchone()[0]);data['work_type']='follow_up';data['completions']=[{'stage':'observation','regrowth':'yes','notes':'Historical evidence of regrowth','photo_ids':[]}]
  db.execute("UPDATE work_items SET status='awaiting_verification',data=? WHERE id=?",(json.dumps(data),work['id']))
 r=client.get(f"/reports/{r['id']}",headers=management).json()
 assert r['work_items'][0]['completions'][0]['regrowth']=='yes'
 assert verify(client,management,r).status_code==422
 response=client.post(f"/reports/{r['id']}/review",headers=management,json={'revision':r['revision'],'decision':'cancel','notes':'Replace historical work with a new approved plan.'})
 assert response.status_code==200 and response.json()['work_items'][0]['status']=='cancelled'


def test_inspection_for_unknown_species_and_reassignment_privacy(setup):
 client,ground,management,outsider,team,api,ecology,other_ecology=setup
 r=review(client,management,submit(client,ground).json(),team,work_type='inspection',confirmed_species='Unknown',confirmed_invasive=None,removal_instructions='',replacement_species='',replanting_instructions='')
 other=api.state.records.session_user(other_ecology['Authorization'][7:])['team_id'];w=r['work_items'][0]
 plan=assignment(other,w['revision'],work_type='inspection',confirmed_species='Unknown',confirmed_invasive=None,removal_instructions='',replacement_species='',replanting_instructions='')
 response=client.post(f"/reports/{r['id']}/work/{w['id']}/revise",headers=management,json=plan);assert response.status_code==200,response.text
 assert client.get(f"/reports/{r['id']}",headers=other_ecology).status_code==200
 assert evidence(client,ecology,response.json(),stage='observation').status_code==404


def test_problem_and_cancel_prevent_new_evidence(setup):
 client,ground,management,_,team,_,ecology,other_ecology=setup
 r=accept(client,ecology,review(client,management,submit(client,ground).json(),team));w=r['work_items'][0]
 path=f"/reports/{r['id']}/work/{w['id']}/progress"
 assert client.post(path,headers=ecology,json={'revision':w['revision'],'action':'blocked','notes':''}).status_code==422
 r=client.post(path,headers=ecology,json={'revision':w['revision'],'action':'blocked','notes':'Access blocked.'}).json();assert r['status']=='blocked'
 assert any('problem' in n['message'] for n in client.get('/notifications',headers=management).json())
 r=client.post(f"/reports/{r['id']}/review",headers=management,json={'revision':r['revision'],'decision':'cancel','notes':'Unsafe access; cancelled.'}).json();assert r['work_items'][0]['status']=='cancelled'
 assert evidence(client,ecology,r).status_code==409

def test_reports_survive_model_inference_or_startup_failure(setup,tmp_path):
 client,ground,management,_,_,api,ecology,other_ecology=setup
 def fail(*args):raise RuntimeError('Broken model')
 api.state.predictor.predict=fail
 r=submit(client,ground).json();assert r['prediction'] is None and r['model']['status']=='unavailable'
 api=create_app(fail,data_dir=tmp_path/'down',seed_accounts=False)
 with TestClient(api) as down:
  api.state.records.add_user('field','test-password','Field','ground');token=down.post('/auth/login',json={'username':'field','password':'test-password'}).json()['token'];down.cookies.clear()
  assert down.get('/health').json()['identification_available'] is False
  assert down.post('/identify',content=photo_bytes(),headers={'Content-Type':'image/png'}).status_code==503
  assert submit(down,{'Authorization':'Bearer '+token}).status_code==201

def test_skip_model_and_validate_catalog_coordinates(setup):
 client,ground,management,*_=setup
 site=client.post('/admin/catalog/sites',headers=management,json={'name':'Demo estate'}).json()
 block=client.post('/admin/catalog/blocks',headers=management,json={'name':'B','site_id':site['id']}).json()
 r=submit(client,ground,identify_requested=False,site='untrusted label',site_id=site['id'],block_id=block['id'],latitude=3.1,longitude=101.7).json()
 assert r['prediction'] is None and r['site']=='Demo estate' and r['block_name']=='B'
 assert submit(client,ground,request_key='bad_location_123',latitude=91,longitude=0).status_code==422
 assert submit(client,ground,request_key='bad_location_456',block_id=block['id']).status_code==422

def test_duplicate_linking_stale_review_and_no_chains(setup):
 client,ground,management,*_=setup
 a=submit(client,ground).json();b=submit(client,ground,request_key='another_report_123').json()
 r=client.post(f"/reports/{a['id']}/review",headers=management,json={'revision':1,'decision':'duplicate','notes':'Same sighting','duplicate_of':b['id']});assert r.status_code==200,r.text
 assert r.json()['duplicate_of']==b['id']
 assert client.post(f"/reports/{b['id']}/review",headers=management,json={'revision':1,'decision':'duplicate','notes':'Loop','duplicate_of':a['id']}).status_code==422
 c=submit(client,ground,request_key='another_report_456').json()
 assert client.post(f"/reports/{b['id']}/review",headers=management,json={'revision':1,'decision':'duplicate','notes':'Chain','duplicate_of':c['id']}).status_code==422

def test_shared_team_members_and_personal_notice_reads(setup):
 client,ground,management,_,team,api,ecology,other_ecology=setup
 api.state.records.add_user('colleague','staff-password','Colleague','ecology',team)
 token=client.post('/auth/login',json={'username':'colleague','password':'staff-password'}).json()['token'];client.cookies.clear();colleague={'Authorization':'Bearer '+token}
 r=review(client,management,submit(client,ground).json(),team)
 assert client.get(f"/reports/{r['id']}",headers=colleague).status_code==200
 notice=client.get('/notifications',headers=ecology).json()[0]
 assert client.post(f"/notifications/{notice['id']}/read",headers=ecology).status_code==204
 assert client.get('/notifications',headers=colleague).json()[0]['read_at'] is None

def test_forced_password_change_revocation_and_admin_guards(setup):
 client,ground,management,_,team,_,ecology,other_ecology=setup
 assert client.get('/admin/users',headers=ground).status_code==403
 created=client.post('/admin/users',headers=management,json={'username':'newstaff','display_name':'New staff','role':'ground','team_id':client.get('/auth/me',headers=ground).json()['team_id']}).json()
 result=client.post('/auth/login',json={'username':'newstaff','password':created['temporary_password']}).json();client.cookies.clear();headers={'Authorization':'Bearer '+result['token']}
 assert result['user']['must_change_password'] and client.get('/reports',headers=headers).status_code==403
 assert client.post('/auth/password',headers=headers,json={'current_password':created['temporary_password'],'new_password':'new-staff-password'}).status_code==204
 assert client.get('/auth/me',headers=headers).status_code==401
 assert client.post('/auth/login',json={'username':'newstaff','password':'new-staff-password'}).status_code==200;client.cookies.clear()
 users=client.get('/admin/users',headers=management).json();management_id=next(u['id'] for u in users if u['role']=='management')
 assert client.post(f'/admin/users/{management_id}/active',headers=management,json={'active':False}).status_code==422
 reset=client.post(f"/admin/users/{created['id']}/reset",headers=management);assert reset.status_code==200
 assert client.post('/auth/login',json={'username':'newstaff','password':'new-staff-password'}).status_code==401

@pytest.mark.parametrize('new_password', [' field-password', 'field-password ', '\t field-password \t'])
def test_password_changes_preserve_whitespace_and_revoke_sessions(setup,new_password):
 client,ground,*_=setup
 response=client.post('/auth/password',headers=ground,json={'current_password':'ground-test-password','new_password':new_password})
 assert response.status_code==204,response.text
 assert client.get('/auth/me',headers=ground).status_code==401
 assert client.post('/auth/login',json={'username':'grounds','password':new_password.strip()}).status_code==401
 response=client.post('/auth/login',json={'username':'grounds','password':new_password})
 assert response.status_code==200,response.text
 headers={'Authorization':'Bearer '+response.json()['token']};client.cookies.clear()
 response=client.post('/auth/password',headers=headers,json={'current_password':new_password,'new_password':'replacement-password'})
 assert response.status_code==204,response.text
 assert client.get('/auth/me',headers=headers).status_code==401
 assert client.post('/auth/login',json={'username':'grounds','password':'replacement-password'}).status_code==200


def test_backup_contains_evidence_and_restores_to_new_directory(setup,tmp_path):
 client,ground,management,_,_,api,ecology,other_ecology=setup
 r=submit(client,ground).json();assert client.post('/admin/backups',headers=ground).status_code==403
 backup=client.post('/admin/backups',headers=management);assert backup.status_code==201,backup.text
 name=backup.json()['name'];download=client.get('/admin/backups/'+name,headers=management);assert download.status_code==200
 import sqlite3
 restored=tmp_path/'restored.sqlite3';restored.write_bytes(download.content)
 with sqlite3.connect(restored) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert db.execute('SELECT count(*) FROM photos').fetchone()[0]==1
 assert client.get('/admin/backups/../bioguard.sqlite3',headers=management).status_code==404


def test_offline_restore_invalidates_sessions_and_preserves_private_photos(setup,tmp_path):
 client,ground,management,_,_,api,ecology,other_ecology=setup
 r=submit(client,ground).json();created=api.state.records.backup_database()
 from backup_tool import restore
 directory=tmp_path/'recovery';result=restore(api.state.records.directory/'backups'/created['name'],directory)
 assert result['restored']['photos']==1
 restored=Records(directory)
 assert restored.session_user(ground['Authorization'][7:]) is None
 account=restored.login('grounds','ground-test-password')['user']
 assert restored.get_report(r['id'],account)['photos'][0]['id']==r['photos'][0]['id']
 assert restored.get_photo(r['id'],r['photos'][0]['id'],account)[1]==photo_bytes(format='JPEG')

def test_legacy_assignment_migration_is_repeatable(tmp_path):
 from records import BaseRecords
 legacy=BaseRecords(tmp_path);legacy.initialize(False);ground=legacy.add_user('grounds','test-password','Team','ground');old_manager=legacy.add_user('ecology','test-password','Officer','management')
 data={'site':'Demo','landmark':'Drain','prediction':None,'review':{'notes':'Legacy approval'},'history':[]}
 with legacy.connect() as db:
  db.execute("UPDATE users SET role='officer' WHERE id=?",(old_manager,))
  db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?,?,?,?)',('legacy',ground,ground,'assigned',2,'old_key_123','digest','2026-01-01','2026-01-01',json.dumps(data)))
 upgraded=Records(tmp_path);upgraded.initialize(False);upgraded.initialize(False)
 user=upgraded.login('grounds','test-password')['user'];manager=upgraded.login('ecology','test-password')['user'];r=upgraded.get_report('legacy',manager)
 assert manager['role']=='management' and r['assigned_team_id']==user['team_id']
 assert upgraded.get_report('legacy',user)['work_items']==[]
 assert len(r['work_items'])==1 and r['work_items'][0]['history'][0]['action']=='legacy_assignment_imported'

def test_cookie_writes_reject_another_origin(setup):
 client,ground,management,*_=setup
 client.post('/auth/login',json={'username':'management','password':'management-test-password'})
 assert client.post('/admin/backups',headers={'Origin':'http://another.example'}).status_code==403
 assert client.post('/admin/backups',headers={'Origin':'http://testserver'}).status_code==201


def test_calendar_dates_use_malaysia_even_on_a_utc_host():
 from field_clock import field_today
 from datetime import datetime,timezone
 assert field_today(datetime(2026,10,15,16,1,tzinfo=timezone.utc)).isoformat()=='2026-10-16'
 assert field_today(datetime(2026,10,15,15,59,tzinfo=timezone.utc)).isoformat()=='2026-10-15'


def test_startup_preparation_failure_keeps_reporting_online(tmp_path,monkeypatch):
 monkeypatch.setenv('BIOGUARD_MODEL_DISABLED','1')
 with TestClient(create_app(data_dir=tmp_path,seed_accounts=False)) as client:
  assert client.get('/health').json()['identification_available'] is False
  assert client.get('/health').json()['stores_submitted_reports'] is True
