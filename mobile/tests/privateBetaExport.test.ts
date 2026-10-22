import assert from 'node:assert/strict';
import test from 'node:test';
import { privateBetaWebEnv } from '../scripts/export-private-beta.mjs';

test('private beta browser exports always enable sign-in and same-origin authentication',()=>{
 const env=privateBetaWebEnv({PATH:'synthetic-path'});
 assert.equal(env.EXPO_PUBLIC_PRIVATE_BETA,'1');
 assert.equal(env.EXPO_PUBLIC_API_URL,'/');
 assert.equal(env.PATH,'synthetic-path');
});
test('native Expo LAN settings cannot leak into the served browser build',()=>{
 const source={EXPO_PUBLIC_PRIVATE_BETA:'0',EXPO_PUBLIC_API_URL:'http://192.168.1.2:8001'};
 assert.deepEqual(privateBetaWebEnv(source),{EXPO_PUBLIC_PRIVATE_BETA:'1',EXPO_PUBLIC_API_URL:'/'});
 assert.equal(source.EXPO_PUBLIC_PRIVATE_BETA,'0');
});
