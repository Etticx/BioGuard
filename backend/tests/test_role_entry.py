"""Role entry and native WebView bootstrap use isolated staff sessions only."""
import pytest
from fastapi.testclient import TestClient
from app import create_app
from test_api import Predictor

@pytest.fixture
def entry(tmp_path):
 app=create_app(Predictor,data_dir=tmp_path,seed_accounts=False,private_beta=True)
 with TestClient(app) as client:
  for username,role,temporary in [('grounds','ground',False),('ecology','officer',False),('temporary','officer',True)]:
   app.state.records.add_user(username,'synthetic-test-password','Synthetic tester',role,must_change=temporary)
  yield client

def signed_in(client,username):
 result=client.post('/auth/login',json={'username':username,'password':'synthetic-test-password'})
 assert result.status_code==200
 token=result.json()['token'];client.cookies.clear()
 return token

def test_shared_login_exposes_role_and_browser_cookie_restores_without_a_bearer(entry):
 for username,role in [('grounds','ground'),('ecology','officer')]:
  response=entry.post('/auth/login',json={'username':username,'password':'synthetic-test-password'})
  assert response.status_code==200
  assert response.json()['user']['role']==role
  assert entry.get('/auth/me').json()['role']==role
  # Routing is not authorization: ground accounts still cannot manage staff.
  assert entry.get('/admin/users').status_code==(200 if role=='officer' else 403)
  entry.post('/auth/logout')

def test_native_officer_bootstrap_sets_a_private_cookie_and_reuses_the_same_session(entry):
 token=signed_in(entry,'ecology')
 response=entry.get('/officer',headers={'Authorization':'Bearer '+token})
 assert response.status_code==200
 cookie=response.headers['set-cookie']
 assert cookie.startswith('bioguard_beta_session=') and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
 assert str(response.url).endswith('/officer') and token not in str(response.url)
 assert entry.get('/auth/me').json()['role']=='officer'
 assert entry.get('/admin/users').status_code==200
 assert entry.post('/auth/logout').status_code==204
 assert entry.get('/auth/me',headers={'Authorization':'Bearer '+token}).status_code==401

@pytest.mark.parametrize('username,status',[('grounds',403),('temporary',403)])
def test_native_bootstrap_rejects_wrong_role_and_temporary_password(entry,username,status):
 token=signed_in(entry,username)
 response=entry.get('/officer',headers={'Authorization':'Bearer '+token})
 assert response.status_code==status and 'set-cookie' not in response.headers

def test_invalid_bootstrap_cannot_create_a_cookie_but_public_login_page_remains_available(entry):
 response=entry.get('/officer',headers={'Authorization':'Bearer invalid-token'})
 assert response.status_code==401 and 'set-cookie' not in response.headers
 response=entry.get('/officer')
 assert response.status_code==200 and 'set-cookie' not in response.headers

def test_https_native_bootstrap_keeps_secure_cookie_flag(entry):
 token=signed_in(entry,'ecology')
 response=entry.get('https://testserver/officer',headers={'Authorization':'Bearer '+token})
 assert response.status_code==200 and '; Secure' in response.headers['set-cookie']
