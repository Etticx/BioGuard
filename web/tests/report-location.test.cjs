const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
class Element{constructor(tag){this.tag=tag;this.children=[];this.style={};this.listeners={};this.textContent='';}append(...items){this.children.push(...items);}setAttribute(name,value){this[name]=value;}addEventListener(name,fn){this.listeners[name]=fn;}replaceChildren(...items){this.children=items;}getBoundingClientRect(){return{left:0,top:0,width:642,height:453};}setPointerCapture(){}}
function setup(){const context=vm.createContext({Number,document:{createElement:tag=>new Element(tag)}});const start=source.indexOf('function drawLocation(');assert.ok(start>=0,'Management needs a location renderer');vm.runInContext("const node=(tag,text,cls)=>{const e=document.createElement(tag);e.textContent=text??'';e.className=cls;return e;};"+source.slice(start,source.indexOf('function drawDetail(',start)),context);const container=new Element('section');return{context,container};}
function flatten(e){return[e,...e.children.flatMap(flatten)];}
test('saved point is placed on the same demo map at its exact relative coordinates',()=>{
 const {context,container}=setup();context.drawLocation(container,{site:'Synthetic Elmina site',landmark:'Lake path',location_mode:'demo_map',demo_pin:{map_id:'elmina-city-centre-v1',x:0.72,y:0.83}});
 const all=flatten(container);const pin=all.find(e=>e.className==='report-location-pin');assert.ok(pin);assert.equal(pin.style.left,'72%');assert.equal(pin.style.top,'83%');
 assert.equal(all.find(e=>e.className==='report-location-image').src,'/officer-assets/elmina-city-centre-demo.png');
 assert.equal(all.some(e=>e.className==='report-location-info'),false);
 assert.equal(all.find(e=>e.className==='report-location-layout').children.length,1);
});
test('older and invalid locations never receive an invented centre pin',()=>{
 for(const pin of [undefined,{map_id:'other',x:0.5,y:0.5},{map_id:'elmina-city-centre-v1',x:NaN,y:0.5},{map_id:'elmina-city-centre-v1',x:1.5,y:0.5}]){
 const {context,container}=setup();context.drawLocation(container,{site:'Synthetic',landmark:'Path',demo_pin:pin});assert.equal(flatten(container).some(e=>e.className==='report-location-pin'),false);
 }
});
test('location section is inserted after report facts and before review decisions',()=>{
 const detail=source.slice(source.indexOf('function drawDetail('),source.indexOf('function appendResearchLinks('));
 assert.ok(detail.indexOf('drawLocation(detail,report)')>detail.indexOf('detail.append(facts)'));
 assert.ok(detail.indexOf('drawLocation(detail,report)')<detail.indexOf('drawReview(detail,report)'));
});
test('management and phone use the identical version of the supplied map',()=>{
 assert.deepEqual(fs.readFileSync(path.join(__dirname,'../elmina-city-centre-demo.png')),fs.readFileSync(path.join(__dirname,'../../mobile/assets/elmina-city-centre-demo.png')));
});

function gestureFixture(){const f=setup();const report={site:'Synthetic',landmark:'Lake',demo_pin:{map_id:'elmina-city-centre-v1',x:0.72,y:0.83}};f.context.drawLocation(f.container,report);const all=flatten(f.container);return{report,frame:all.find(e=>e.className==='report-location-map'),image:all.find(e=>e.className==='report-location-image'),pin:all.find(e=>e.className==='report-location-pin')};}
function event(extra){return{preventDefault(){},...extra};}
test('wheel zoom keeps the reported pin attached to its map point without modifying the report',()=>{
 const f=gestureFixture();const original=JSON.stringify(f.report);assert.equal(typeof f.frame.listeners.wheel,'function');
 f.frame.listeners.wheel(event({deltaY:-120,deltaMode:0,clientX:642*0.72,clientY:453*0.83}));
 assert.match(f.image.style.transform,/scale\(1\./);assert.ok(Math.abs(parseFloat(f.pin.style.left)-72)<0.00001);assert.ok(Math.abs(parseFloat(f.pin.style.top)-83)<0.00001);assert.equal(JSON.stringify(f.report),original);
});
test('two touch pointers pinch to zoom and a single pointer pans the zoomed map',()=>{
 const f=gestureFixture();const original=JSON.stringify(f.report);assert.equal(typeof f.frame.listeners.pointerdown,'function');
 f.frame.listeners.pointerdown(event({pointerId:1,button:0,clientX:100,clientY:100}));
 f.frame.listeners.pointerdown(event({pointerId:2,button:0,clientX:200,clientY:100}));
 f.frame.listeners.pointermove(event({pointerId:2,clientX:300,clientY:100}));assert.match(f.image.style.transform,/scale\(2\)/);
 f.frame.listeners.pointerup(event({pointerId:2}));const before=f.pin.style.left;
 f.frame.listeners.pointermove(event({pointerId:1,clientX:80,clientY:100}));assert.notEqual(f.pin.style.left,before);assert.equal(JSON.stringify(f.report),original);
});
