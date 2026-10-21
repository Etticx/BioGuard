import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {isElminaPoint,elminaMapUrl,decodeMapMessage,isElminaMapPage} from '../src/services/elminaMap';
test('only finite real coordinates inside the selected pilot area are accepted',()=>{
 assert.equal(isElminaPoint({latitude:3.180661,longitude:101.509091}),true);
 for(const p of [{latitude:0,longitude:0},{latitude:NaN,longitude:101.509091},{latitude:3.19,longitude:101.509091}])assert.equal(isElminaPoint(p),false);
});
test('map messages require the correct map and a valid point',()=>{
 assert.equal(decodeMapMessage({type:'bioguard:map-point',map_id:'elmina-lakeside-v1',latitude:3.180661,longitude:101.509091})?.type,'bioguard:map-point');
 assert.equal(decodeMapMessage({type:'bioguard:map-point',map_id:'other',latitude:3.180661,longitude:101.509091}),null);
 assert.equal(decodeMapMessage({type:'bioguard:map-ready',map_id:'elmina-lakeside-v1',latitude:50,longitude:0}),null);
});
test('map URL stays on the backend and preserves manual coordinate selection',()=>{
 const url=new URL(elminaMapUrl('http://localhost:8001','http://localhost:8085','picker',{latitude:3.180661,longitude:101.509091}));
 assert.equal(url.origin,'http://localhost:8001');assert.equal(url.pathname,'/maps/elmina');assert.equal(url.searchParams.get('latitude'),'3.180661');assert.equal(url.searchParams.get('parent_origin'),'http://localhost:8085');
});
test('phone and web share identical pilot boundaries',()=>{
 assert.deepEqual(JSON.parse(readFileSync(new URL('../src/services/elmina-map-config.json',import.meta.url),'utf8')),JSON.parse(readFileSync(new URL('../../web/elmina-map-config.json',import.meta.url),'utf8')));
});

test('native map navigation stays on the exact trusted backend map route',()=>{
 const url='http://localhost:8001/maps/elmina?mode=picker';
 assert.equal(isElminaMapPage('http://localhost:8001/maps/elmina?mode=view',url),true);
 assert.equal(isElminaMapPage('https://evil.test/maps/elmina',url),false);
 assert.equal(isElminaMapPage('http://localhost:8001/maps/elmina-extra',url),false);
});
