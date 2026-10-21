const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
class Element{constructor(tag){this.tag=tag;this.children=[];this.style={};this.listeners={};this.textContent='';}append(...items){this.children.push(...items);}setAttribute(name,value){this[name]=value;}addEventListener(name,fn){this.listeners[name]=fn;}replaceChildren(...items){this.children=items;}}
function setup(){const context=vm.createContext({Number,document:{createElement:tag=>new Element(tag)}});const start=source.indexOf('function drawLocation(');assert.ok(start>=0,'Management needs a location renderer');vm.runInContext("const node=(tag,text,cls)=>{const e=document.createElement(tag);e.textContent=text??'';e.className=cls;return e;};"+source.slice(start,source.indexOf('function drawDetail(',start)),context);const container=new Element('section');return{context,container};}
function flatten(e){return[e,...e.children.flatMap(flatten)];}
test('saved point is placed on the same demo map at its exact relative coordinates',()=>{
 const {context,container}=setup();context.drawLocation(container,{site:'Synthetic Elmina site',landmark:'Lake path',location_mode:'demo_map',demo_pin:{map_id:'elmina-city-centre-v1',x:0.72,y:0.83}});
 const all=flatten(container);const pin=all.find(e=>e.className==='report-location-pin');assert.ok(pin);assert.equal(pin.style.left,'72%');assert.equal(pin.style.top,'83%');
 assert.equal(all.find(e=>e.className==='report-location-image').src,'/officer-assets/elmina-city-centre-demo.png');
 assert.ok(all.some(e=>e.textContent==='Lake path'));assert.ok(all.some(e=>/not GPS/.test(e.textContent)));
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
