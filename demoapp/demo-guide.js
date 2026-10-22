/* Step-specific guidance over the unchanged product UI. No automatic approvals. */
(() => {
 const demo=window.BioGuardDemo;
 let target=null,step=null,paused=localStorage.getItem('bioguard-demo-guide-paused')==='1';
 const visible=e=>!!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!=='hidden';
 const text=e=>(e?.textContent||'').trim().replace(/\s+/g,' ');
 const controls=()=>[...document.querySelectorAll('button,[role="button"],a')].filter(visible);
 const button=(label,toolbar=false)=>controls().find(e=>(text(e)===label||e.getAttribute('aria-label')===label||text(e).replace(/ \(Selected\)$/,'')===label)&&(toolbar?!!e.closest('#demo-toolbar'):!e.closest('#demo-toolbar')));
 const tool=label=>button(label,true);
 const input=label=>[...document.querySelectorAll('input,textarea')].find(e=>visible(e)&&e.getAttribute('aria-label')===label)||(label==='Inspection note'?[...document.querySelectorAll('textarea:not([aria-label])')].find(visible):null);
 const field=name=>[...document.querySelectorAll(`[name="${name}"]`)].find(visible);
 const checked=e=>e&&(e.checked||text(e).endsWith(' (Selected)')||['aria-selected','aria-checked','aria-pressed'].some(a=>e.getAttribute(a)==='true'));
 const image=label=>document.querySelector(`[aria-label="${label}"],img[alt="${label}"]`);
 const make=(number,phase,message,element)=>({number,phase,message,element});
 const role=(name,number,message)=>make(number,'Switch role',message,tool(name));
 function openReport(number){return make(number,'Management', 'Click the '+demo.state.reports[0].reference+' report in the left-hand list to open its details.',controls().find(e=>e.getAttribute('aria-label')?.startsWith(demo.state.reports[0].reference+':')));}
 function detail(){return !!document.querySelector('#detail h2');}
 function ecologyDetails(number,followup){
  if(button('Open job'))return make(number,'Ecology','Click Open job to view '+(followup?'the follow-up inspection.':'the assigned restoration job.'),button('Open job'));
  if(![...document.querySelectorAll('h1,h2,[role="heading"]')].some(e=>text(e)==='Job details.')){
   const tab=button(followup?'Upcoming inspections':'Active');
   if(!tab&&button('Back'))return make(number,'Ecology','Click Back to return to My jobs and continue the assigned work.',button('Back'));
   if(tab)return make(number,'Ecology',followup?'Click Upcoming inspections. The follow-up is separate from the approved restoration job.':'Click Active to find the assigned restoration job.',tab);
  }
  return null;
 }
 function next(){
  const r=demo.state.reports[0],user=demo.state.user,last=r?.work_items.at(-1);
  if(!user){
   if(!input('Username')?.value||!input('Password')?.value)return make(1,'Login','Click Fill example fields to enter grounds / 123. You can also type these demo credentials yourself.',tool('Fill example fields'));
   return make(2,'Login','Click Sign in to enter the Grounds workspace.',button('Sign in'));
  }
  if(!r){
   if(user.role!=='ground')return role('Grounds',3,'Click Grounds to start by reporting a plant.');
   if(button('Done'))return make(8,'Pin the location','Move the map under the red pin to the plant location. Then click Done to save that point.',button('Done'));
   if(button('Submit report')){
    if(!input('Site or block')?.value||!input('Nearby landmark')?.value)return make(6,'Grounds report','Click Fill example fields to enter the site, nearby landmark and note. You can edit those details afterwards.',tool('Fill example fields'));
    if(button('Pin plant location'))return make(7,'Grounds report','Click Pin plant location. A map will open; position the red pin, then press Done.',button('Pin plant location'));
    return make(9,'Grounds report','Click Submit report to send the photo, location and details to Management.',button('Submit report'));
   }
   if(button('Report sighting'))return make(5,'Grounds identification','The sample result is Mimosa pudica. Click Report sighting to add its location and details.',button('Report sighting'));
   if(controls().some(e=>e.getAttribute('aria-label')==='Identify plant'))return make(4,'Grounds identification','Click Identify. This demo displays a fixed Mimosa pudica example; it does not classify your image.',controls().find(e=>e.getAttribute('aria-label')==='Identify plant'));
   if(button('Back'))return make(3,'Grounds','Click Back to return to the plant photo screen and begin the report.',button('Back'));
   return make(3,'Grounds photo','Click Use sample photo to load the demo image into the original photo picker. You can choose your own image instead.',tool('Use sample photo'));
  }
  if(r.status==='completed'){
   if(user.role!=='management')return role('Management',35,'Click Management to review the closed case and download its demo PDF.');
   if(!detail())return openReport(35);
   if(localStorage.getItem('bioguard-demo-guide-pdf:'+r.id))return make(36,'Walkthrough complete','You completed the whole workflow. Use Reset demo to try again, or explore the closed record.',tool('Reset demo'));
   return make(35,'Closed case','Click Download PDF for a browser-generated demo summary. The real product export also includes its full evidence appendix.',document.querySelector('#detail a[download]'));
  }
  if(!last){
   if(user.role!=='management')return role('Management',10,'Your report is submitted. Click Management to review it and assign the work.');
   if(!detail())return openReport(11);
   if(!field('assigned_team_id')?.value||!field('due_on')?.value)return make(12,'Assign the work','Click Fill example fields to select Ecology field team and today’s work date. Review the inspection guidance above the form.',tool('Fill example fields'));
   const approval=[...document.querySelectorAll('input[type="checkbox"]')].find(e=>e.closest('label')?.textContent.includes('approve removal at this site'));
   if(approval&&!approval.checked)return make(13,'Management approval','Review the suggested species and guidance. Tick this confirmation to approve removal and display the sample restoration plan.',approval.closest('label'));
   const save=button('Save decision');
   if(save)return make(14,'Review the sample plan','Read Removal, Replacement species, Replanting and Handover note. You can edit each section. Then click Save decision to assign the job.',save);
  }
  if(last?.status==='awaiting_verification'){
   const final=!!last.followup_of;
   if(user.role!=='management')return role('Management',final?32:23,'Ecology has submitted '+(final?'the follow-up findings.':'restoration evidence.')+' Click Management to review it.');
   if(!detail())return openReport(final?33:24);
   const review=button('Mark inspection reviewed');
   if(review){const note=[...document.querySelectorAll('textarea[name^="inspection_review_"]')].find(visible);if(!note?.value.trim())return make(25,'Review the initial inspection','Click Fill example fields to add an inspection review note, then review the result before approving the work.',tool('Fill example fields'));
    return make(26,'Review the initial inspection','Click Mark inspection reviewed to accept the recorded inspection result.',review);}
   if(!field('verification_notes')?.value.trim())return make(final?33:27,'Review the evidence','Review the photos and findings, then click Fill example fields to add the Management review note. You can edit the note.',tool('Fill example fields'));
   return make(final?34:28,final?'Close the case':'Schedule the follow-up',final?'Click Approve and close to accept the successful follow-up and close the whole case.':'Check the follow-up date, then click Approve and schedule inspection. The default is replanting date plus 14 days.',button(final?'Approve and close':'Approve and schedule inspection'));
  }
  if(last){
   const followup=!!last.followup_of;
   if(user.role!=='ecology')return role('Ecology',followup?29:15,'Click Ecology to '+(followup?'open the linked follow-up inspection.':'carry out the assigned inspection and restoration work.'));
   const opening=ecologyDetails(followup?29:16,followup);if(opening)return opening;
   if(followup&&last.due_on!==demo.day())return make(29,'Scheduled inspection','This visit is locked until '+last.due_on+'. Click Advance to inspection date to simulate that date. No real computer clock is changed.',tool('Advance to inspection date'));
   if(last.status==='assigned')return make(followup?30:17,'Accept the job','Click Accept job. This opens the fields for '+(followup?'the scheduled follow-up findings.':'the initial inspection and restoration evidence.'),button('Accept job'));
   if(followup){
    if(!checked(button('Not observed')))return make(31,'Follow-up findings','For the successful sample, choose Not observed: the target invasive plant has not reappeared.',button('Not observed'));
    if(!checked(button('Healthy')))return make(31,'Follow-up findings','Choose Healthy to record that the sample replacement planting is doing well.',button('Healthy'));
    if(!checked(button('No')))return make(31,'Follow-up findings','Choose No for other suspected invasive plants in this successful example.',button('No'));
    if(!input('Visit note')?.value.trim())return make(31,'Follow-up evidence','Click Fill example fields to add a visit note. The visit date is fixed to the inspection date.',tool('Fill example fields'));
    if(!image('Removal or visit evidence preview'))return make(31,'Follow-up evidence','Click Use sample photo to add the current-site evidence image, or choose a photo yourself.',tool('Use sample photo'));
    return make(31,'Submit follow-up','Click Send to management. Management must review these findings before the case can close.',button('Send to management'));
   }
   if(!last.inspections?.length){
    if(!input('Inspection note'))return make(18,'Initial site inspection','For the successful walkthrough, click No more plants found under Inspection result.',button('No more plants found'));
    if(!input('Inspection note')?.value.trim())return make(19,'Initial site inspection','Click Fill example fields to add an inspection note. The date is already filled.',tool('Fill example fields'));
    return make(20,'Submit initial inspection','Click Send inspection result. This records the site check; restoration evidence is submitted separately.',button('Send inspection result'));
   }
   const removed=document.querySelector('[role="checkbox"][aria-label="Removal completed as instructed"]');
   if(removed&&!checked(removed))return make(21,'Restoration evidence','After reviewing the sample work instructions, tick Removal completed as instructed.',removed);
   if(!input('Quantity planted')?.value||!input('Visit note')?.value.trim())return make(21,'Restoration details','Click Fill example fields to enter the planted quantity and visit note. Check the removal and planting dates.',tool('Fill example fields'));
   if(!image('Removal or visit evidence preview'))return make(22,'Removal photo','Click Use sample photo once to fill the removal evidence image. This is an illustrative image, not proof of field work.',tool('Use sample photo'));
   if(!image('Replanting evidence preview'))return make(22,'Replanting photo','Click Use sample photo again to fill the separate replanting evidence image.',tool('Use sample photo'));
   return make(22,'Submit restoration','Click Send to management to submit the completed removal and replanting evidence for review.',button('Send to management'));
  }
  return make(1,'Explore','Open a report to continue the guided example. Reset demo starts a clean walkthrough.',tool('Reset demo'));
 }
 function mount(){
  const bar=document.getElementById('demo-toolbar');if(!bar){setTimeout(mount,100);return;}
  const hint=document.getElementById('demo-hint');const row=bar.querySelector('.demo-controls');
  const show=document.createElement('button');show.textContent='Show next step';show.id='demo-show-step';
  const toggle=document.createElement('button');toggle.textContent=paused?'Resume guide':'Hide guide';
  row.append(show,toggle);
  const arrow=document.createElement('div');arrow.id='demo-guide-arrow';arrow.setAttribute('aria-hidden','true');arrow.innerHTML='<svg width="30" height="34" viewBox="0 0 30 34"><path d="M15 2v25M5 19l10 11 10-11" fill="none" stroke="#b45a00" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  document.body.append(arrow);
  function position(){
   if(paused||!visible(target)){arrow.hidden=true;return;}
   const r=target.getBoundingClientRect(),height=bar.getBoundingClientRect().bottom,inside=!!target.closest('#demo-toolbar');
   if(inside||r.bottom<height+10||r.top>innerHeight-15){arrow.hidden=true;return;}
   arrow.hidden=false;
   if(innerWidth-r.right>42){arrow.style.transform='rotate(90deg)';arrow.style.left=(r.right+6)+'px';arrow.style.top=Math.max(height+3,r.top+r.height/2-17)+'px';}
   else if(r.left>42){arrow.style.transform='rotate(-90deg)';arrow.style.left=(r.left-36)+'px';arrow.style.top=Math.max(height+3,r.top+r.height/2-17)+'px';}
   else{arrow.style.transform='none';arrow.style.left=Math.max(8,Math.min(innerWidth-38,r.right-34))+'px';arrow.style.top=Math.max(height+3,r.top-38)+'px';}
  }
  function update(){
   if(paused){target?.classList.remove('demo-next-target');target=null;arrow.hidden=true;if(!show.disabled)show.disabled=true;const note='Guide paused. Click Resume guide for precise instructions and highlights.';if(hint.textContent!==note)hint.textContent=note;return;}
   step=next();if(target!==step.element){target?.classList.remove('demo-next-target');target=step.element||null;target?.classList.add('demo-next-target');}if(target&&!target.classList.contains('demo-next-target'))target.classList.add('demo-next-target');
   const note='Next - '+step.phase+': '+step.message;if(hint.textContent!==note)hint.textContent=note;
   bar.dataset.guideStep=String(step.number);bar.dataset.guidePhase=step.phase;if(show.disabled!==!target)show.disabled=!target;position();
  }
  show.addEventListener('click',()=>{if(!target)return;target.scrollIntoView({block:'center',inline:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});setTimeout(position,400);});
  toggle.addEventListener('click',()=>{paused=!paused;localStorage.setItem('bioguard-demo-guide-paused',paused?'1':'0');toggle.textContent=paused?'Resume guide':'Hide guide';update();});
  let timer;const schedule=()=>{clearTimeout(timer);timer=setTimeout(update,100);};
  new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','aria-selected','aria-checked','aria-pressed','disabled']});
  document.addEventListener('input',schedule,true);document.addEventListener('change',schedule,true);document.addEventListener('click',schedule,true);
  document.addEventListener('click',e=>{if(e.target.closest?.('#detail a[download]')&&demo.state.reports[0])localStorage.setItem('bioguard-demo-guide-pdf:'+demo.state.reports[0].id,'1');},true);
  window.addEventListener('bioguard:demo-state',schedule);window.addEventListener('scroll',position,true);window.addEventListener('resize',position);update();
 }
 mount();
})();
