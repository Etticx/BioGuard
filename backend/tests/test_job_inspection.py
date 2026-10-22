import json
import pytest
from test_three_roles import roles,auth,sighting,assign
from test_api import photo_bytes
from field_clock import field_today

def job(client,sessions):
 report=sighting(client,sessions,key='inspection_job')
 report=assign(client,sessions,report,work_type='restoration',confirmed_species='Mimosa pudica',confirmed_invasive=True,removal_instructions='Approved removal',replacement_species='Approved replacement',replanting_instructions='Approved planting',inspection_brief='Management-edited inspection wording.')
 return report,report['work_items'][-1]

def test_approved_inspection_snapshot_is_delivered_without_inference(roles):
 client,app,sessions=roles;report,work=job(client,sessions)
 assert work['inspection']['brief']=='Management-edited inspection wording.'
 assert work['inspection']['species']=='Mimosa pudica'
 assert work['inspection']['source']['url'].startswith('https://www.business.qld.gov.au/')
 delivered=client.get('/reports/'+report['id'],headers=auth(sessions,'fieldalpha')).json()
 assert delivered['work_items'][-1]['inspection']==work['inspection']

def test_findings_are_idempotent_team_scoped_and_not_removal_approval(roles):
 client,app,sessions=roles;report,work=job(client,sessions)
 accepted=client.post(f"/reports/{report['id']}/work/{work['id']}/progress",headers=auth(sessions,'fieldalpha'),json={'revision':work['revision'],'action':'accept'}).json();work=accepted['work_items'][-1]
 body={'revision':work['revision'],'request_key':'inspection_result_123','outcome':'found','observed_on':str(field_today()),'notes':'Additional suspected plants found.','findings':[{'latitude':3.180661,'longitude':101.509091,'notes':'Near original plant'}]}
 path=f"/reports/{report['id']}/work/{work['id']}/inspection"
 def send(who,details=body):return client.post(path,headers=auth(sessions,who),data={'details':json.dumps(details)},files={'photo_0':('synthetic.jpg',photo_bytes(format='JPEG'),'image/jpeg')})
 assert send('reporter').status_code==403
 assert send('fieldbeta').status_code==404
 first=send('fieldalpha');assert first.status_code==200,first.text
 updated=first.json();saved=updated['work_items'][-1]
 assert saved['status']=='accepted' and len(updated['work_items'])==1
 assert saved['inspections'][0]['review_status']=='pending'
 assert saved['inspections'][0]['findings'][0]['photo_id']
 assert len(send('fieldalpha').json()['work_items'][-1]['inspections'])==1
 assert send('fieldalpha',{**body,'notes':'Different retry'}).status_code==409
 review=client.post(path+'/review',headers=auth(sessions,'manager'),json={'revision':saved['revision'],'inspection_id':saved['inspections'][0]['id'],'notes':'Reviewed; additional plants need a separate management decision.'})
 assert review.status_code==200 and review.json()['work_items'][-1]['inspections'][0]['review_status']=='reviewed'
 assert len(review.json()['work_items'])==1

def test_none_and_unable_need_no_findings_but_found_requires_pin_and_photo(roles):
 client,app,sessions=roles;report,work=job(client,sessions)
 accepted=client.post(f"/reports/{report['id']}/work/{work['id']}/progress",headers=auth(sessions,'fieldalpha'),json={'revision':work['revision'],'action':'accept'}).json();work=accepted['work_items'][-1]
 path=f"/reports/{report['id']}/work/{work['id']}/inspection"
 base={'revision':work['revision'],'request_key':'inspection_none_123','outcome':'found','observed_on':str(field_today()),'notes':'Checked the assigned vegetation.','findings':[]}
 assert client.post(path,headers=auth(sessions,'fieldalpha'),data={'details':json.dumps(base)}).status_code==422
 response=client.post(path,headers=auth(sessions,'fieldalpha'),data={'details':json.dumps({**base,'outcome':'none'})})
 assert response.status_code==200,response.text
 assert response.json()['work_items'][-1]['inspections'][0]['outcome']=='none'
