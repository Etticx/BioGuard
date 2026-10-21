const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../app.js'),'utf8');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.value='';this.listeners={};this.hidden=false;}
 append(...children){for(const child of children){child.parentElement=this;this.children.push(child);}}
 insertBefore(child,before){child.parentElement=this;this.children.splice(this.children.indexOf(before),0,child);}
 setAttribute(){}
 addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
 dispatch(name){for(const fn of this.listeners[name]??[])fn({});}
}
function fixture(){
 const requests=[];let complete;
 const context=vm.createContext({document:{createElement:tag=>new Element(tag)},teams:[],fieldId:0,today:()=> '2026-10-21',workNames:{},feedback:()=>{},Promise,
 post:(path,body)=>{requests.push({path,body});return new Promise(resolve=>complete=resolve);}});
 vm.runInContext("const node=(tag,text,cls)=>{const e=document.createElement(tag);e.textContent=text;e.className=cls;return e;};"+source.slice(source.indexOf('function field('),source.indexOf('function fact('))+source.slice(source.indexOf('function planFields('),source.indexOf('function drawReview(')),context);
 const form=new Element('form'),notes=new Element('textarea'),wrap=new Element('label');wrap.append(notes);
 context.planFields(form,{}, {id:'synthetic',revision:1},notes);
 const all=[];function walk(e){all.push(e);for(const c of e.children)walk(c);}walk(form);
 return {requests,form,notes,all,finish:()=>complete({removal_instructions:'Draft removal',replacement_species:'',replanting_instructions:'Draft planting',review_notes:'Draft note',notice:'Review draft'}),
 species:all.find(e=>e.name==='confirmed_species'),checkbox:all.find(e=>e.type==='checkbox'),removal:all.find(e=>e.name==='removal_instructions'),assistant:all.find(e=>e.className==='ai-draft')};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('confirmation gates visibility and the only automatic request is a draft',async()=>{
 const f=fixture();assert.equal(f.requests.length,0);assert.equal(f.removal.parentElement.hidden,true);assert.equal(f.notes.parentElement.hidden,true);
 f.species.value='Mimosa pudica';f.checkbox.checked=true;f.checkbox.dispatch('change');
 assert.equal(f.removal.parentElement.hidden,false);assert.equal(f.requests.length,1);assert.equal(f.requests[0].path,'/reports/synthetic/restoration-draft');
 f.finish();await tick();assert.equal(f.removal.value,'Draft removal');assert.equal(f.notes.value,'Draft note');
 f.checkbox.checked=false;f.checkbox.dispatch('change');assert.equal(f.removal.parentElement.hidden,true);
});
test('species edits invalidate an in-flight result and require fresh confirmation',async()=>{
 const f=fixture();f.species.value='Mimosa pudica';f.checkbox.checked=true;f.checkbox.dispatch('change');
 f.species.value='Imperata cylindrica';f.species.dispatch('input');f.finish();await tick();
 assert.equal(f.checkbox.checked,false);assert.equal(f.removal.value,'');assert.equal(f.removal.parentElement.hidden,true);
});
test('late drafts preserve text typed by management',async()=>{
 const f=fixture();f.species.value='Mimosa pudica';f.checkbox.checked=true;f.checkbox.dispatch('change');
 f.removal.value='Management instructions';f.notes.value='Management note';f.finish();await tick();
 assert.equal(f.removal.value,'Management instructions');assert.equal(f.notes.value,'Management note');
});

test('leaving assignment while a draft is loading does not fill the other decision note',async()=>{
 const f=fixture();f.species.value='Mimosa pudica';f.checkbox.checked=true;f.checkbox.dispatch('change');
 f.form.hidden=true;f.finish();await tick();assert.equal(f.notes.value,'');assert.equal(f.removal.value,'');
});
