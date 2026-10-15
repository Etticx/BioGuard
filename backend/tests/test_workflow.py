import json
from datetime import date,timedelta
from fastapi.testclient import TestClient
from app import create_app
from records import Records
from test_api import Predictor,photo_bytes
from test_reporting import setup,submit,assignment,details

def review(client,officer,report,team,**change):
 response=client.post(f"/reports/{report['id']}/review",headers=officer,json=assignment(team,report['revision'],**change));assert response.status_code==200,response.text;return response.json()
def evidence(client,ground,report,**change):
 work=report['work_items'][-1]
 values={'revision':work['revision'],'request_key':'evidence_test_123','stage':'both','observed_on':date.today().isoformat(),'notes':'DEMO evidence','removal_complete':True,'removed_on':date.today().isoformat(),'planted_on':date.today().isoformat(),'planted_species':'Officer-selected replacement','quantity':2,**change}
 return client.post(f"/reports/{report['id']}/work/{work['id']}/complete",headers=ground,data={'details':json.dumps(values)},files={'photo':('evidence.jpg',photo_bytes(format='JPEG'),'image/jpeg')})
def verify(client,officer,report,**change):
 work=report['work_items'][-1]
 return client.post(f"/reports/{report['id']}/work/{work['id']}/verify",headers=officer,json={'revision':work['revision'],'decision':'accept','notes':'DEMO reviewed','next_visit_on':(date.today()+timedelta(days=7)).isoformat(),**change})
def test_partial_removal_planting_followup_and_closure(setup):
 client,ground,officer,_,team,_=setup
 r=review(client,officer,submit(client,ground).json(),team)
 response=evidence(client,ground,r,stage='removal',planted_on=None,planted_species='',quantity=None);assert response.status_code==200,response.text;r=response.json()
 assert r['status']=='awaiting_verification'
 assert verify(client,officer,r,next_visit_on=None).status_code==422
 r=verify(client,officer,r).json();assert r['work_items'][-1]['work_type']=='replanting'
 r=evidence(client,ground,r,stage='replanting',removed_on=None,removal_complete=False,request_key='planting_test_123').json()
 r=verify(client,officer,r).json();assert r['status']=='follow_up'
 r=evidence(client,ground,r,stage='observation',removed_on=None,planted_on=None,planted_species='',quantity=None,regrowth='no',checked_count=2,surviving_count=1,request_key='followup_test_123').json()
 r=verify(client,officer,r,next_visit_on=None).json();assert r['status']=='completed'
 assert len(r['photos'])==4 and all(w['status']=='verified' for w in r['work_items'])
 assert len(r['history'])==8

def test_completion_is_idempotent_and_officer_only_verification(setup):
 client,ground,officer,outsider,team,_=setup
 assigned=review(client,officer,submit(client,ground).json(),team)
 assert evidence(client,outsider,assigned).status_code==404
 assert evidence(client,officer,assigned).status_code==403
 response=evidence(client,ground,assigned);r=response.json();assert response.status_code==200,response.text
 assert evidence(client,ground,assigned).json()['id']==r['id']
 assert len(evidence(client,ground,assigned).json()['photos'])==2
 assert evidence(client,ground,assigned,notes='Changed evidence').status_code==409
 assert verify(client,ground,r).status_code==403
 assert verify(client,officer,assigned).status_code==409
 assert verify(client,officer,r,next_visit_on=None).status_code==422
 assert verify(client,officer,r,next_visit_on=None,no_followup_reason='Officer documented site-specific exception.').json()['status']=='completed'

def test_corrections_preserve_previous_evidence(setup):
 client,ground,officer,_,team,_=setup
 r=review(client,officer,submit(client,ground).json(),team);r=evidence(client,ground,r).json()
 r=verify(client,officer,r,decision='corrections',next_visit_on=None,notes='Add clearer photo.').json();assert r['work_items'][-1]['status']=='correction_requested'
 r=evidence(client,ground,r,request_key='corrected_test_123').json();assert len(r['work_items'][-1]['completions'])==2
 assert len(r['photos'])==3

def test_regrowth_cannot_be_silently_closed(setup):
 client,ground,officer,_,team,_=setup
 r=review(client,officer,submit(client,ground).json(),team,work_type='follow_up')
 r=evidence(client,ground,r,stage='observation',removed_on=None,planted_on=None,quantity=None,regrowth='yes').json()
 assert verify(client,officer,r,next_visit_on=None).status_code==422
 r=verify(client,officer,r,decision='reopen',next_visit_on=None).json();assert r['status']=='submitted'

def test_inspection_for_unknown_species_and_reassignment_privacy(setup):
 client,ground,officer,outsider,team,api=setup
 r=review(client,officer,submit(client,ground).json(),team,work_type='inspection',confirmed_species='Unknown',confirmed_invasive=None,removal_instructions='',replacement_species='',replanting_instructions='')
 other=api.state.records.session_user(outsider['Authorization'][7:])['team_id'];w=r['work_items'][0]
 plan=assignment(other,w['revision'],work_type='monitoring',confirmed_species='Unknown',confirmed_invasive=None,removal_instructions='',replacement_species='',replanting_instructions='')
 response=client.post(f"/reports/{r['id']}/work/{w['id']}/revise",headers=officer,json=plan);assert response.status_code==200,response.text
 assert client.get(f"/reports/{r['id']}",headers=outsider).status_code==200
 assert evidence(client,ground,response.json(),stage='observation').status_code==404

def test_problem_and_cancel_prevent_new_evidence(setup):
 client,ground,officer,_,team,_=setup
 r=review(client,officer,submit(client,ground).json(),team);w=r['work_items'][0]
 path=f"/reports/{r['id']}/work/{w['id']}/progress"
 assert client.post(path,headers=ground,json={'revision':w['revision'],'action':'blocked','notes':''}).status_code==422
 r=client.post(path,headers=ground,json={'revision':w['revision'],'action':'blocked','notes':'Access blocked.'}).json();assert r['status']=='blocked'
 assert any('problem' in n['message'] for n in client.get('/notifications',headers=officer).json())
 r=client.post(f"/reports/{r['id']}/review",headers=officer,json={'revision':r['revision'],'decision':'cancel','notes':'Unsafe access; cancelled.'}).json();assert r['work_items'][0]['status']=='cancelled'
 assert evidence(client,ground,r).status_code==409

def test_reports_survive_model_inference_or_startup_failure(setup,tmp_path):
 client,ground,officer,_,_,api=setup
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
 client,ground,officer,*_=setup
 site=client.post('/admin/catalog/sites',headers=officer,json={'name':'Demo estate'}).json()
 block=client.post('/admin/catalog/blocks',headers=officer,json={'name':'B','site_id':site['id']}).json()
 r=submit(client,ground,identify_requested=False,site='untrusted label',site_id=site['id'],block_id=block['id'],latitude=3.1,longitude=101.7).json()
 assert r['prediction'] is None and r['site']=='Demo estate' and r['block_name']=='B'
 assert submit(client,ground,request_key='bad_location_123',latitude=91,longitude=0).status_code==422
 assert submit(client,ground,request_key='bad_location_456',block_id=block['id']).status_code==422

def test_duplicate_linking_stale_review_and_no_chains(setup):
 client,ground,officer,*_=setup
 a=submit(client,ground).json();b=submit(client,ground,request_key='another_report_123').json()
 r=client.post(f"/reports/{a['id']}/review",headers=officer,json={'revision':1,'decision':'duplicate','notes':'Same sighting','duplicate_of':b['id']});assert r.status_code==200,r.text
 assert r.json()['duplicate_of']==b['id']
 assert client.post(f"/reports/{b['id']}/review",headers=officer,json={'revision':1,'decision':'duplicate','notes':'Loop','duplicate_of':a['id']}).status_code==422
 c=submit(client,ground,request_key='another_report_456').json()
 assert client.post(f"/reports/{b['id']}/review",headers=officer,json={'revision':1,'decision':'duplicate','notes':'Chain','duplicate_of':c['id']}).status_code==422

def test_shared_team_members_and_personal_notice_reads(setup):
 client,ground,officer,_,team,api=setup
 api.state.records.add_user('colleague','staff-password','Colleague','ground',team)
 token=client.post('/auth/login',json={'username':'colleague','password':'staff-password'}).json()['token'];client.cookies.clear();colleague={'Authorization':'Bearer '+token}
 r=review(client,officer,submit(client,ground).json(),team)
 assert client.get(f"/reports/{r['id']}",headers=colleague).status_code==200
 notice=client.get('/notifications',headers=ground).json()[0]
 assert client.post(f"/notifications/{notice['id']}/read",headers=ground).status_code==204
 assert client.get('/notifications',headers=colleague).json()[0]['read_at'] is None

def test_forced_password_change_revocation_and_admin_guards(setup):
 client,ground,officer,_,team,_=setup
 assert client.get('/admin/users',headers=ground).status_code==403
 created=client.post('/admin/users',headers=officer,json={'username':'newstaff','display_name':'New staff','role':'ground','team_id':team}).json()
 result=client.post('/auth/login',json={'username':'newstaff','password':created['temporary_password']}).json();client.cookies.clear();headers={'Authorization':'Bearer '+result['token']}
 assert result['user']['must_change_password'] and client.get('/reports',headers=headers).status_code==403
 assert client.post('/auth/password',headers=headers,json={'current_password':created['temporary_password'],'new_password':'new-staff-password'}).status_code==204
 assert client.get('/auth/me',headers=headers).status_code==401
 assert client.post('/auth/login',json={'username':'newstaff','password':'new-staff-password'}).status_code==200;client.cookies.clear()
 users=client.get('/admin/users',headers=officer).json();officer_id=next(u['id'] for u in users if u['role']=='officer')
 assert client.post(f'/admin/users/{officer_id}/active',headers=officer,json={'active':False}).status_code==422
 reset=client.post(f"/admin/users/{created['id']}/reset",headers=officer);assert reset.status_code==200
 assert client.post('/auth/login',json={'username':'newstaff','password':'new-staff-password'}).status_code==401

def test_backup_contains_evidence_and_restores_to_new_directory(setup,tmp_path):
 client,ground,officer,_,_,api=setup
 r=submit(client,ground).json();assert client.post('/admin/backups',headers=ground).status_code==403
 backup=client.post('/admin/backups',headers=officer);assert backup.status_code==201,backup.text
 name=backup.json()['name'];download=client.get('/admin/backups/'+name,headers=officer);assert download.status_code==200
 import sqlite3
 restored=tmp_path/'restored.sqlite3';restored.write_bytes(download.content)
 with sqlite3.connect(restored) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert db.execute('SELECT count(*) FROM photos').fetchone()[0]==1
 assert client.get('/admin/backups/../bioguard.sqlite3',headers=officer).status_code==404


def test_offline_restore_invalidates_sessions_and_preserves_private_photos(setup,tmp_path):
 client,ground,officer,_,_,api=setup
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
 legacy=BaseRecords(tmp_path);legacy.initialize(False);ground=legacy.add_user('grounds','test-password','Team','ground');legacy.add_user('ecology','test-password','Officer','officer')
 data={'site':'Demo','landmark':'Drain','prediction':None,'review':{'notes':'Legacy approval'},'history':[]}
 with legacy.connect() as db:
  db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?,?,?,?)',('legacy',ground,ground,'assigned',2,'old_key_123','digest','2026-01-01','2026-01-01',json.dumps(data)))
 upgraded=Records(tmp_path);upgraded.initialize(False);upgraded.initialize(False)
 user=upgraded.login('grounds','test-password')['user'];r=upgraded.get_report('legacy',user)
 assert r['assigned_team_id']==user['team_id']
 assert len(r['work_items'])==1 and r['work_items'][0]['history'][0]['action']=='legacy_assignment_imported'

def test_cookie_writes_reject_another_origin(setup):
 client,ground,officer,*_=setup
 client.post('/auth/login',json={'username':'ecology','password':'officer-test-password'})
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
