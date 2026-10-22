import json
import pytest
from inspection_guidance import guidance
import restoration_ai as ai
from test_three_roles import roles

def test_seven_rules_have_quotes_sources_and_unknown_actions():
 from inspection_guidance import RULES
 assert len(RULES)==7
 for species,rule in RULES.items():
  result=guidance(species,{})
  assert result['source']['url'].startswith('https://')
  assert result['source']['excerpt'] and result['actions']
  assert result['variables']=={key:'unknown' for key in rule['variables']}
  assert result['location']['kind']=='unmapped'

def test_known_absent_and_unknown_conditions_select_different_actions():
 unknown=guidance('Psidium guajava',{})
 yes=guidance('Psidium guajava',{'inspection_observations':{'previous_cutting':'yes'}})
 no=guidance('Psidium guajava',{'inspection_observations':{'previous_cutting':'no'}})
 assert 'Check for signs' in ' '.join(unknown['actions'])
 assert 'reshooting' in ' '.join(yes['actions'])
 assert yes['actions']!=no['actions']
 assert guidance('Psidium guajava',{'notes':'previous_cutting yes'})['variables']['previous_cutting']=='unknown'

def test_real_point_has_block_and_water_is_not_forced_into_land():
 r=guidance('Mimosa pudica',{'location_mode':'osm','map_id':'elmina-lakeside-v1','latitude':3.180661,'longitude':101.509091})
 assert r['location']['block_ids']==['B15']
 assert guidance('Mimosa pudica',{'location_mode':'osm','map_id':'elmina-lakeside-v1','latitude':3.1802345,'longitude':101.50984533636469})['location']['kind']=='water'
 assert guidance('Ficus microcarpa',{})['supported'] is False
 assert guidance('Sieruela rutidosperma',{})['supported'] is True

def test_inspection_opens_without_confirmation_uses_one_call_and_caches(roles,monkeypatch):
 from test_three_roles import auth,sighting
 client,app,sessions=roles;report=sighting(client,sessions,key="auto_inspection")
 calls=[]
 def complete(body):
  calls.append(body)
  return {"content":json.dumps({"inspection_brief":"Inspect surrounding vegetation and any vegetated path edges. Record additional plants found."})}
 monkeypatch.setattr(ai,"completion",complete)
 path=f"/reports/{report['id']}/inspection-draft";payload={"revision":report['revision'],"species":"Mimosa pudica"}
 assert client.post(path,json=payload).status_code==401
 assert client.post(path,headers=auth(sessions,'reporter'),json=payload).status_code==403
 first=client.post(path,headers=auth(sessions,'manager'),json=payload)
 assert first.status_code==200,first.text
 assert first.json()['inspection']['source']['excerpt']
 assert len(calls)==1
 assert calls[0]['response_format']['json_schema']['schema']['required']==['inspection_brief']
 second=client.post(path,headers=auth(sessions,'manager'),json=payload)
 assert second.status_code==200 and len(calls)==1
 assert second.json()['request_receipt']['cached'] is True
 assert second.json()['request_receipt']['groq_requests']==0

def test_inspection_error_does_not_retry_groq_and_returns_template(roles,monkeypatch):
 from test_three_roles import auth,sighting
 client,app,sessions=roles;report=sighting(client,sessions,key="inspection_failure")
 calls=[]
 def fail(body):calls.append(body);raise ai.HTTPException(429,"Synthetic quota limit")
 monkeypatch.setattr(ai,'completion',fail);monkeypatch.setattr(ai,'local_model',lambda:'')
 result=client.post(f"/reports/{report['id']}/inspection-draft",headers=auth(sessions,'manager'),json={'revision':report['revision'],'species':'Psidium guajava'})
 assert result.status_code==200 and len(calls)==1
 assert result.json()['template_only'] is True
 assert 'Check for signs' in result.json()['inspection_brief']


def test_template_recovery_is_management_only_and_uses_no_provider(roles,monkeypatch):
 from test_three_roles import auth,sighting
 client,app,sessions=roles
 report=sighting(client,sessions,key="inspection_offline_recovery")
 monkeypatch.setattr(ai,"completion",lambda *a,**k:pytest.fail("Template must not call Groq"))
 monkeypatch.setattr(ai,"local_completion",lambda *a,**k:pytest.fail("Template must not call Ollama"))
 path=f"/reports/{report['id']}/inspection-guidance?confirmed_species=Psidium%20guajava"
 assert client.get(path).status_code==401
 assert client.get(path,headers=auth(sessions,'reporter')).status_code==403
 response=client.get(path,headers=auth(sessions,'manager'))
 assert response.status_code==200
 assert response.json()['template_only'] is True
 assert 'Check for signs' in response.json()['inspection_brief']


def test_inspection_transport_receipt_one_request_then_zero_cached(roles,monkeypatch):
 from test_three_roles import auth,sighting
 client,app,sessions=roles;report=sighting(client,sessions,key="inspection_transport")
 calls=[];monkeypatch.setenv('GROQ_API_KEY','synthetic-key')
 class Response:
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def read(self,size):return json.dumps({'id':'synthetic-inspection','choices':[{'finish_reason':'stop','message':{'content':json.dumps({'inspection_brief':'Inspect surrounding vegetation.'})}}]}).encode()
 def opening(req,**kwargs):calls.append(req);return Response()
 monkeypatch.setattr(ai,'urlopen',opening)
 path=f"/reports/{report['id']}/inspection-draft";payload={'revision':report['revision'],'species':'Mimosa pudica'}
 results=[client.post(path,headers=auth(sessions,'manager'),json=payload).json() for _ in range(2)]
 assert len(calls)==1
 assert [r['request_receipt']['groq_requests'] for r in results]==[1,0]
 assert 'tools' not in json.loads(calls[0].data)

def test_inspection_failure_uses_one_local_attempt_then_template(roles,monkeypatch):
 from test_three_roles import auth,sighting
 client,app,sessions=roles;report=sighting(client,sessions,key="inspection_local_failure")
 calls=[]
 def groq(body):calls.append('groq');raise ai.HTTPException(429,'Synthetic quota limit')
 def local(body):calls.append('local');raise ai.HTTPException(503,'Synthetic local unavailable')
 monkeypatch.setattr(ai,'completion',groq);monkeypatch.setattr(ai,'local_completion',local);monkeypatch.setattr(ai,'local_model',lambda:'synthetic-qwen')
 result=client.post(f"/reports/{report['id']}/inspection-draft",headers=auth(sessions,'manager'),json={'revision':report['revision'],'species':'Mimosa pudica'})
 assert result.status_code==200 and result.json()['template_only'] is True
 assert calls==['groq','local']
