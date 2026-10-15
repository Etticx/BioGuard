const $ = selector => document.querySelector(selector);
const statusNames = {submitted:'Needs review',needs_info:'More info needed',assigned:'Assigned',closed:'Closed'};
const extentNames = {one:'One plant',few:'A few plants',patch:'A patch',unsure:'Not sure'};
let currentUser, reports = [], teams = [], selectedId, filter = 'all', loading = false;
const node = (tag, text, className) => { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; };
async function api(path, options = {}) {
  const response = await fetch(path, {credentials:'same-origin', ...options, headers:{Accept:'application/json', ...options.headers}});
  if (!response.ok) {
    let message = 'Could not complete this action.';
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : 'Check the review fields and try again.'; } catch {}
    if (response.status === 401) showLogin();
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function showLogin() { currentUser = undefined; reports = []; $('#workspace').hidden = true; $('#account').hidden = true; $('#login-panel').hidden = false; }
function badge(status) { return node('span', statusNames[status] || status, 'badge ' + (status === 'submitted' || status === 'needs_info' ? 'warning' : status === 'closed' ? 'neutral' : '')); }
function feedback(message, failed = false) { const element = $('#feedback'); element.textContent = message; element.className = message ? failed ? 'error' : 'success' : ''; }
async function enter(user) {
  if (user.role !== 'officer') { await api('/auth/logout', {method:'POST'}); throw new Error('Use an ecology-officer account for this dashboard.'); }
  currentUser = user; $('#login-panel').hidden = true; $('#workspace').hidden = false; $('#account').hidden = false; $('#account-name').textContent = user.display_name;
  teams = await api('/teams'); await loadReports();
}
async function loadReports() {
  if (loading) return;
  loading = true; $('#refresh').disabled = true;
  try { reports = await api('/reports'); drawInbox(); if (selectedId) { const report = reports.find(item => item.id === selectedId); if (report) drawDetail(report); } }
  catch (error) { feedback(error.message, true); }
  finally { loading = false; $('#refresh').disabled = false; }
}
function drawInbox() {
  const inbox = $('#inbox'); inbox.replaceChildren();
  const visible = reports.filter(report => filter === 'all' || report.status === filter);
  if (!visible.length) { inbox.append(node('p', reports.length ? 'No reports in this view.' : 'Sightings submitted by the ground team will appear here.', 'empty')); return; }
  for (const report of visible) {
    const button = node('button', undefined, 'report-row' + (selectedId === report.id ? ' selected' : ''));
    button.setAttribute('aria-label', `${report.reference}: ${report.site}, ${report.prediction.common_name}`);
    button.append(node('span', report.prediction.common_name, 'row-title'), node('span', `${report.site} · ${report.landmark}`, 'row-sub'));
    const meta = node('span', undefined, 'row-meta'); meta.append(badge(report.status), node('span', report.reference, 'row-sub')); button.append(meta);
    if (report.prediction.uncertain_identification) button.append(node('span','Identification uncertain','row-sub'));
    button.addEventListener('click', () => { selectedId = report.id; drawInbox(); drawDetail(report); }); inbox.append(button);
  }
}
function fact(label, value) { const container = node('div'); container.append(node('span',label,'fact-label'), node('span',value)); return container; }
function drawDetail(report) {
  const detail = $('#detail'); detail.replaceChildren();
  const top = node('div',undefined,'detail-top'); top.append(node('span',report.reference,'reference'),badge(report.status)); detail.append(top,node('h2', report.site),node('p',report.landmark,'detail-location'));
  const photos = node('div',undefined,'photos');
  for (const photo of report.photos) { const figure = node('figure'); const image = node('img'); image.src = photo.url; image.alt = `${photo.kind} photo for ${report.reference}`; image.loading = 'lazy'; figure.append(image,node('figcaption', {identification:'Plant photo',overview:'Overview',additional:'Additional evidence'}[photo.kind] || photo.kind)); photos.append(figure); }
  detail.append(photos);
  const suggestion = node('div',undefined,'suggestion'); suggestion.append(node('span',`${(report.prediction.confidence * 100).toFixed(1)}%`,'confidence'),node('span','MODEL SUGGESTION','eyebrow'),node('h3',report.prediction.common_name),node('p',report.prediction.predicted_species,'scientific'));
  suggestion.append(node('span', report.prediction.uncertain_identification ? 'Not confident · officer review needed' : report.prediction.sdp_listed_invasive ? 'Invasive · SDP list' : 'Not listed as invasive · SDP list', 'badge ' + (report.prediction.uncertain_identification || report.prediction.sdp_listed_invasive ? 'warning' : 'neutral')));
  detail.append(suggestion);
  const facts = node('div',undefined,'facts'); facts.append(fact('Reported by',report.reporter_name),fact('Observed',report.observed_on),fact('Amount seen',extentNames[report.extent]),fact('Submitted',new Date(report.created_at).toLocaleString())); detail.append(facts);
  if (report.notes) detail.append(node('p', report.notes, 'note'));
  detail.append(node('hr',undefined,'divider'));
  if (report.status === 'assigned' || report.status === 'closed') showDecision(detail,report);
  else {
    if (report.review) { detail.append(node('h3','Previous review'),node('p',report.review.notes,'note'),node('hr',undefined,'divider')); }
    drawReview(detail,report);
  }
  detail.append(node('hr',undefined,'divider'),node('h3','Activity'));
  const history = node('ol',undefined,'history');
  for (const event of report.history) { const item = node('li',`${({submitted:'Report submitted',information_added:'More information added',assigned:'Work approved and assigned',needs_info:'More information requested',closed:'Closed without work'})[event.action] || event.action} · ${event.by}`); item.append(node('time',new Date(event.at).toLocaleString())); if(event.notes) item.append(node('p',event.notes,'note')); history.append(item); }
  detail.append(history);
}
function field(form,label,name,kind='input') { const wrapper = node('label',label); const input = node(kind); input.name = name; input.id = name; wrapper.append(input); form.append(wrapper); return input; }
function option(select,value,label) { const item = node('option',label); item.value = value; select.append(item); }
function drawReview(detail,report) {
  detail.append(node('h3','Ecology review'));
  const form = node('form',undefined,'review-form');
  const decision = field(form,'Decision','decision','select'); option(decision,'request_info','Request more information'); option(decision,'assign','Approve removal & replanting'); option(decision,'no_action','Close — no work needed');
  const species = field(form,'Confirmed species','confirmed_species'); species.maxLength = 160; species.placeholder = 'Enter a verified species, or Unknown';
  const notes = field(form,'Review note','notes','textarea'); notes.required = true; notes.maxLength = 1600; notes.placeholder = 'Explain your decision or the information needed.';
  const work = node('div',undefined,'work-fields'); work.hidden = true;
  const verifiedLabel = node('label',undefined,'check'); const verified = node('input'); verified.type='checkbox'; verified.name='verified'; verifiedLabel.append(verified,node('span','I have verified the species and confirmed that invasive removal is appropriate here.')); work.append(verifiedLabel);
  const crew = field(work,'Assign ground team','assigned_team_id','select'); option(crew,'','Choose team'); for(const team of teams) option(crew,team.id,team.display_name);
  const removal = field(work,'Removal instructions','removal_instructions','textarea'); removal.maxLength=1600;
  const replacement = field(work,'Replacement species','replacement_species'); replacement.maxLength=160; replacement.placeholder='Chosen by the ecology officer';
  const planting = field(work,'Replanting instructions','replanting_instructions','textarea'); planting.maxLength=1600;
  work.append(node('p','The officer chooses the replacement species for this site.','review-hint')); form.append(work);
  const error = node('p','','error'); error.setAttribute('role','alert');
  const submit = node('button','Request information','primary'); submit.type='submit';
  decision.addEventListener('change',() => { const assign = decision.value==='assign'; work.hidden=!assign; for(const element of [verified,crew,removal,replacement,planting]) element.required=assign; species.required=assign; submit.textContent=assign?'Approve & assign':decision.value==='no_action'?'Close report':'Request information'; });
  form.append(error,submit);
  form.addEventListener('submit',async event => {
    event.preventDefault(); submit.disabled=true; error.textContent='';
    const assign=decision.value==='assign';
    const body={revision:report.revision,decision:decision.value,confirmed_species:species.value.trim(),confirmed_invasive:assign?verified.checked:null,notes:notes.value.trim(),assigned_team_id:assign?crew.value:null,removal_instructions:assign?removal.value.trim():'',replacement_species:assign?replacement.value.trim():'',replanting_instructions:assign?planting.value.trim():''};
    try { await api(`/reports/${report.id}/review`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); feedback(assign?'Work approved and assigned to the ground team.':decision.value==='no_action'?'Report closed.':'Information requested from the reporting team.'); await loadReports(); }
    catch(failure){error.textContent=failure.message;submit.disabled=false;}
  }); detail.append(form);
}
function showDecision(detail,report) {
  const review=report.review; const plan=node('div',undefined,'plan'); plan.append(node('h3',report.status==='assigned'?'Approved field work':'Ecology decision'),fact('Reviewed by',review.reviewer_name));
  if(review.confirmed_species) plan.append(fact('Confirmed species',review.confirmed_species)); plan.append(node('p',review.notes));
  if(report.status==='assigned') for(const [label,key] of [['Assigned team','assigned_team_name'],['Removal','removal_instructions'],['Replacement species','replacement_species'],['Replanting','replanting_instructions']]) {const item=node('div');item.append(node('span',label,'fact-label'),node('p',review[key]));plan.append(item);}
  detail.append(plan);
}
$('#login-form').addEventListener('submit',async event => { event.preventDefault(); const form=event.currentTarget; const button=form.querySelector('button'); button.disabled=true; $('#login-error').textContent=''; try {const result=await api('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:form.elements.username.value,password:form.elements.password.value})});form.elements.password.value='';await enter(result.user);}catch(error){$('#login-error').textContent=error.message;}finally{button.disabled=false;}});
$('#signout').addEventListener('click',async()=>{try{await api('/auth/logout',{method:'POST'});showLogin();$('#detail').replaceChildren(node('p','Choose a report to review.','empty'));selectedId=undefined;}catch(error){feedback(error.message,true);}});
$('#refresh').addEventListener('click',()=>loadReports());
$('#filters').addEventListener('click',event=>{const button=event.target.closest('[data-filter]');if(!button)return;filter=button.dataset.filter;for(const item of $('#filters').querySelectorAll('button'))item.setAttribute('aria-pressed',String(item===button));drawInbox();});
api('/auth/me').then(enter).catch(()=>showLogin());
