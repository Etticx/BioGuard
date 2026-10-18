import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
const require=createRequire(import.meta.url);
const query=require('query-string') as {parse:(value:string)=>Record<string,unknown>;stringify:(value:Record<string,string>)=>string};
test('the patched URL decoder preserves plant names and location query parameters',()=>{const input={plant:'Mimosa pudica',landmark:'A/B - café'};assert.deepEqual({...query.parse(query.stringify(input))},input);});
test('malformed URL input completes without the old exponential decoder behavior',()=>{const script=`const q=require(${JSON.stringify(require.resolve('query-string'))});const value=q.parse('q='+ '%C2'.repeat(15000));if(typeof value.q!=='string')process.exit(1);`;assert.doesNotThrow(()=>execFileSync(process.execPath,['-e',script],{timeout:2500,stdio:'pipe'}));});
test('the patched UUID version still supports native project identifiers',()=>{const project=require('xcode').project('test.pbxproj');project.hash={project:{objects:{PBXFileReference:{}}}};const identifiers=Array.from({length:100},()=>project.generateUuid());assert.equal(new Set(identifiers).size,100);for(const value of identifiers)assert.match(value,/^[A-F0-9]{24}$/);});
