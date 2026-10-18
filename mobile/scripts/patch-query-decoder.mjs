// Expo Router 57 uses query-string 7 (CJS). Keep that API while using the patched decoder.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
const require=createRequire(import.meta.url);
const path=require.resolve('query-string');
const source=readFileSync(path,'utf8');
const before="const decodeComponent = require('decode-uri-component');";
const after="const decodeComponent = require('decode-uri-component').default;";
const decoder=require('decode-uri-component');
if(typeof decoder.default!=='function')throw new Error('Expected the patched ESM decoder. Review the compatibility patch.');
if(source.includes(before))writeFileSync(path,source.replace(before,after));
else if(!source.includes(after))throw new Error('query-string changed; review and remove/update this compatibility patch.');
