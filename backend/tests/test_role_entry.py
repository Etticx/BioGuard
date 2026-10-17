"""Role entry and native WebView bootstrap use isolated staff sessions only."""
import pytest
from fastapi.testclient import TestClient
from test_api import Predictor
from app import create_app

@pytest.fixture
def entry(tmp_path,monkeypatch):
 web=tmp_path/"synthetic-mobile-preview";web.mkdir();(web/"index.html").write_text("<main>Synthetic common BioGuard entry</main>",encoding="utf-8")
 monkeypatch.setenv("BIOGUARD_WEB_DIR",str(web))
 app=create_app(Predictor,data_dir=tmp_path,seed_accounts=False,private_beta=True)
 with TestClient(app) as client:
  for username,role,temporary in [('grounds','ground',False),('ecology','ecology',False),('management','management',False),('temporary','management',True)]:
   app.state.records.add_user(username,'synthetic-test-password','Synthetic tester',role,must_change=temporary)
  yield client

def signed_in(client,username):
 result=client.post('/auth/login',json={'username':username,'password':'synthetic-test-password'})
 assert result.status_code==200
 token=result.json()['token'];client.cookies.clear()
 return token

def test_shared_login_exposes_role_and_browser_cookie_restores_without_a_bearer(entry):
 for username,role in [('grounds','ground'),('ecology','ecology'),('management','management')]:
  response=entry.post('/auth/login',json={'username':username,'password':'synthetic-test-password'})
  assert response.status_code==200
  assert response.json()['user']['role']==role
  assert entry.get('/auth/me').json()['role']==role
  # Routing is not authorization: ground accounts still cannot manage staff.
  assert entry.get('/admin/users').status_code==(200 if role=='management' else 403)
  entry.post('/auth/logout')

def test_native_officer_bootstrap_sets_a_private_cookie_and_reuses_the_same_session(entry):
 token=signed_in(entry,'management')
 response=entry.get('/officer',headers={'Authorization':'Bearer '+token})
 assert response.status_code==200
 cookie=response.headers['set-cookie']
 assert cookie.startswith('bioguard_beta_session=') and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
 assert str(response.url).endswith('/officer') and token not in str(response.url)
 assert entry.get('/auth/me').json()['role']=='management'
 assert entry.get('/admin/users').status_code==200
 assert entry.post('/auth/logout').status_code==204
 assert entry.get('/auth/me',headers={'Authorization':'Bearer '+token}).status_code==401

@pytest.mark.parametrize('username,status',[('grounds',403),('ecology',403),('temporary',403)])
def test_native_bootstrap_rejects_wrong_role_and_temporary_password(entry,username,status):
 token=signed_in(entry,username)
 response=entry.get('/officer',headers={'Authorization':'Bearer '+token})
 assert response.status_code==status and 'set-cookie' not in response.headers

def test_invalid_native_bootstrap_cannot_create_a_cookie_and_signed_out_browser_uses_common_entry(entry):
 response=entry.get('/officer',headers={'Authorization':'Bearer invalid-token'})
 assert response.status_code==401 and 'set-cookie' not in response.headers
 response=entry.get('/officer',follow_redirects=False)
 assert response.status_code==303 and response.headers['location']=='/' and 'set-cookie' not in response.headers
 root=entry.get(response.headers['location'])
 assert root.status_code==200 and 'Synthetic common BioGuard entry' in root.text
 assert entry.get('/auth/me').status_code==401

def test_https_native_bootstrap_keeps_secure_cookie_flag(entry):
 token=signed_in(entry,'management')
 response=entry.get('https://testserver/officer',headers={'Authorization':'Bearer '+token})
 assert response.status_code==200 and '; Secure' in response.headers['set-cookie']


@pytest.mark.parametrize('username,role,temporary',[('grounds','ground',False),('ecology','ecology',False),('temporary','management',True)])
def test_browser_cookie_returns_to_common_entry_without_losing_the_account_or_password_gate(entry,username,role,temporary):
 response=entry.post('/auth/login',json={'username':username,'password':'synthetic-test-password'})
 assert response.status_code==200
 response=entry.get('/officer',follow_redirects=False)
 assert response.status_code==303 and response.headers['location']=='/'
 assert 'set-cookie' not in response.headers
 me=entry.get('/auth/me')
 assert me.status_code==200 and me.json()['role']==role
 assert bool(me.json()['must_change_password']) is temporary
 root=entry.get(response.headers['location'])
 assert root.status_code==200 and 'Synthetic common BioGuard entry' in root.text


def test_management_browser_logout_revokes_the_session_and_uses_the_same_sign_in_entry(entry):
 response=entry.post('/auth/login',json={'username':'management','password':'synthetic-test-password'})
 assert response.status_code==200
 token=response.json()['token']
 assert entry.get('/officer',follow_redirects=False).status_code==200
 response=entry.post('/auth/logout')
 assert response.status_code==204 and 'Max-Age=0' in response.headers['set-cookie']
 assert entry.get('/auth/me').status_code==401
 response=entry.get('/officer',follow_redirects=False)
 assert response.status_code==303 and response.headers['location']=='/'
 assert entry.get('/officer',headers={'Authorization':'Bearer '+token}).status_code==401


def test_expired_management_cookie_returns_to_common_entry_instead_of_another_dashboard_login(entry):
 response=entry.post('/auth/login',json={'username':'management','password':'synthetic-test-password'})
 assert response.status_code==200
 with entry.app.state.records.connect() as db:
  db.execute('UPDATE sessions SET expires_at=0')
 response=entry.get('/officer',follow_redirects=False)
 assert response.status_code==303 and response.headers['location']=='/'
 assert entry.get('/auth/me').status_code==401
 assert entry.get(response.headers['location']).status_code==200


def test_explicit_native_authorization_never_borrows_a_different_browser_cookie(entry):
 ecology=signed_in(entry,'ecology')
 response=entry.post('/auth/login',json={'username':'management','password':'synthetic-test-password'})
 assert response.status_code==200
 for authorization,status in [('Bearer invalid-token',401),('Basic invalid-token',401),('Bearer '+ecology,403)]:
  response=entry.get('/officer',headers={'Authorization':authorization},follow_redirects=False)
  assert response.status_code==status and 'set-cookie' not in response.headers
 assert entry.get('/auth/me').json()['role']=='management'
