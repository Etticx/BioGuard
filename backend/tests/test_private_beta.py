import json
import pytest
from fastapi.testclient import TestClient
from app import create_app
from test_api import Predictor,photo_bytes

@pytest.fixture
def beta(tmp_path):
 app=create_app(Predictor,data_dir=tmp_path,seed_accounts=False,private_beta=True)
 with TestClient(app) as client:
  app.state.records.add_user('tester','tester-password','Invited tester','ground')
  yield client,app

def login(client):
 response=client.post('/auth/login',json={'username':'tester','password':'tester-password'})
 assert response.status_code==200
 return response.json()

def test_identification_is_invite_only_in_beta(beta):
 client,app=beta
 content=photo_bytes()
 assert client.post('/identify',content=content,headers={'Content-Type':'image/png'}).status_code==401
 result=login(client)
 client.cookies.clear()
 response=client.post('/identify',content=content,headers={'Content-Type':'image/png','Authorization':'Bearer '+result['token']})
 assert response.status_code==200,response.text
 assert client.get('/reports',headers={'Authorization':'Bearer '+result['token']}).json()==[]

def test_beta_cookie_is_separate_from_prototype_and_has_security_flags(beta):
 client,app=beta
 response=client.post('/auth/login',json={'username':'tester','password':'tester-password'})
 cookie=response.headers['set-cookie']
 assert cookie.startswith('bioguard_beta_session=') and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
 assert client.get('/auth/me').status_code==200
 token=response.json()['token'];client.cookies.clear();client.cookies.set('bioguard_session',token)
 assert client.get('/auth/me').status_code==401

def test_private_routes_and_framing_headers(beta):
 client,app=beta
 assert client.get('/openapi.json').status_code==404
 assert client.get('/docs').status_code==404
 health=client.get('/health')
 assert health.headers['x-frame-options']=='DENY'
 assert health.headers['referrer-policy']=='no-referrer'
 assert client.get('/beta-information').status_code==200

def test_inference_rejects_an_unbounded_queue(beta,monkeypatch):
 client,app=beta;result=login(client);client.cookies.clear()
 monkeypatch.setattr(app.state.inference_lock,'locked',lambda:True)
 response=client.post('/identify',content=photo_bytes(),headers={'Content-Type':'image/png','Authorization':'Bearer '+result['token']})
 assert response.status_code==429

def test_seed_beta_accounts_must_change_temporary_passwords(tmp_path):
 app=create_app(Predictor,data_dir=tmp_path,private_beta=True)
 with TestClient(app) as client:
  staff=json.loads((tmp_path/'local-accounts.json').read_text('utf-8'))[0]
  response=client.post('/auth/login',json={'username':staff['username'],'password':staff['password']})
  assert response.json()['user']['must_change_password']
  assert client.post('/identify',content=photo_bytes(),headers={'Content-Type':'image/png'}).status_code==403
  assert client.post('/auth/password',json={'current_password':staff['password'],'new_password':'changed-test-password'}).status_code==204
  assert client.get('/auth/me').status_code==401
