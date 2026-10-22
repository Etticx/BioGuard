(() => {
 const demo=window.BioGuardDemo;
 function button(label,action){const b=document.createElement('button');b.textContent=label;b.type='button';b.addEventListener('click',action);return b;}
 function fill(input,value){const proto=input.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:input.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));}
 function fillFields(){
  for(const input of document.querySelectorAll('input,textarea,select')){
   const label=((input.getAttribute('aria-label')||'')+' '+(input.name||'')+' '+(input.closest('label')?.textContent||'')).toLowerCase();
   if(input.type==='file'||input.type==='checkbox'||input.type==='password'||input.disabled)continue;
   if(input.tagName==='SELECT'){if(input.name==='assigned_team_id')fill(input,'ecology-team');continue;}
   if(label.includes('site or block'))fill(input,'Near Elmina Lake');
   else if(label.includes('nearby landmark'))fill(input,'Vegetated path beside Elmina Lakeside Mall');
   else if(label.includes('username'))fill(input,'grounds');
   else if(label.includes('quantity'))fill(input,'3');
   else if(input.type==='date'||label.includes('yyyy-mm-dd')){if(!input.value)fill(input,demo.day());}
   else if(label.includes('note')||label.includes('problem')||input.tagName==='TEXTAREA')fill(input,'Demo: checked the assigned location and recorded the requested work and photo evidence.');
  }
  for(const input of document.querySelectorAll('input[type=password]'))fill(input,'123');
 }
 // Feed a local sample file through the original Expo image picker, using its normal change event.
 const originalClick=HTMLInputElement.prototype.click;
 HTMLInputElement.prototype.click=function(){if(this.type!=='file'||!window.__demoSamplePhoto)return originalClick.call(this);window.__demoSamplePhoto=false;const input=this;demo.realFetch('/samples/mimosa.jpg').then(r=>r.blob()).then(blob=>{const transfer=new DataTransfer();transfer.items.add(new File([blob],'demo-mimosa.jpg',{type:'image/jpeg'}));input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));}).catch(()=>originalClick.call(input));};
 const originalDispatch=HTMLInputElement.prototype.dispatchEvent;
 HTMLInputElement.prototype.dispatchEvent=function(event){if(this.type==='file'&&event.type==='click'&&window.__demoSamplePhoto){this.click();return true;}return originalDispatch.call(this,event);};
 let sampleStep=0;
 function sample(){
  const candidates=[...document.querySelectorAll('button,[role=button]')].filter(b=>!b.closest('#demo-toolbar')&&!b.disabled&&b.offsetParent!==null);
  const choices=candidates.filter(b=>/choose.*(photo|image)/i.test(b.textContent));const target=choices[sampleStep%Math.max(choices.length,1)];if(target)sampleStep++;
  if(!target){document.getElementById('demo-hint').textContent='Open a photo selection screen first. This fills the next visible Choose photo action.';return;}
  window.__demoSamplePhoto=true;target.click();
 }
 function guidance(){
  const r=demo.state.reports[0],jobs=r?.work_items||[],last=jobs.at(-1);
  if(!demo.state.user)return 'Start: sign in as grounds / 123. The same password works for management and ecology.';
  if(!r)return 'Grounds: use the sample photo, identify it, then report it. Fill the site details and pin its position on the map.';
  if(r.status==='completed')return 'Finished: Management accepted the follow-up and closed the case. Download the demo PDF or reset to start again.';
  if(!jobs.length)return 'Next: switch to Management, open the report, review the guidance, choose the Ecology team/date and approve the illustrated restoration plan.';
  if(last.status==='awaiting_verification')return last.followup_of?'Next: Management reviews the follow-up findings and approves closure.':'Next: Management marks the inspection result reviewed, then approves restoration to schedule the follow-up.';
  if(last.followup_of)return last.due_on!==demo.day()?'Follow-up is scheduled for '+last.due_on+'. View it in Upcoming inspections; use Advance to inspection date to unlock the simulated visit.':'Ecology: open Upcoming inspections, accept the visit, answer Not observed / Healthy / No, add a photo and submit. Then switch to Management for closure.';
  return 'Ecology: accept the job, record the initial inspection result, then record removal and replanting dates, quantity and two evidence photos. Send to Management.';
 }
 function mount(){
  const bar=document.createElement('aside');bar.id='demo-toolbar';bar.setAttribute('aria-label','Demo walkthrough controls');
  const title=document.createElement('div');title.className='demo-title';title.textContent='BioGuard interactive demo';
  const notice=document.createElement('span');notice.textContent='Frontend only · Sample identification and AI plans · No real reports sent';notice.className='demo-notice';
  const row=document.createElement('div');row.className='demo-controls';
  row.append(button('Grounds',()=>demo.login('grounds')),button('Management',()=>demo.login('management')),button('Ecology',()=>demo.login('ecology')),button('Fill example fields',fillFields),button('Use sample photo',sample),button('Advance to inspection date',()=>demo.advance()),button('Reset demo',()=>{if(confirm('Clear this browser’s demo progress and sample photos?'))demo.reset();}));
  const hint=document.createElement('p');hint.id='demo-hint';hint.setAttribute('aria-live','polite');
  const clock=document.createElement('small');clock.id='demo-clock';
  bar.append(title,notice,row,hint,clock);document.body.append(bar);
  const resize=()=>{document.documentElement.style.setProperty('--demo-bar-height',bar.offsetHeight+'px');if(!document.getElementById('root'))document.body.classList.add('demo-management');};new ResizeObserver(resize).observe(bar);resize();
  function update(){hint.textContent=guidance();clock.textContent='Demo date: '+demo.day()+' (Malaysia) · Data stays in this browser · Any uploaded image shows the same prewritten Mimosa example.';}
  window.addEventListener('bioguard:demo-state',update);update();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
