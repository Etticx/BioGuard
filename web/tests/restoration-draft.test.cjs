const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../app.js'),'utf8');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.value='';this.listeners={};this.hidden=false;this.dataset={};this.textContent='';}
 append(...children){for(const child of children){child.parentElement=this;this.children.push(child);}}
 insertBefore(child,before){child.parentElement=this;this.children.splice(this.children.indexOf(before),0,child);}
 get lastChild(){return this.children.at(-1);}
 replaceChildren(...children){this.children=[];this.append(...children);}
 setAttribute(){}
 addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
 dispatch(name){for(const fn of this.listeners[name]??[])fn({});}
}
function fixture(){
 const requests=[];let complete,reject;
 const context=vm.createContext({document:{createElement:tag=>new Element(tag)},teams:[],fieldId:0,today:()=> '2026-10-21',workNames:{},feedback:()=>{},Promise,AbortController,
 post:(path,body,options)=>{requests.push({path,body,options});return new Promise((resolve,fail)=>{complete=resolve;reject=fail;});}});
 vm.runInContext("const node=(tag,text,cls)=>{const e=document.createElement(tag);e.textContent=text??'';e.className=cls;return e;};"+source.slice(source.indexOf('function field('),source.indexOf('function fact('))+source.slice(source.indexOf('function appendResearchLinks('),source.indexOf('function drawReview(')),context);
 const form=new Element('form'),notes=new Element('textarea'),wrap=new Element('label');wrap.append(notes);
 const values=context.planFields(form,{}, {id:'synthetic',revision:1,prediction:{predicted_species:'Mimosa pudica'}},notes);
 const all=[];function walk(e){all.push(e);for(const c of e.children)walk(c);}walk(form);
 const paragraphs=all.filter(e=>e.className==='draft-paragraph');
 return {requests,form,notes,all,values,paragraphs,fail:(extra={})=>reject(Object.assign(new Error('Provider rejected key'),extra)),finish:(extra={})=>complete({removal_instructions:'Draft removal',replacement_species:'',replanting_instructions:'Draft planting',review_notes:'Draft note',notice:'Review draft',...extra}),
 species:all.find(e=>e.name==='species_correction'),checkbox:all.find(e=>e.type==='checkbox'),editor:all.find(e=>e.className==='restoration-document'),panel:all.find(e=>e.className==='restoration-draft-panel'),retry:all.find(e=>e.textContent==='Retry draft')};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function confirm(f){f.species.value='Mimosa pudica';f.checkbox.checked=true;f.checkbox.dispatch('change');}
test('confirmation automatically generates one editable document without a draft button',async()=>{
 const f=fixture();assert.equal(f.species.value,'Mimosa pudica');assert.equal(f.species.parentElement.hidden,true);assert.equal(f.requests.length,0);assert.equal(f.panel.hidden,true);assert.equal(f.notes.parentElement.hidden,true);
 assert.equal(f.all.some(e=>e.textContent==='Draft instructions with AI'),false);
 confirm(f);assert.equal(f.editor.hidden,true);assert.equal(f.requests.length,1);assert.equal(f.requests[0].path,'/reports/synthetic/restoration-draft');
 f.finish();await tick();assert.equal(f.editor.hidden,false);assert.equal(f.paragraphs[0].textContent,'Draft removal');assert.equal(f.retry.hidden,true);
 f.paragraphs[0].textContent='Management edited removal';f.paragraphs[1].textContent='Approved synthetic native';f.paragraphs[3].textContent='Edited handover';
 const plan=f.values();assert.equal(plan.removal_instructions,'Management edited removal');assert.equal(plan.replacement_species,'Approved synthetic native');assert.equal(plan.notes,'Edited handover');
 f.checkbox.checked=false;f.checkbox.dispatch('change');assert.equal(f.panel.hidden,true);assert.throws(()=>f.values(),/Confirm/);
});
test('species edits invalidate an in-flight result and require fresh confirmation',async()=>{
 const f=fixture();confirm(f);f.species.value='Imperata cylindrica';f.species.dispatch('input');f.finish();await tick();
 assert.equal(f.checkbox.checked,false);assert.equal(f.editor.hidden,true);assert.equal(f.paragraphs[0].textContent,'');assert.equal(f.requests[0].options.signal.aborted,true);
});
test('edits to the document are preserved when confirmation is toggled',async()=>{
 const f=fixture();confirm(f);f.finish();await tick();f.paragraphs[0].textContent='Management instructions';
 f.checkbox.checked=false;f.checkbox.dispatch('change');f.checkbox.checked=true;f.checkbox.dispatch('change');
 assert.equal(f.requests.length,1);assert.equal(f.paragraphs[0].textContent,'Management instructions');
});
test('leaving assignment while loading does not fill another decision note',async()=>{
 const f=fixture();confirm(f);f.values.cancel();f.form.hidden=true;f.finish();await tick();assert.equal(f.notes.value,'');assert.equal(f.editor.hidden,true);
});
test('failure offers retry; no job can be assigned before a complete reviewed draft',async()=>{
 const f=fixture();confirm(f);f.fail();await tick();assert.equal(f.retry.hidden,false);assert.equal(f.editor.hidden,true);assert.throws(()=>f.values(),/Wait/);
 f.retry.dispatch('click');await tick();f.finish();await tick();assert.equal(f.editor.hidden,false);assert.throws(()=>f.values(),/replacement species/);
});

test('researched candidate selection fills the species and its planting guidance and retains sources',async()=>{
 const f=fixture();confirm(f);f.finish({sources:[{url:'https://www.nparks.gov.sg/test',title:'Official profile'}],candidates:[{scientific_name:'Synthetic native',common_name:'Test native',reason:'Evidence summary',site_checks:'Confirm sunlight',planting_instructions:'Candidate planting instructions',sources:[{url:'https://www.nparks.gov.sg/test',title:'Official profile'}]}]});await tick();
 const all=[];function walk(e){all.push(e);for(const child of e.children)walk(child);}walk(f.form);
 all.find(e=>e.textContent==='Use Synthetic native').dispatch('click');await tick();
 const plan=f.values();assert.equal(plan.replacement_species,'Synthetic native');assert.equal(plan.replanting_instructions,'Candidate planting instructions');assert.equal(plan.research_sources[0],'https://www.nparks.gov.sg/test');
});

test('inline numbered output is displayed as separate steps',async()=>{
 const f=fixture();confirm(f);f.finish({removal_instructions:'1. Wear gloves. 2. Pull carefully; keep a 2.5 cm sample. 3. Bag fragments.',replanting_instructions:'1) Check the site. 2) Plant if approved. 3) Take a photo.'});await tick();
 assert.equal(f.paragraphs[0].textContent,'1. Wear gloves.\n2. Pull carefully; keep a 2.5 cm sample.\n3. Bag fragments.');
 assert.equal(f.paragraphs[2].textContent,'1. Check the site.\n2. Plant if approved.\n3. Take a photo.');
});


test('Groq failure automatically starts exactly one local backup request',async()=>{
 const f=fixture();assert.equal(f.all.some(e=>e.textContent==='Use local backup'),false);
 confirm(f);f.fail({localBackup:true});await tick();assert.equal(f.requests.length,2);assert.equal(f.requests[1].body.provider,'local');
 f.finish({provider:'local',model:'qwen3.5:2b-q4_K_M',replacement_species:'Synthetic native',request_receipt:{groq_requests:0,local_requests:1,pipeline:'test',action_id:'synthetic'}});await tick();
 assert.equal(f.editor.hidden,false);assert.equal(f.values().replacement_species,'Synthetic native');
});

test('failed local backup stops and retry stays local without another Groq request',async()=>{
 const f=fixture();confirm(f);f.fail({localBackup:true});await tick();f.fail();await tick();
 assert.equal(f.requests.length,2);assert.equal(f.retry.hidden,false);f.retry.dispatch('click');await tick();
 assert.equal(f.requests.length,3);assert.equal(f.requests[1].body.provider,'local');assert.equal(f.requests[2].body.provider,'local');
 f.finish({replacement_species:'Synthetic native'});await tick();
});

test('a stale Groq failure cannot start local inference after species changes',async()=>{
 const f=fixture();confirm(f);f.species.value='Imperata cylindrica';f.species.dispatch('input');f.fail({localBackup:true});await tick();
 assert.equal(f.requests.length,1);assert.equal(f.checkbox.checked,false);
});

test('manual edits made during Groq generation survive automatic local fallback',async()=>{
 const f=fixture();confirm(f);f.paragraphs[0].textContent='Preserve this management edit';f.fail({localBackup:true});await tick();
 assert.equal(f.requests.length,2);f.finish({replacement_species:'Synthetic native'});await tick();
 assert.equal(f.paragraphs[0].textContent,'Preserve this management edit');
});

test('loading messages contain no broken UTF-8 character sequences',()=>{
 assert.equal(/\u00e2\u20ac|\u00c2\u00b7/.test(source),false);
});


test('inspection brief and source arrive in the same request and hide when confirmation is removed',async()=>{
 const f=fixture();confirm(f);assert.equal(f.requests.length,1);
 f.finish({inspection_brief:'Check vegetated edges of any nearby paths.',inspection:{species:'Mimosa pudica',location:{kind:'block',block_ids:['B15']},actions:['Inspect surrounding vegetation.'],variables:{used_path_nearby:'unknown'},source:{title:'Queensland Government',url:'https://www.business.qld.gov.au/example',excerpt:'Spread mainly by seeds clinging to humans and animals.'},limitations:['Not a spread prediction.']}});await tick();
 const all=[];function walk(e){all.push(e);for(const c of e.children)walk(c);}walk(f.form);
 assert.equal(f.requests.length,1);
 assert.equal(all.find(e=>e.className==='inspection-brief').textContent,'Check vegetated edges of any nearby paths.');
 assert.ok(all.some(e=>e.textContent==='Location: B15'));
 assert.ok(all.some(e=>e.tag==='blockquote'&&e.textContent.includes('clinging')));
 const host=all.find(e=>e.className==='inspection-guidance');assert.equal(host.hidden,false);
 f.checkbox.checked=false;f.checkbox.dispatch('change');assert.equal(host.hidden,true);
});
