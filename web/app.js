const $=s=>document.querySelector(s);
const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const statusNames={submitted:'New',needs_info:'More info needed',assigned:'Assigned',closed:'Closed',in_progress:'In progress',blocked:'Problem reported',awaiting_verification:'Ready for review',follow_up:'Follow-up due',completed:'Closed',cancelled:'Cancelled',duplicate:'Linked duplicate'};
const workNames={restoration:'Restoration',inspection:'Inspection',monitoring:'Monitoring',removal:'Removal',replanting:'Replanting',removal_replanting:'Removal & replanting',follow_up:'Follow-up'};
let currentUser,reports=[],teams=[],notices=[],selectedId,filter='all',loading=false,view='reports',fieldId=0;
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
async function api(path,options={}){const response=await fetch(path,{credentials:'same-origin',...options,headers:{Accept:'application/json',...options.headers}});if(!response.ok){let message='Could not complete this action.';try{const body=await response.json();message=typeof body.detail==='string'?body.detail:'Check the fields and try again.';}catch{}if(response.status===401)showLogin(true);const failure=new Error(message);failure.status=response.status;failure.localBackup=response.headers.get('X-BioGuard-Local-Backup')==='available';throw failure;}return response.status===204?null:response.json();}
const post=(path,body,options={})=>api(path,{...options,method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function showLogin(ended=false){currentUser=undefined;reports=[];teams=[];notices=[];selectedId=undefined;$('#workspace').hidden=true;$('#account').hidden=true;$('#inbox').replaceChildren();$('#detail').replaceChildren();$('#manage-panel').replaceChildren();$('#entry-panel').hidden=false;$('#entry-message').textContent='Opening sign in...';$('#entry-retry').hidden=true;if(window.ReactNativeWebView){if(ended)window.ReactNativeWebView.postMessage('bioguard:session-ended');}else window.location.replace('/');}
function badge(status){return node('span',statusNames[status]||status.replaceAll('_',' '),'badge '+(['submitted','needs_info','blocked','awaiting_verification'].includes(status)?'warning':''));}
function feedback(message,failed=false){const e=$('#feedback');e.textContent=message;e.className=message?(failed?'error':'success'):'';}
function field(form,label,name,kind='input',value=''){const wrap=node('label',label);const input=node(kind);input.name=name;input.id=name+'_'+(++fieldId);wrap.htmlFor=input.id;input.value=value??'';wrap.append(input);form.append(wrap);return input;}
function option(select,value,label){const e=node('option',label);e.value=value;select.append(e);}
function select(form,label,name,options,value){const input=field(form,label,name,'select');for(const [v,l] of options)option(input,v,l);if(value!==undefined)input.value=value??'';return input;}
function text(form,label,name,value='',max=1600){const input=field(form,label,name,'textarea',value);input.maxLength=max;return input;}
function check(form,label,checked=false){const wrap=node('label',undefined,'check');const input=node('input');input.type='checkbox';input.checked=checked;wrap.append(input,node('span',label));form.append(wrap);return input;}
function button(label,run,cls='secondary'){const b=node('button',label,cls);b.type='button';b.addEventListener('click',()=>{b.disabled=true;Promise.resolve().then(run).catch(e=>feedback(e.message,true)).finally(()=>{b.disabled=false;});});return b;}
function fact(label,value){const e=node('div');e.append(node('span',label,'fact-label'),node('span',value??'-'));return e;}
function photos(container,report,ids,labels={}){const grid=node('div',undefined,'photos work');for(const photo of report.photos.filter(p=>ids.includes(p.id))){const fig=node('figure'),image=node('img');image.src=photo.url;image.alt='Evidence for '+report.reference;image.loading='lazy';fig.append(image,node('figcaption',labels[photo.id]??photo.kind.replaceAll('_',' ')));grid.append(fig);}container.append(grid);}
async function enter(user){if(!['ground','ecology','management'].includes(user.role))throw new Error('Could not read your account.');if(user.role!=='management'||user.must_change_password){showLogin(true);return;}currentUser=user;$('#entry-panel').hidden=true;$('#workspace').hidden=false;$('#account').hidden=false;$('#account-name').textContent=user.display_name;teams=await api('/teams');showView('reports');await loadReports();await loadNotices();}
async function loadReports(){if(loading)return;loading=true;$('#refresh').disabled=true;try{reports=await api('/reports');teams=await api('/teams');drawInbox();if(selectedId){const item=reports.find(r=>r.id===selectedId);if(item)drawDetail(item);}}catch(e){feedback(e.message,true);}finally{loading=false;$('#refresh').disabled=false;}}
async function loadNotices(){if(!currentUser||currentUser.must_change_password)return;try{notices=await api('/notifications');const count=notices.filter(n=>!n.read_at).length;$('#unread').textContent=count?`(${count})`:'';if(view==='updates')drawNotices();}catch{}}
function drawInbox(){const inbox=$('#inbox');inbox.replaceChildren();const visible=reports.filter(r=>filter==='all'||(filter==='assigned'?['assigned','accepted','in_progress','blocked','follow_up'].includes(r.status):filter==='completed'?['completed','closed','cancelled','duplicate'].includes(r.status):filter==='submitted'?['submitted','needs_info'].includes(r.status):r.status===filter));if(!visible.length)inbox.append(node('p','No reports in this view.','empty'));for(const report of visible){const b=node('button',undefined,'report-row'+(report.id===selectedId?' selected':''));const name=report.prediction?.common_name??'Plant to be reviewed';b.setAttribute('aria-label',`${report.reference}: ${report.site}, ${name}`);b.append(node('span',name,'row-title'),node('span',`${report.site} · ${report.landmark}`,'row-sub'));const meta=node('span',undefined,'row-meta');meta.append(badge(report.status),node('span',report.reference,'row-sub'));b.append(meta);if(report.work_items.some(w=>w.overdue))b.append(node('span','Visit overdue','overdue'));if(report.identification_questioned)b.append(node('span','Reporter questioned the match','row-sub'));b.addEventListener('click',()=>{selectedId=report.id;drawInbox();drawDetail(report);});inbox.append(b);}}
function drawLocation(container,report){
 const section=node('section',undefined,'report-location');section.setAttribute('aria-label','Reported plant location');
 section.append(node('h3','Plant location'));
 const pin=report.demo_pin;
 const valid=pin&&pin.map_id==='elmina-city-centre-v1'&&typeof pin.x==='number'&&typeof pin.y==='number'&&Number.isFinite(pin.x)&&Number.isFinite(pin.y)&&pin.x>=0&&pin.x<=1&&pin.y>=0&&pin.y<=1;
 if(!valid){section.append(node('p',pin?'This map location cannot be displayed.':'No map pin was saved with this report.','compact-note'));container.append(section);return;}
 const layout=node('div',undefined,'report-location-layout'),figure=node('figure',undefined,'report-location-figure');
 const frame=node('div',undefined,'report-location-map'),image=node('img',undefined,'report-location-image');
 image.src='/officer-assets/elmina-city-centre-demo.png';image.alt='Elmina City Centre demo map';image.width=642;image.height=453;
 const marker=node('img',undefined,'report-location-pin');marker.src='/officer-assets/location-pin.svg';marker.alt='Plant location selected by the reporter';marker.style.left=(pin.x*100)+'%';marker.style.top=(pin.y*100)+'%';
 image.addEventListener('error',()=>{frame.hidden=true;figure.append(node('p','The location map could not load. Refresh to try again.','compact-note'));});
 frame.append(image,marker);figure.append(frame,node('figcaption','Red pin: location selected by the reporter.','compact-note'));
 const information=node('div',undefined,'report-location-info');
 information.append(node('span','Site','fact-label'),node('p',report.site),node('span','Nearby landmark','fact-label'),node('p',report.landmark),node('p','Demo map position, not GPS coordinates.','compact-note'));
 layout.append(figure,information);section.append(layout);container.append(section);
}
function drawDetail(report){const detail=$('#detail');detail.replaceChildren();const top=node('div',undefined,'detail-top');top.append(node('span',report.reference,'reference'),badge(report.status));detail.append(top,node('h2',report.site),node('p',[report.block_name,report.landmark].filter(Boolean).join(' · '),'detail-location'));photos(detail,report,report.photos.filter(p=>!p.work_id).map(p=>p.id));
 const suggestion=node('div',undefined,'suggestion');if(report.prediction){const p=report.prediction;suggestion.append(node('span',`${(p.confidence*100).toFixed(1)}%`,'confidence'),node('span','MODEL SUGGESTION','eyebrow'),node('h3',p.common_name),node('p',p.predicted_species,'scientific'),node('p',p.uncertain_identification?'Not confident · review needed':p.sdp_listed_invasive?'Invasive · SDP list':'Not listed as invasive · SDP list','compact-note'));}else if(report.review?.confirmed_species&&report.review.confirmed_invasive===true)suggestion.append(node('span','MANAGEMENT CONFIRMED','eyebrow'),node('h3',report.review.confirmed_species),node('p','Invasive identification confirmed for this site.','compact-note'));else suggestion.append(node('h3','Identification pending'),node('p','Confirm the plant from the photos or request clearer evidence before assigning restoration.','compact-note'));if(report.identification_questioned)suggestion.append(node('p','The reporter questioned this identification.','error'));detail.append(suggestion);
 const facts=node('div',undefined,'facts');facts.append(fact('Reported by',report.reporter_name),fact('Observed',report.observed_on),fact('Amount seen',{one:'One plant',few:'A few plants',patch:'A patch',unsure:'Not sure'}[report.extent]),fact('Submitted',new Date(report.created_at).toLocaleString()));if(report.latitude!=null)facts.append(fact('Coordinates',`${report.latitude}, ${report.longitude}`));detail.append(facts);if(report.notes)detail.append(node('p',report.notes,'note'));
 drawLocation(detail,report);
 if(report.review)detail.append(node('hr',undefined,'divider'),node('h3','Management review'),node('p',report.review.notes,'note'),node('p',report.review.reviewer_name,'compact-note'));
 for(const work of [...report.work_items].sort((a,b)=>Number(['verified','cancelled'].includes(a.status))-Number(['verified','cancelled'].includes(b.status))))drawWork(detail,report,work);
 const active=report.work_items.some(w=>!['verified','cancelled'].includes(w.status));if(!active&&!['cancelled','duplicate','completed','closed'].includes(report.status))drawReview(detail,report);
 const actions=node('details');actions.append(node('summary','Case actions'));const form=node('form',undefined,'review-form');const decision=select(form,'Case action','case_action',[['cancel','Cancel case and active visits'],['duplicate','Link as duplicate'],...(!active?[['reopen','Reopen for review']]:[])]);const candidates=reports.filter(r=>r.id!==report.id&&r.status!=='duplicate');const original=select(form,'Original report','duplicate_of',[['','Choose original'],...candidates.map(r=>[r.id,`${r.reference} · ${r.site} · ${r.landmark}`])]);original.parentElement.hidden=true;decision.addEventListener('change',()=>{original.parentElement.hidden=decision.value!=='duplicate';original.required=decision.value==='duplicate';});const note=text(form,'Reason','case_reason');note.required=true;const err=node('p','','error');const submit=node('button','Save case action','secondary');submit.type='submit';form.append(err,submit);form.addEventListener('submit',async e=>{e.preventDefault();submit.disabled=true;try{await post(`/reports/${report.id}/review`,{revision:report.revision,decision:decision.value,notes:note.value,duplicate_of:decision.value==='duplicate'?original.value:null});feedback('Case updated.');await loadReports();}catch(f){err.textContent=f.message;submit.disabled=false;}});actions.append(form);detail.append(actions);
 const activity=node('details');activity.append(node('summary','Activity'));const list=node('ol',undefined,'history');for(const event of report.history){const li=node('li',event.action.replaceAll('_',' ')+' · '+event.by);li.append(node('time',new Date(event.at).toLocaleString()));if(event.notes)li.append(node('p',event.notes,'note'));list.append(li);}activity.append(list);detail.append(activity);
}
function appendResearchLinks(container,sources){
 const list=node('ul',undefined,'research-links');
 for(const source of sources){if(typeof source.url!=='string'||!source.url.startsWith('https://'))continue;const row=node('li'),link=node('a',source.title||source.url);link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';row.append(link);list.append(row);}
 container.append(list);
}
function formatSteps(value){
 const text=String(value??'').replaceAll('\\n','\n').trim();
 const markers=[...text.matchAll(/(?:^|\s)([0-9]{1,2})[.)]\s+/g)];
 if(markers.length<2||markers[0][1]!=='1')return text;
 const prefix=text.slice(0,markers[0].index).trim();
 const steps=markers.map((match,index)=>text.slice(match.index+match[0].length,markers[index+1]?.index??text.length).trim().replace(/\s+/g,' ')).filter(Boolean).map((body,index)=>`${index+1}. ${body}`);
 return (prefix?prefix+'\n':'')+steps.join('\n');
}
function draftText(key,value){return ['removal_instructions','replanting_instructions'].includes(key)?formatSteps(value):String(value??'');}
function planFields(form,initial={},report=null,reviewNotes=null){
 if(!report||(initial.id&&initial.work_type!=='restoration'))return legacyPlanFields(form,initial);
 form.append(node('h3','Restoration job'),node('p','One job for removal and approved replanting.','compact-note'));
 const crew=select(form,'Assign ecology team','assigned_team_id',[['','Choose ecology team'],...teams.filter(t=>t.members>0).map(t=>[t.id,t.name])],initial.team_id??initial.assigned_team_id);crew.required=true;
 const due=field(form,'Due date','due_on','input',initial.due_on??'');due.type='date';due.min=today();due.required=true;
 const classified=report.prediction?.predicted_species??report.review?.confirmed_species??'';
 const species=field(form,'Correct scientific name','species_correction','input',initial.confirmed_species||classified);species.maxLength=160;species.parentElement.hidden=true;
 const correction=button('Correct identification',()=>{species.parentElement.hidden=!species.parentElement.hidden;species.required=!species.value.trim();if(!species.parentElement.hidden)species.focus?.();},'text-button');form.append(correction);
 if(!species.value.trim())species.parentElement.hidden=false;
 const approved=check(form,`I confirm ${species.value||'this plant'} is invasive and approve removal at this site.`,initial.confirmed_invasive===true);approved.required=true;
 const panel=node('section',undefined,'restoration-draft-panel');panel.hidden=true;form.append(panel);
 const status=node('p','','compact-note');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 const editor=node('div',undefined,'restoration-document');editor.hidden=true;
 const content=body=>body.innerText??body.textContent;
 const sections={};const labels={removal_instructions:'Removal',replacement_species:'Replacement species',replanting_instructions:'Replanting',review_notes:'Handover note'};
 for(const [key,label] of Object.entries(labels)){
  const heading=node('h4',label);const body=node('div','','draft-paragraph');body.contentEditable='plaintext-only';body.setAttribute('role','textbox');body.setAttribute('aria-label',label);body.setAttribute('aria-multiline','true');body.dataset.placeholder=key==='replacement_species'?'Enter the management-approved replacement species':'Edit this section';
  body.addEventListener('input',()=>{if(reviewNotes&&key==='review_notes')reviewNotes.value=content(body);});
  sections[key]=body;editor.append(heading,body);
 }
 const researchPanel=node('div',undefined,'replacement-research');researchPanel.hidden=true;
 let lastProvider='groq';const retry=button('Retry draft',()=>generate(lastProvider));retry.hidden=true;
 panel.append(status,editor,researchPanel,retry);
 let researchSources=(initial.research_sources??[]).map(url=>({url,title:url})),lastPlanting='';
 function renderResearch(result){
  researchPanel.replaceChildren();researchPanel.hidden=false;researchSources=result.sources??[];
  researchPanel.append(node('h4','Replacement guidance'),node('p',result.research_notice??'Check site conditions before approving a replacement.','compact-note'));
  for(const candidate of result.candidates??[]){
   const card=node('div',undefined,'replacement-candidate');card.append(node('strong',candidate.common_name?`${candidate.common_name} · ${candidate.scientific_name}`:candidate.scientific_name),node('p',candidate.reason),node('p','Check: '+candidate.site_checks,'compact-note'));
   card.append(button('Use '+candidate.scientific_name,()=>{sections.replacement_species.textContent=candidate.scientific_name;
    if(content(sections.replanting_instructions)===lastPlanting){sections.replanting_instructions.textContent=candidate.planting_instructions;lastPlanting=candidate.planting_instructions;}
    status.textContent='Replacement selected. Review its site checks and edit the plan before saving.';
   }));appendResearchLinks(card,candidate.sources??[]);researchPanel.append(card);
  }
  if(result.provider)researchPanel.append(node('p',`Draft provider: ${result.provider==='local'?'Local backup':'Groq'} · ${result.model??''}`,'compact-note'));
  if(result.request_receipt){const usage=result.request_receipt;researchPanel.append(node('p',`Groq requests this action: ${usage.groq_requests}${usage.cached?' (cached draft)':''}. Local requests: ${usage.local_requests??0}`,'compact-note'));const receipt=node('details');receipt.append(node('summary','Usage receipt'),node('p','Pipeline: '+usage.pipeline,'compact-note'),node('p','Action: '+usage.action_id,'compact-note'));if(usage.provider_request_id)receipt.append(node('p','Provider request: '+usage.provider_request_id,'compact-note'));researchPanel.append(receipt);}
  if(researchSources.length){const details=node('details');details.append(node('summary','Research sources'));appendResearchLinks(details,researchSources);researchPanel.append(details);}
 }
 let version=0,controller=null;
 function show(){approved.parentElement.lastChild.textContent=`I confirm ${species.value||'this plant'} is invasive and approve removal at this site.`;panel.hidden=!approved.checked;if(reviewNotes)reviewNotes.parentElement.hidden=true;}
 function cancel(){version++;if(controller)controller.abort();controller=null;if(approved.checked&&editor.hidden){status.textContent='Draft preparation interrupted. Retry to prepare the plan.';retry.hidden=false;}}
 async function generate(provider='groq',previousSnapshot=null){
  cancel();if(!approved.checked)return;lastProvider=provider;const confirmed=species.value.trim();show();retry.hidden=true;
  if(confirmed.length<3){status.textContent='Enter the confirmed species first.';retry.hidden=false;return;}
  const current=version;controller=new AbortController();status.textContent=provider==='local'?'Groq is unavailable. Preparing your draft with local Qwen...':'Preparing your restoration draft...';
  const snapshot=previousSnapshot??Object.fromEntries(Object.entries(sections).map(([key,body])=>[key,content(body)]));
  try{
   const result=await post(`/reports/${report.id}/restoration-draft`,{revision:report.revision,confirmed_species:confirmed,confirmed_invasive:true,...(provider==='local'?{provider:'local'}:{})},{signal:controller.signal});
   if(current!==version||!approved.checked||species.value.trim()!==confirmed||form.hidden||form.isConnected===false)return;
   for(const [key,body] of Object.entries(sections))if(content(body)===snapshot[key])body.textContent=draftText(key,result[key]);
   if(reviewNotes)reviewNotes.value=content(sections.review_notes);
   lastPlanting=content(sections.replanting_instructions);renderResearch(result);
   editor.hidden=false;status.textContent=(provider==='local'?'Local backup draft ready. ':'')+'Review all four sections, including the proposed replacement. Edit directly before saving.';
  }catch(error){
   if(current!==version||error.name==='AbortError'||!approved.checked||species.value.trim()!==confirmed||form.hidden||form.isConnected===false)return;
   if(provider==='groq'&&error.localBackup)return generate('local',snapshot);
   status.textContent=error.message;retry.hidden=false;
  }
 }
 approved.addEventListener('change',()=>{cancel();show();if(approved.checked&&editor.hidden)void generate();});
 species.addEventListener('input',()=>{cancel();approved.checked=false;editor.hidden=true;for(const body of Object.values(sections))body.textContent='';researchPanel.hidden=true;researchSources=[];if(reviewNotes)reviewNotes.value='';show();});
 const initialValues={...initial,review_notes:reviewNotes?.value||initial.notes||''};
 if(initial.removal_instructions||initial.replanting_instructions){for(const [key,body] of Object.entries(sections))body.textContent=draftText(key,initialValues[key]);editor.hidden=false;status.textContent='Review and edit this restoration plan directly.';lastPlanting=content(sections.replanting_instructions);if(researchSources.length)renderResearch({sources:researchSources,candidates:[],research_notice:'Sources retained from the approved plan.'});}
 show();
 const values=()=>{
  if(!approved.checked)throw new Error('Confirm the invasive species first.');
  if(editor.hidden)throw new Error('Wait for the restoration draft, or retry if generation failed.');
  const plan=Object.fromEntries(Object.entries(sections).map(([key,body])=>[key,draftText(key,content(body)).trim()]));
  for(const [key,value] of Object.entries(plan)){if(!value)throw new Error('Complete '+labels[key].toLowerCase()+' in the draft.');if(value.length>(key==='replacement_species'?160:1600))throw new Error(labels[key]+' is too long.');}
  return {work_type:'restoration',assigned_team_id:crew.value,due_on:due.value,priority:initial.priority??'normal',confirmed_species:species.value.trim(),confirmed_invasive:true,removal_instructions:plan.removal_instructions,replacement_species:plan.replacement_species,replanting_instructions:plan.replanting_instructions,notes:plan.review_notes,research_sources:researchSources.map(source=>source.url).slice(0,8)};
 };
 values.cancel=cancel;return values;
}
function legacyPlanFields(form,initial={},report=null,reviewNotes=null){
 const kind={value:initial.id?initial.work_type:'restoration'};form.append(node('h3',kind.value==='restoration'?'Restoration job':workNames[kind.value]),node('p',kind.value==='restoration'?'Remove the invasive plant and replant with the approved replacement.':'Existing assignment · original instructions retained.','compact-note'));
 const crew=select(form,'Assign ecology team','assigned_team_id',[['','Choose ecology team'],...teams.filter(t=>t.members>0).map(t=>[t.id,t.name])],initial.team_id??initial.assigned_team_id);crew.required=true;
 const due=field(form,'Due date','due_on','input',initial.due_on??'');due.type='date';due.min=today();due.required=true;
 const species=field(form,'Confirmed species','confirmed_species','input',initial.confirmed_species??'');species.maxLength=160;
 const approved=check(form,'I confirmed this invasive species and approve removal at this site.',initial.confirmed_invasive===true);
 const removal=text(form,'Approved removal instructions','removal_instructions',initial.removal_instructions);
 const replacement=field(form,'Approved replacement species','replacement_species','input',initial.replacement_species);replacement.maxLength=160;
 const planting=text(form,'Replanting instructions','replanting_instructions',initial.replanting_instructions);
 function adjust(){const removes=['restoration','removal'].includes(kind.value),plants=['restoration','replanting'].includes(kind.value);species.parentElement.hidden=!removes;species.required=removes;approved.parentElement.hidden=!removes;approved.required=removes;removal.parentElement.hidden=!removes;removal.required=removes;replacement.parentElement.hidden=!plants;planting.parentElement.hidden=!plants;replacement.required=planting.required=plants;}
 adjust();
 return ()=>({work_type:kind.value,assigned_team_id:crew.value,due_on:due.value,priority:initial.priority??'normal',confirmed_species:species.value.trim(),confirmed_invasive:['restoration','removal'].includes(kind.value)?approved.checked:null,removal_instructions:['restoration','removal'].includes(kind.value)?removal.value.trim():'',replacement_species:['restoration','replanting'].includes(kind.value)?replacement.value.trim():'',replanting_instructions:['restoration','replanting'].includes(kind.value)?planting.value.trim():''});
}
function drawReview(detail,report){
 detail.append(node('hr',undefined,'divider'),node('h3','Next step'));
 const form=node('form',undefined,'review-form');
 const decision=select(form,'Decision','decision',[['assign','Assign restoration job'],['request_info','Request more information'],['no_action','Close - no work needed']]);
 const work=node('div',undefined,'work-fields');form.append(work);
 const notes=text(form,'Instructions or review note','review_notes');notes.required=true;
 const values=planFields(work,{},report,notes);notes.required=false;
 const err=node('p','','error'),submit=node('button','Save decision','primary');submit.type='submit';form.append(err,submit);
 decision.addEventListener('change',()=>{values.cancel?.();work.hidden=decision.value!=='assign';notes.parentElement.hidden=decision.value==='assign';notes.required=work.hidden;for(const input of work.querySelectorAll('input,select,textarea'))input.disabled=work.hidden;});
 form.addEventListener('submit',async e=>{e.preventDefault();submit.disabled=true;try{await post(`/reports/${report.id}/review`,{revision:report.revision,decision:decision.value,notes:notes.value.trim(),...(decision.value==='assign'?values():{})});feedback('Decision saved.');await loadReports();await loadNotices();}catch(f){err.textContent=f.message;submit.disabled=false;}});detail.append(form);
}
function drawWork(detail,report,work){
 const card=node('section',undefined,'visit');card.append(node('h3',workNames[work.work_type]??work.work_type),badge(work.status),fact('Ecology team',work.team_name),fact('Due',work.due_on??'Date needs review'),node('p',work.notes,'note'));
 if(work.overdue)card.append(node('p','Overdue','overdue'));
 if(work.legacy)card.append(node('p','Earlier work type. Preserve this record; cancel the active case and reopen it to create a new work step.','compact-note'));
 if(work.requires_reassignment)card.append(node('p','This older job needs an explicit reassignment to an ecology team.','error'));
 for(const [label,key] of [['Confirmed species','confirmed_species'],['Approved removal instructions','removal_instructions'],['Approved replacement','replacement_species'],['Replanting instructions','replanting_instructions']])if(work[key])card.append(fact(label,draftText(key,work[key])));
 if(work.research_sources?.length){const references=node('details');references.append(node('summary','Plan research sources'));appendResearchLinks(references,work.research_sources.map(url=>({url,title:url})));card.append(references);}
 for(const [index,c] of work.completions.entries()){
  const evidence=node('div',undefined,'evidence-record');evidence.append(node('h3',`Evidence ${index+1}`),fact('Visit date',c.observed_on),node('p',c.notes,'note'));
  for(const [label,key] of [['Plant identified by ecology team','suggested_species'],['Recommended next step','recommended_action'],['Suggested removal method','removal_recommendation'],['Suggested replacement','replacement_recommendation'],['Removed on','removed_on']])if(c[key])evidence.append(fact(label,c[key]));
  if(c.planted_on)evidence.append(fact('Planted',`${c.quantity} Ã— ${c.planted_species} · ${c.planted_on}`));
  if(c.planting_pending_reason)evidence.append(fact('Replanting pending',c.planting_pending_reason));
  if(c.regrowth)evidence.append(fact('Regrowth',c.regrowth));if(c.checked_count!=null)evidence.append(fact('Plants surviving',`${c.surviving_count} / ${c.checked_count}`));
  evidence.append(node('p',`${c.submitted_by} · ${new Date(c.submitted_at).toLocaleString()}`,'compact-note'));const labels={};if(work.work_type==='restoration')for(const [i,id] of (c.photo_ids??[]).entries())labels[id]=c.stage==='both'?(i===0?'After removal':'After replanting'):c.stage==='removal'?'After removal':'After replanting';photos(evidence,report,c.photo_ids??[],labels);card.append(evidence);
 }
 if(work.verification)card.append(fact('Management review',work.verification.notes));
 if(work.status==='awaiting_verification'&&!work.legacy&&!work.requires_reassignment){
  const form=node('form',undefined,'review-form');form.append(node('h3','Review evidence'));
  const notes=text(form,'Review note','verification_notes');notes.required=true;
  const more=work.work_type==='restoration'?{checked:false,addEventListener:()=>{}}:check(form,'More work needed');const next=node('div',undefined,'work-fields');next.hidden=true;form.append(next);
  const latest=work.completions.at(-1);const values=work.work_type==='restoration'?()=>({}):planFields(next,{work_type:latest?.recommended_action==='replanting'?'replanting':latest?.recommended_action==='removal'?'removal':'inspection',team_id:work.team_id,confirmed_species:latest?.suggested_species??work.confirmed_species,removal_instructions:latest?.removal_recommendation??'',replacement_species:latest?.replacement_recommendation??work.replacement_species});
  const err=node('p','','error');const approve=node('button','Approve and close','primary');approve.type='submit';approve.value='accept';approve.name='decision';
  const changes=node('button','Request changes','secondary');changes.type='submit';changes.value='corrections';changes.name='decision';changes.formNoValidate=true;form.append(err,approve,changes);
  function toggle(){next.hidden=!more.checked;for(const input of next.querySelectorAll('input,select,textarea'))input.disabled=!more.checked;approve.textContent=more.checked?'Approve and assign next step':'Approve and close';}more.addEventListener('change',toggle);toggle();
  form.addEventListener('submit',async e=>{e.preventDefault();const decision=e.submitter?.value??'accept';if(!notes.value.trim()){err.textContent='Add a review note.';return;}approve.disabled=changes.disabled=true;try{const body={revision:work.revision,decision,notes:notes.value.trim()};if(decision==='accept'&&more.checked)body.next_plan={revision:report.revision,decision:'assign',notes:notes.value.trim(),...values()};await post(`/reports/${report.id}/work/${work.id}/verify`,body);feedback(decision==='corrections'?'Changes requested.':'Evidence approved.');await loadReports();await loadNotices();}catch(f){err.textContent=f.message;approve.disabled=changes.disabled=false;}});card.append(form);
 }
 if(!work.legacy&&['assigned','accepted','in_progress','blocked','correction_requested'].includes(work.status)){
  const revise=node('details');revise.append(node('summary','Change instructions or ecology team'));const form=node('form');const values=planFields(form,work,report),note=text(form,'Reason for change','change_reason');note.required=true;const err=node('p','','error'),submit=node('button','Save changes','secondary');submit.type='submit';form.append(err,submit);
  form.addEventListener('submit',async e=>{e.preventDefault();submit.disabled=true;try{const plan=values();const handover=plan.notes?plan.notes+'\n\nChange reason: '+note.value.trim():note.value.trim();if(handover.length>1600)throw new Error('Shorten the handover note and change reason to 1600 characters.');await post(`/reports/${report.id}/work/${work.id}/revise`,{revision:work.revision,decision:'assign',...plan,notes:handover});feedback('Job updated.');await loadReports();}catch(f){err.textContent=f.message;submit.disabled=false;}});revise.append(form);card.append(revise);
 }
 const history=node('details');history.append(node('summary','Job history'));for(const event of work.history)history.append(node('p',`${event.action.replaceAll('_',' ')} · ${event.by??'System'}${event.notes?' · '+event.notes:''}`,'compact-note'));card.append(history);
 if(['verified','cancelled'].includes(work.status)){const past=node('details');past.append(node('summary',`${workNames[work.work_type]} · ${work.status} · ${work.due_on??'Earlier job'}`),card);detail.append(past);}else detail.append(card);
}
async function showView(next){if(currentUser?.must_change_password)next='password';view=next;$('#reports-panel').hidden=next!=='reports';$('#manage-panel').hidden=next==='reports';for(const b of $('#views').querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.dataset.view===next));const panel=$('#manage-panel');panel.replaceChildren();if(next==='updates'){drawNotices();return;}if(next==='password'){drawPassword(panel);return;}if(next==='staff')await drawAdmin(panel);if(next==='backups')await drawBackups(panel);}
function drawNotices(){const panel=$('#manage-panel');panel.replaceChildren(node('h2','Updates'));if(!notices.length)panel.append(node('p','No updates yet.'));for(const notice of notices){const row=node('div',undefined,'notice');row.append(node('p',notice.message),node('time',new Date(notice.created_at).toLocaleString(),'compact-note'));if(!notice.read_at)row.append(button('Mark as read',async()=>{await post(`/notifications/${notice.id}/read`,{});await loadNotices();},'text-button'));if(notice.report_id)row.append(button('Open report',()=>{selectedId=notice.report_id;showView('reports');drawInbox();const report=reports.find(r=>r.id===selectedId);if(report)drawDetail(report);},'text-button'));panel.append(row);}}
function drawPassword(panel){panel.append(node('h2','Change password'));const form=node('form',undefined,'admin-form login');const current=field(form,'Current password','current_password');current.type='password';current.autocomplete='current-password';const next=field(form,'New password','new_password');next.type='password';next.minLength=10;next.autocomplete='new-password';const confirm=field(form,'Confirm new password','confirm_password');confirm.type='password';for(const input of [current,next,confirm])input.required=true;const err=node('p','','error');const submit=node('button','Save password','primary');submit.type='submit';form.append(err,submit);form.addEventListener('submit',async e=>{e.preventDefault();if(next.value!==confirm.value){err.textContent='Passwords do not match.';return;}submit.disabled=true;try{await post('/auth/password',{current_password:current.value,new_password:next.value});showLogin(true);}catch(f){err.textContent=f.message;submit.disabled=false;}});panel.append(form);}
function temporary(panel,value){const box=node('div',undefined,'temporary-password');box.setAttribute('role','status');box.append(node('h3','Temporary password'),node('p','Copy it now and share it privately with this staff member. They must change it at sign-in.'));const input=node('input');input.readOnly=true;input.value=value;input.setAttribute('aria-label','Temporary password');box.append(input,button('Hide password',()=>box.remove(),'text-button'));panel.prepend(box);}
async function drawAdmin(panel){panel.append(node('h2','Staff & sites','manage-title'));let users,catalog;try{[users,catalog]=await Promise.all([api('/admin/users'),api('/admin/catalog')]);}catch(e){panel.append(node('p',e.message,'error'));return;}const grid=node('div',undefined,'admin-grid');panel.append(grid);const staff=node('section',undefined,'admin-card');staff.append(node('h3','Staff accounts'));const form=node('form',undefined,'admin-form');const name=field(form,'Staff name','display_name'),username=field(form,'Username','username');name.required=username.required=true;username.pattern='[a-zA-Z0-9_.-]+';const role=select(form,'Role','role',[['ground','Ground team'],['ecology','Ecology field team'],['management','Ecology management']]);const team=select(form,'Team','team_id',[['','Choose team'],...catalog.teams.filter(t=>t.active&&t.role==='ground').map(t=>[t.id,t.name])]);team.required=true;role.addEventListener('change',()=>{team.replaceChildren();option(team,'','Choose team');for(const t of catalog.teams.filter(t=>t.active&&t.role===role.value))option(team,t.id,t.name);team.required=role.value!=='management';team.disabled=role.value==='management';});const err=node('p','','error');const add=node('button','Create staff account','primary');add.type='submit';form.append(err,add);form.addEventListener('submit',async e=>{e.preventDefault();add.disabled=true;try{const result=await post('/admin/users',{username:username.value.trim(),display_name:name.value.trim(),role:role.value,team_id:role.value==='management'?null:team.value});await showView('staff');temporary($('#manage-panel'),result.temporary_password);}catch(f){err.textContent=f.message;add.disabled=false;}});staff.append(form);
 for(const user of users){const row=node('div',undefined,'staff-row');row.append(node('strong',user.display_name),node('p',`${user.username} · ${user.role==='management'?'Ecology management':catalog.teams.find(t=>t.id===user.team_id)?.name??'Ground team'} · ${user.active?'Active':'Disabled'}`,'compact-note'));const actions=node('div',undefined,'inline-actions');actions.append(button('Reset password',async()=>{const result=await post(`/admin/users/${user.id}/reset`,{});temporary(panel,result.temporary_password);},'text-button'),button(user.active?'Disable':'Enable',async()=>{await post(`/admin/users/${user.id}/active`,{active:!user.active});await showView('staff');},'text-button'));row.append(actions);staff.append(row);}grid.append(staff);
 const lists=node('section',undefined,'admin-card');lists.append(node('h3','Teams, sites & blocks'));for(const kind of ['teams','sites','blocks']){const section=node('details');section.open=true;section.append(node('summary',kind[0].toUpperCase()+kind.slice(1)));const f=node('form',undefined,'admin-form');const n=field(f,'New '+kind.slice(0,-1)+' name',kind+'_name');n.required=true;n.maxLength=100;const teamRole=kind==='teams'?select(f,'Team role','team_role',[['ecology','Ecology field team'],['ground','Ground team']]):null;const site=kind==='blocks'?select(f,'Site for block','block_site',[['','Choose site'],...catalog.sites.filter(s=>s.active).map(s=>[s.id,s.name])]):null;if(site)site.required=true;const error=node('p','','error');const add=node('button','Add '+kind.slice(0,-1),'secondary');add.type='submit';f.append(error,add);f.addEventListener('submit',async e=>{e.preventDefault();add.disabled=true;try{await post('/admin/catalog/'+kind,{name:n.value.trim(),site_id:site?.value??null,...(teamRole?{role:teamRole.value}:{})});await showView('staff');}catch(f){error.textContent=f.message;add.disabled=false;}});section.append(f);for(const item of catalog[kind]){const row=node('div',undefined,'staff-row');row.append(node('p',item.name+(kind==='teams'?' · '+item.role:'')+(kind==='blocks'?' · '+catalog.sites.find(s=>s.id===item.site_id)?.name:'')),button(item.active?'Disable':'Enable',async()=>{await post(`/admin/catalog/${kind}/${item.id}/active`,{active:!item.active});await showView('staff');},'text-button'));section.append(row);}lists.append(section);}grid.append(lists);}
async function drawBackups(panel){panel.append(node('h2','Backups'),node('p','Includes staff accounts, private photos and report history. Store downloaded copies securely.','muted'));panel.append(button('Create backup',async()=>{await post('/admin/backups',{});await showView('backups');},'primary'));try{const list=await api('/admin/backups');for(const item of list){const row=node('div',undefined,'staff-row');const link=node('a',item.name);link.href='/admin/backups/'+encodeURIComponent(item.name);link.download=item.name;row.append(link,node('span',`${(item.bytes/1024/1024).toFixed(1)} MB`,'compact-note'));panel.append(row);}panel.append(node('p','Daily backups run while the backend is running. Restoration is an offline operator step; see the pilot guide.','compact-note'));}catch(e){panel.append(node('p',e.message,'error'));}}
$('#signout').addEventListener('click',async()=>{try{await api('/auth/logout',{method:'POST'});showLogin(true);selectedId=undefined;}catch(e){feedback(e.message,true);}});
$('#password-button').addEventListener('click',()=>{void showView('password');});
$('#refresh').addEventListener('click',()=>{void loadReports();void loadNotices();});
$('#filters').addEventListener('click',e=>{const b=e.target.closest('[data-filter]');if(!b)return;filter=b.dataset.filter;for(const item of $('#filters').querySelectorAll('button'))item.setAttribute('aria-pressed',String(item===b));drawInbox();});
$('#views').addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(b)void showView(b.dataset.view).catch(f=>feedback(f.message,true));});
setInterval(()=>{void loadNotices();},30000);
function openWorkspace(){$('#entry-message').textContent='Opening management...';$('#entry-retry').hidden=true;api('/auth/me').then(enter).catch(error=>{if(error.status===401)return;$('#entry-panel').hidden=false;$('#entry-message').textContent=error.message||'Could not open management. Please retry.';$('#entry-retry').hidden=false;});}
$('#entry-retry').addEventListener('click',openWorkspace);
$('#entry-signin').addEventListener('click',event=>{event.preventDefault();showLogin(true);});
openWorkspace();
