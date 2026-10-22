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

def test_one_completion_contains_inspection_and_restoration(monkeypatch):
 calls=[]
 monkeypatch.setenv('GROQ_API_KEY','synthetic')
 monkeypatch.setattr(ai,'load_references',lambda c:[{'url':'https://www.nparks.gov.sg/example','title':'Synthetic','text':'Grona heterophylla native in Malaya.'}])
 def complete(body):
  calls.append(body)
  return {'content':json.dumps({'removal_instructions':'Remove carefully','replacement_species':'Grona heterophylla','replanting_instructions':'Plant if approved','review_notes':'Handover','inspection_brief':'Inspect the surrounding vegetation.'})}
 monkeypatch.setattr(ai,'completion',complete)
 context={'confirmed_species':'Mimosa pudica','inspection':guidance('Mimosa pudica',{})}
 result=ai.generate(context)
 assert len(calls)==1
 assert 'inspection_brief' in calls[0]['response_format']['json_schema']['schema']['required']
 assert 'inspection' in json.loads(calls[0]['messages'][1]['content'])
 assert result['inspection']['source']['excerpt']
 assert result['inspection_brief']=='Inspect the surrounding vegetation.'


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
