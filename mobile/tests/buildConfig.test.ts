import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
const {validateBuildApi}=require('../scripts/check-build.mjs') as {validateBuildApi:(value?:string)=>string};
test('signed beta builds reject unusable or secret-bearing API addresses',()=>{for(const value of [undefined,'/','http://beta.example.org','https://localhost','https://127.0.0.1','https://[::1]','https://0x7f000001','https://user:secret@beta.example.org','https://beta.example.org/?key=secret','https://your-domain.example'])assert.throws(()=>validateBuildApi(value));assert.equal(validateBuildApi('https://beta.example.org/'),'https://beta.example.org');});
