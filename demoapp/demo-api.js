/* Browser-only simulation. Never contacts the BioGuard backend or AI providers. */
(() => {
 const realFetch=window.fetch.bind(window), NativeDate=window.Date;
 const KEY='bioguard-judge-demo-v1';
 const blocksPromise=realFetch('/officer-assets/elmina-inspection-blocks.geojson').then(r=>r.json()).then(data=>window.demoBlocks=data);
 const initial=()=>({user:null,reports:[],offset:0,notices:[]});
 let state;try{state=JSON.parse(localStorage.getItem(KEY))||initial();}catch{state=initial();}
 class DemoDate extends NativeDate{constructor(...args){super(...(args.length?args:[NativeDate.now()+(state.offset||0)]));}static now(){return NativeDate.now()+(state.offset||0);}}
 window.Date=DemoDate;
 const day=()=>new DemoDate(DemoDate.now()+8*3600000).toISOString().slice(0,10),now=()=>new DemoDate().toISOString();
 const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(state));}catch{throw Error('Demo storage is full. Reset the demo to continue.');}window.dispatchEvent(new Event('bioguard:demo-state'));};
 const uid=()=>crypto.randomUUID(),users={grounds:{id:'demo-ground',username:'grounds',display_name:'Ground team',role:'ground',team_id:'ground-team'},management:{id:'demo-manager',username:'management',display_name:'Ecology Management',role:'management',team_id:null},ecology:{id:'demo-ecology',username:'ecology',display_name:'Ecology field team',role:'ecology',team_id:'ecology-team'}};
 const teams=[{id:'ecology-team',name:'Ecology field team',role:'ecology',members:1,active:true},{id:'ground-team',name:'Ground team',role:'ground',members:1,active:true}];
 const prediction={predicted_species:'Mimosa pudica',common_name:'Touch-me-not',sdp_listed_invasive:true,confidence:.98,uncertain_identification:false,known_class_scope_only:true,supported_species_count:9};
 const source={title:'Queensland Government - Common sensitive plant',url:'https://www.business.qld.gov.au/industries/farms-fishing-forestry/agriculture/biosecurity/plants/invasive/other/common-sensitive-plant',excerpt:'Spread mainly by seeds clinging to humans and animals.'};
 const brief='Inspect vegetation around the reported Mimosa pudica, including vegetated path edges in the highlighted block where present. Photograph and pin additional suspected plants; record none if no additional plants are observed. Demonstration wording, pending Ecology review.';
 function inspection(r,text=brief){return {brief:text,species:'Mimosa pudica',location:{kind:'land',block_ids:[block(r)]},point:{latitude:r.latitude,longitude:r.longitude,map_id:r.map_id,location_mode:r.location_mode},source,approved_by:'Ecology Management',approved_at:now()};}
 function block(r){try{return window.BioGuardBlocks?.classify(window.demoBlocks,[r.longitude,r.latitude]).features?.[0]?.properties?.block_id||'Reported block';}catch{return 'Reported block';}}
 let dbPromise;
 function db(){return dbPromise??=new Promise((resolve,reject)=>{const q=indexedDB.open('bioguard-judge-demo-photos',1);q.onupgradeneeded=()=>q.result.createObjectStore('photos');q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(q.error);});}
 async function putPhoto(r,file,kind,workId){if(!(file instanceof Blob))return null;const id=uid(),database=await db();await new Promise((res,rej)=>{const t=database.transaction('photos','readwrite');t.objectStore('photos').put(file,id);t.oncomplete=res;t.onerror=()=>rej(t.error);});r.photos.push({id,kind,work_id:workId||null,url:`/reports/${r.id}/photos/${id}`});return id;}
 async function getPhoto(id){const database=await db();return new Promise((res,rej)=>{const q=database.transaction('photos').objectStore('photos').get(id);q.onsuccess=()=>res(q.result);q.onerror=()=>rej(q.error);});}
 function event(r,action,notes=''){r.revision++;r.updated_at=now();r.history.push({at:now(),action,by:state.user?.display_name||'Demo',notes});state.notices.unshift({id:uid(),report_id:r.id,message:action.replaceAll('_',' '),created_at:now(),read_at:null});}
 function hydrate(r){for(const w of r.work_items){w.overdue=w.due_on<day()&&!['verified','cancelled','awaiting_verification'].includes(w.status);w.inspection_open_today=!w.followup_of||w.due_on===day();}r.completion_pdf_available=r.status==='completed'&&r.work_items.some(w=>w.followup_of&&w.status==='verified');return r;}
 function newWork(r,plan){const w={...plan,id:uid(),report_id:r.id,team_id:plan.assigned_team_id||'ecology-team',team_name:'Ecology field team',revision:1,status:'assigned',legacy:false,requires_reassignment:false,overdue:false,completions:[],inspections:[],verification:null,history:[{at:now(),action:'assigned',by:'Ecology Management'}]};if(plan.inspection_brief)w.inspection=inspection(r,plan.inspection_brief);r.work_items.push(w);r.assigned_team_id=w.team_id;return w;}
 const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
 const fail=(message,status=422)=>json({detail:message},status);
 window.BioGuardDemo={get state(){return state;},day,realFetch,async login(role){while(window.__demoPending)await new Promise(resolve=>setTimeout(resolve,25));state.user=users[role];save();location.href=role==='management'?'/officer/':'/';},async reset(){state=initial();for(const key of Object.keys(localStorage)){if(key===KEY||key.startsWith('bioguard.draft.v1.demo-')||key.includes('bioguard')&&key.includes('demo-'))localStorage.removeItem(key);}const database=await db();await new Promise(resolve=>{const t=database.transaction('photos','readwrite');t.objectStore('photos').clear();t.oncomplete=resolve;});save();location.href='/';},advance(){const w=state.reports.flatMap(r=>r.work_items).find(w=>w.followup_of&&!['verified','cancelled'].includes(w.status));if(!w)return;state.offset=NativeDate.parse(w.due_on+'T12:00:00+08:00')-NativeDate.now();save();location.reload();}};
 window.fetch=async(input,options={})=>{
  const url=new URL(typeof input==='string'?input:input instanceof URL?input.href:input.url,location.href),p=url.pathname;
  if(url.origin!==location.origin||!/^\/(auth|identify|reports|teams|catalog|notifications|admin|health)(\/|$)/.test(p))return realFetch(input,options);
  try{
   const req=new Request(url,input instanceof Request?input:options),method=req.method;
   let body={},form;
   if(method!=='GET'&&method!=='HEAD'){if((req.headers.get('content-type')||'').includes('multipart/form-data')){form=await req.formData();body=JSON.parse(form.get('details')||'{}');}else if((req.headers.get('content-type')||'').includes('json'))body=await req.json();}
   if(p==='/auth/login'){if(!users[body.username]||body.password!=='123')return fail('Use grounds, management or ecology with password 123.',401);state.user=users[body.username];save();return json({user:state.user,token:'demo-token'});}
   if(p==='/auth/logout'){state.user=null;save();return new Response(null,{status:204});}
   if(p==='/auth/password')return fail('Demo account passwords are fixed at 123. No real account is changed.');
   if(p.startsWith('/admin/')&&method!=='GET')return fail('Staff and backup changes are not part of this frontend walkthrough. No server is connected.');
   if(p==='/auth/me')return state.user?json(state.user):fail('Sign in to the demo.',401);
   if(p==='/health')return json({identification_available:true,supported_species_count:9,demo:true});
   if(!state.user)return fail('Sign in to the demo.',401);
   if(p==='/identify')return json(prediction);
   if(p==='/teams')return json(teams.filter(t=>t.role==='ecology'));
   if(p==='/catalog'||p==='/admin/catalog')return json({teams,sites:[],blocks:[]});
   if(p==='/admin/users')return json(Object.values(users).map(u=>({...u,active:true})));
   if(p==='/admin/backups')return json([]);
   if(p==='/notifications')return json(state.notices);
   if(p.startsWith('/notifications/')){const n=state.notices.find(n=>n.id===p.split('/')[2]);if(n)n.read_at=now();save();return new Response(null,{status:204});}
   if(p==='/reports'&&method==='GET')return json(state.reports.map(hydrate));
   if(p==='/reports'&&method==='POST'){
    const previous=state.reports.find(r=>r.request_key===body.request_key);if(previous)return json(hydrate(previous),201);
    const r={...body,id:uid(),reference:'BG-DEMO-'+String(state.reports.length+1).padStart(3,'0'),status:'submitted',revision:1,reporter_name:'Ground team',reporter_id:'demo-ground',assigned_team_id:null,prediction:body.identify_requested===false?null:prediction,created_at:now(),review:null,photos:[],work_items:[],history:[]};await putPhoto(r,form.get('photo'),'identification');await putPhoto(r,form.get('overview'),'overview');state.reports.unshift(r);event(r,'submitted',body.notes);save();return json(hydrate(r),201);
   }
   const parts=p.split('/'),r=state.reports.find(r=>r.id===parts[2]);if(!r)return fail('Demo report not found.',404);
   if(parts[3]==='photos'){const file=await getPhoto(parts[4]);return file?new Response(file,{headers:{'Content-Type':file.type}}):fail('Photo missing.',404);}
   if(parts.length===3)return json(hydrate(r));
   if(parts[3]==='duplicates')return json([]);
   if(['inspection-draft','inspection-guidance'].includes(parts[3])){await blocksPromise;const guide={...inspection(r),supported:true,actions:[brief],variables:{used_path_nearby:'unknown'}};return json({inspection:guide,inspection_brief:brief,template_only:false,provider:'demo',model:'Prewritten example',sources:[source]});}
   if(parts[3]==='restoration-draft')return json({removal_instructions:'1. Ecology checks the management-confirmed plant and site conditions.\n2. Follow the site-approved removal and disposal method, taking care to prevent seed movement.\n3. Record the removal date and an after-removal photo.\nIllustrative demo plan; this is not field treatment advice.',replacement_species:'Site-approved native groundcover (demo placeholder)',replanting_instructions:'1. Ecology confirms a suitable locally approved replacement against the actual light, soil and moisture conditions.\n2. Prepare the cleared site and plant using the approved nursery guidance.\n3. Record species, quantity, planting date and a current photo.\nIllustrative demo plan; replacement selection requires site review.',review_notes:'Demonstration handover: remove the reviewed invasive plant, complete approved replacement planting and retain evidence. A follow-up is scheduled after Management accepts completed restoration.',sources:[source],candidates:[],research_notice:'Prewritten demonstration content. No AI request or live replacement research is performed.',provider:'demo',model:'Prewritten demonstration',request_receipt:{groq_requests:0,local_requests:0,cached:true,action_id:'DEMO',pipeline:'frontend-demo'}});
   if(parts[3]==='review'){
    if(state.user.role!=='management')return fail('Switch to Management.',403);
    r.review={...body,reviewer_name:state.user.display_name,assigned_team_name:'Ecology field team',reviewed_at:now()};
    if(body.decision==='assign'){newWork(r,body);r.status='assigned';}else r.status=body.decision==='request_info'?'needs_info':'closed';event(r,'management_review',body.notes);save();return json(hydrate(r));
   }
   if(parts[3]==='completion.pdf')return new Response(window.demoPdf(r),{headers:{'Content-Type':'application/pdf'}});
   if(parts[3]==='work'){
    const w=r.work_items.find(w=>w.id===parts[4]);if(!w)return fail('Demo job not found.',404);const action=parts[5];
    if(['progress','complete','inspection'].includes(action)&&parts[6]!=='review'&&w.followup_of&&w.due_on!==day())return fail('This visit opens on '+w.due_on+'. Use the demo date button to advance.');
    if(action==='progress'){w.status=body.action==='accept'?'accepted':body.action==='blocked'?'blocked':'in_progress';w.revision++;event(r,'job_'+w.status,body.notes);}
    if(action==='inspection'&&parts[6]!=='review'){
     const existing=w.inspections.find(i=>i.request_key===body.request_key);if(existing)return json(hydrate(r));
     const item={...body,id:uid(),species:w.confirmed_species,submitted_at:now(),submitted_by:state.user.display_name,review_status:'pending',photo_ids:[]};for(let i=0;i<(body.findings||[]).length;i++){const id=await putPhoto(r,form.get('photo_'+i),'inspection_finding',w.id);item.findings[i].photo_id=id;item.photo_ids.push(id);}w.inspections.push(item);w.revision++;event(r,'inspection_submitted',body.notes);
    }
    if(action==='inspection'&&parts[6]==='review'){const item=w.inspections.find(i=>i.id===body.inspection_id);if(item)Object.assign(item,{review_status:'reviewed',review_notes:body.notes,reviewed_by:state.user.display_name});w.revision++;event(r,'inspection_reviewed',body.notes);}
    if(action==='complete'){
     if(w.completions.some(c=>c.request_key===body.request_key))return json(hydrate(r));
     if(w.followup_of&&body.observed_on!==w.due_on)return fail('The inspection date must match the scheduled date.');
     const item={...body,submitted_by:state.user.display_name,submitted_at:now(),photo_ids:[]};for(const name of ['photo','overview']){const id=await putPhoto(r,form.get(name),'work_evidence',w.id);if(id)item.photo_ids.push(id);}w.completions.push(item);w.status=w.work_type==='restoration'&&body.stage==='removal'?'in_progress':'awaiting_verification';r.status=w.status;w.revision++;event(r,'evidence_submitted',body.notes);
    }
    if(action==='verify'){
     if(state.user.role!=='management')return fail('Switch to Management.',403);
     if(body.decision==='accept'&&w.inspections.some(i=>i.review_status!=='reviewed'))return fail('Review the inspection result above before approving restoration.');
     if(body.decision==='accept'&&w.work_type==='restoration'&&!w.completions.at(-1)?.planted_on)return fail('Finish replanting before approval.');
     if(body.decision==='accept'&&w.followup_of&&!body.next_plan){const c=w.completions.at(-1);if(!c||c.regrowth!=='no'||c.replacement_condition!=='healthy'||c.other_invasive!=='no')return fail('Assign corrective work for findings that need further action.');}
     if(body.decision==='corrections'){w.status='correction_requested';r.status='assigned';}
     else{w.status='verified';w.verification={...body,verified_by:state.user.display_name,verified_at:now()};
      if(w.work_type==='restoration'){
       const last=w.completions.at(-1);if(!last?.planted_on)return fail('Finish replanting before approval.');
       const due=new DemoDate(last.planted_on+'T12:00:00Z');due.setUTCDate(due.getUTCDate()+14);
       newWork(r,{work_type:'inspection',followup_of:w.id,previous_work_id:w.id,due_on:body.next_visit_on||due.toISOString().slice(0,10),confirmed_species:w.confirmed_species,replacement_species:w.replacement_species,replanting_instructions:w.replanting_instructions,notes:'Follow-up: check invasive regrowth and replacement planting. Submit photos and findings for Management review.',restoration_snapshot:{planted_on:last.planted_on,planted_species:last.planted_species,quantity:last.quantity,completions:w.completions,point:{latitude:r.latitude,longitude:r.longitude},inspection:w.inspection}});r.status='follow_up';
      }else if(body.next_plan){newWork(r,{...body.next_plan,previous_work_id:w.id,...(w.followup_of&&body.next_plan.work_type==='inspection'?{followup_of:w.followup_of,restoration_snapshot:w.restoration_snapshot}:{})});r.status='assigned';}else if(w.followup_of){const c=w.completions.at(-1);if(c.regrowth!=='no'||c.replacement_condition!=='healthy'||c.other_invasive!=='no'){w.status='awaiting_verification';return fail('Assign corrective work for findings that need further action.');}r.status='completed';}else r.status='completed';
     }w.revision++;event(r,'verification_'+body.decision,body.notes);
    }
    if(action==='revise'){Object.assign(w,body,{team_id:body.assigned_team_id,status:'assigned',revision:w.revision+1});event(r,'work_revised',body.notes);}
    save();return json(hydrate(r));
   }
   return fail('This administrative action is outside the guided demo. Use the report-to-restoration walkthrough.',422);
  }catch(error){console.error('Demo simulation:',error);return fail('Demo could not complete this step: '+error.message);}
 };
 const simulatedFetch=window.fetch;window.fetch=async(input,options={})=>{const method=(options.method||(input instanceof Request?input.method:'GET')).toUpperCase();const writing=method!=='GET'&&method!=='HEAD';if(writing)window.__demoPending=(window.__demoPending||0)+1;try{return await simulatedFetch(input,options);}finally{if(writing)window.__demoPending--;}};
 // Client-generated, illustrative PDF summary; production exports contain the complete evidence appendix.
 window.demoPdf=r=>{
  const escape=s=>String(s).replace(/[^\x20-\x7e]/g,' ').replace(/[\\()]/g,'\\$&');
  const lines=['BioGuard - DEMONSTRATION ONLY','Restoration completion summary',r.reference,r.site,r.landmark,'Status: '+r.status,'Species: Mimosa pudica','Location: '+r.latitude+', '+r.longitude,...r.work_items.flatMap(w=>[w.followup_of?'Follow-up inspection':'Restoration','Team: '+w.team_name,'Scheduled: '+w.due_on,'Status: '+w.status,'Reviewed by: '+(w.verification?.verified_by||'Pending')]),'Sample workflow. No live AI or field work was performed.','The production PDF also includes the full photo evidence appendix.'];
  const content='0.14 0.36 0.26 rg BT /F1 14 Tf 45 790 Td '+lines.map((s,i)=>(i?'0 -25 Td ':'')+'('+escape(s)+') Tj').join('\n')+' ET';
  const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',`<< /Length ${content.length} >>\nstream\n${content}\nendstream`];let out='%PDF-1.4\n',offsets=[0];objects.forEach((o,i)=>{offsets.push(out.length);out+=`${i+1} 0 obj\n${o}\nendobj\n`;});const xref=out.length;out+='xref\n0 6\n0000000000 65535 f \n'+offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')+`trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;return out;
 };
 document.addEventListener('click',async e=>{const a=e.target.closest?.('a[href$="completion.pdf"]');if(!a)return;e.preventDefault();const r=state.reports.find(r=>a.pathname.includes(r.id));if(r?.status!=='completed')return;const url=URL.createObjectURL(new Blob([window.demoPdf(r)],{type:'application/pdf'})),link=document.createElement('a');link.href=url;link.download='BioGuard-DEMO-completion.pdf';link.click();setTimeout(()=>URL.revokeObjectURL(url),3000);});
})();
