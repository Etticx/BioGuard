const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const config=JSON.parse(fs.readFileSync(path.join(__dirname,'../elmina-map-config.json'),'utf8'));
const script=fs.readFileSync(path.join(__dirname,'../elmina-map.js'),'utf8');
async function fixture(){
 const messages=[],events={},tileEvents={};let current={lat:config.center[0],lng:config.center[1]},tileOptions,masked=false;
 const bounds={contains:([a,b])=>a>=config.bounds[0][0]&&a<=config.bounds[1][0]&&b>=config.bounds[0][1]&&b<=config.bounds[1][1],getSouth:()=>config.bounds[0][0],getWest:()=>config.bounds[0][1],getNorth:()=>config.bounds[1][0],getEast:()=>config.bounds[1][1],pad(){return this;}};
 const map={setView(p){current={lat:p[0],lng:p[1]};return this;},getCenter:()=>current,panTo(p){current={lat:p[0],lng:p[1]};events.moveend?.();},on(name,fn){events[name]=fn;},invalidateSize(){},remove(){}};
 const elements={status:{hidden:false,textContent:''},'fixed-pin':{hidden:true},map:{}};
 const context=vm.createContext({URL,URLSearchParams,location:{search:'?mode=picker',origin:'http://localhost:8091'},document:{getElementById:id=>elements[id]},fetch:async()=>({ok:true,json:async()=>config}),setTimeout:()=>0,ResizeObserver:class{observe(){}disconnect(){}},window:{parent:{postMessage:(value,origin)=>messages.push({value,origin})},addEventListener(){}},L:{latLngBounds:()=>bounds,map:()=>map,tileLayer:(url,options)=>{tileOptions={url,...options};return{on(name,fn){tileEvents[name]=fn;},addTo(){}};},polygon:()=>({addTo(){masked=true;}})}});
 context.window.L=context.L; await vm.runInContext(script,context);tileEvents.tileload();tileEvents.load();
 return{messages,map,get tileOptions(){return tileOptions;},get masked(){return masked;}};
}
test('shared map clamps selected coordinates to the pilot boundary including its edges',async()=>{
 const f=await fixture();f.map.panTo([config.bounds[1][0]+0.02,config.bounds[0][1]-0.02]);const value=f.messages.at(-1).value;
 assert.equal(value.type,'bioguard:map-point');assert.equal(value.latitude,config.bounds[1][0]);assert.equal(value.longitude,config.bounds[0][1]);
 assert.equal(f.messages.at(-1).origin,'http://localhost:8091');
});
test('tiles are bounded, attribution is visible, and outside map content is masked',async()=>{
 const f=await fixture();assert.equal(f.tileOptions.url,config.tile_url);assert.ok(f.tileOptions.bounds);assert.match(f.tileOptions.attribution,/OpenStreetMap contributors/);assert.equal(f.masked,true);assert.equal(f.tileOptions.maxNativeZoom,19);
});
