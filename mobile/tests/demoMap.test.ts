import assert from 'node:assert/strict';
import test from 'node:test';
import { DEMO_MAP_ID, clampPoint, panPoint, imageFrame, isDemoPin } from '../src/services/demoMap';
import { validateReportDetails, type ReportDetails } from '../src/services/reportContract';
const details:ReportDetails={site:'Elmina City Centre',landmark:'Lake edge',extent:'few',observed_on:'2026-01-01',notes:'',request_key:'synthetic_map_report',location_mode:'demo_map'};
test('demo submission requires an explicitly confirmed point',()=>{
 assert.match(validateReportDetails(details)??'',/pin/i);
 assert.equal(validateReportDetails({...details,demo_pin:{map_id:DEMO_MAP_ID,x:0.7,y:0.8}}),null);
 for(const pin of [{map_id:'wrong',x:0.5,y:0.5},{map_id:DEMO_MAP_ID,x:NaN,y:0.5},{map_id:DEMO_MAP_ID,x:1.1,y:0.5}])assert.equal(isDemoPin(pin),false);
});
test('dragging the map updates the image position under the fixed pin and clamps edges',()=>{
 assert.deepEqual(panPoint({x:0.5,y:0.5},64.2,-48.5,642,485),{x:0.4,y:0.6});
 assert.deepEqual(clampPoint({x:-1,y:2}),{x:0,y:1});
});
test('pin stays aligned to the selected map point across zoom and viewport changes',()=>{
 for(const viewport of [{width:320,height:450},{width:900,height:400}])for(const zoom of [1,2,5]){
  const p={x:0.72,y:0.83};const frame=imageFrame(viewport,p,zoom);
  assert.ok(Math.abs(frame.left+p.x*frame.width-viewport.width/2)<0.00001);
  assert.ok(Math.abs(frame.top+p.y*frame.height-viewport.height/2)<0.00001);
 }
});
test('saved demo pins survive draft JSON without inventing GPS coordinates',()=>{
 const saved=JSON.parse(JSON.stringify({...details,demo_pin:{map_id:DEMO_MAP_ID,x:0.72,y:0.83}}));
 assert.equal(saved.demo_pin.x,0.72);assert.equal(saved.latitude,undefined);assert.equal(isDemoPin(saved.demo_pin),true);
});
