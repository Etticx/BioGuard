import assert from 'node:assert/strict';
import test from 'node:test';
import { canonicalWebEntry, isOfficerPage, officerUrl, parseSession, parseUser, sessionHeaders, shouldForgetSession, workspaceFor } from '../src/services/roleAccess';
import { RequestError, SessionExpired } from '../src/services/requestErrors';
const user = {id:'synthetic-user',username:'tester',display_name:'Test account',role:'ground' as const};

test('one sign-in accepts ground, ecology and management accounts and preserves password gate',()=>{
 for(const role of ['ground','ecology','management'] as const){
  const session=parseSession({token:'synthetic-token',user:{...user,role}});
  assert.equal(workspaceFor(session.user),role);
  assert.equal(workspaceFor({...session.user,must_change_password:true}),'password');
 }
});
test('unrecognised roles and incomplete account responses cannot restore a workspace',()=>{
 for(const invalid of [null,{}, {...user,role:'admin'}, {...user,id:''}])assert.throws(()=>parseUser(invalid));
 for(const invalid of [{user},{token:'',user},{token:'test',user:{...user,role:'admin'}}])assert.throws(()=>parseSession(invalid));
});
test('browser cookie sessions omit Authorization so the private cookie authenticates reports and identification',()=>{
 assert.deepEqual(sessionHeaders({token:'',user}),{});
 assert.deepEqual(sessionHeaders(undefined),{});
 assert.deepEqual(sessionHeaders({token:'native-test-token',user}),{Authorization:'Bearer native-test-token'});
});
test('officer destination uses the configured backend and never includes session credentials',()=>{
 assert.equal(officerUrl('', 'http://localhost:8001'),'http://localhost:8001/officer');
 assert.equal(officerUrl('http://192.168.1.8:8001'),'http://192.168.1.8:8001/officer');
 assert.equal(officerUrl('https://beta.test/'),'https://beta.test/officer');
 assert.throws(()=>officerUrl('https://user:secret@beta.test'));
 assert.throws(()=>officerUrl('javascript:alert(1)'));
});
test('embedded officer navigation and bridge messages must come from the expected management page',()=>{
 const expected='http://192.168.1.8:8001/officer';
 assert.equal(isOfficerPage(expected,expected),true);
 for(const url of ['http://192.168.1.8:8001/','http://192.168.1.8:8000/officer','https://other.test/officer','javascript:alert(1)','bad'])assert.equal(isOfficerPage(url,expected),false);
});

test('private beta preview moves to the backend origin before credentials are entered',()=>{
 assert.equal(canonicalWebEntry('http://192.168.1.8:8001','http://localhost:8083',true),'http://192.168.1.8:8001/');
 assert.equal(canonicalWebEntry('', 'http://localhost:8001',true),null);
 assert.equal(canonicalWebEntry('http://localhost:8000','http://localhost:8082',false),null);
});

test('restoration preserves native sessions during server failures and clears revoked sessions',()=>{
 for(const status of [429,500,503])assert.equal(shouldForgetSession(new RequestError('Temporary server failure',status)),false);
 assert.equal(shouldForgetSession(new TypeError('Network unavailable')),false);
 assert.equal(shouldForgetSession(new SessionExpired('Revoked')),true);
 assert.equal(shouldForgetSession(new RequestError('Disabled account',403)),true);
});
