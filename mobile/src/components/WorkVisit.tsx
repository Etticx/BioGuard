import { ActionButton as Button } from './ActionButton';
import { useEffect, useRef, useState } from 'react';
import { Image, View } from 'react-native';
import { Chip, Text, TextInput } from 'react-native-paper';
import { router } from 'expo-router';
import { useIdentification } from '../hooks/useIdentification';
import { useTeamSession } from '../hooks/useTeamSession';
import { today, workNames, type Completion, type FieldReport, type WorkItem } from '../services/reportContract';
import { progressWork, SessionExpired } from '../services/reports';
import { listDrafts, openDraft, releaseDraft, saveDraft } from '../services/draftStore';
import { sendDraft } from '../services/outbox';
import type { Draft } from '../services/draftTypes';
import { recoverVisitDraft, requiresVisitReview, visitStage } from '../services/draftRecovery';
import { CheckField } from './CheckField';
import { colors } from '../theme';
import { packVisitPhotos, visitPhotos } from '../services/visitPhotos';

export function WorkVisit({work,onUpdate,draftId}:{work:WorkItem;onUpdate:(report:FieldReport)=>void;draftId?:string}){
 const {session,endSession}=useTeamSession();
 const photo=useIdentification();
 const plantingPhoto=useIdentification();
 const selecting=photo.selecting||plantingPhoto.selecting;
 const restoration=work.work_type==='restoration';
 const removalRecorded=work.completions.some(item=>item.removal_complete&&item.removed_on);
 const initialStage=visitStage(work.work_type,restoration&&removalRecorded?'replanting':undefined);
 const [restored,setRestored]=useState<Draft|null>(null);
 const [loadedKey,setLoadedKey]=useState(''),[queued,setQueued]=useState(false);
 const workKey=`${session?.user.id}:${work.id}:${work.revision}:${work.work_type}`;
 const loading=loadedKey!==workKey;
 const [requestKey,setRequestKey]=useState(()=>`evidence_${Date.now()}_${Math.random().toString(36).slice(2)}`);
 const [reviewed,setReviewed]=useState(false);
 const needsReview=requiresVisitReview(restored,work,reviewed);
 const [stage,setStage]=useState<Completion['stage']>(initialStage);
 const [observed,setObserved]=useState(today()),[removed,setRemoved]=useState(today()),[planted,setPlanted]=useState(today());
 const [pendingReason,setPendingReason]=useState('');
 const [quantity,setQuantity]=useState(''),[notes,setNotes]=useState(''),[confirmed,setConfirmed]=useState(false);
 const [suggested,setSuggested]=useState('');
 const [recommendation,setRecommendation]=useState<NonNullable<Completion['recommended_action']>>('none');
 const [removalPlan,setRemovalPlan]=useState(''),[replacementPlan,setReplacementPlan]=useState('');
 const [expanded,setExpanded]=useState(false),[problem,setProblem]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const pending=useRef(false);
 const mine=session?.user.role==='ecology'&&session.user.team_id===work.team_id;
 const legacy=Boolean(work.legacy)||!['restoration','inspection','removal','replanting'].includes(work.work_type);
 const ready=mine&&!legacy&&!work.requires_reassignment;
 const editable=ready&&['accepted','in_progress','blocked','correction_requested'].includes(work.status);

 useEffect(()=>{
  if(!session||!mine)return;
  let alive=true;let loaded:Draft|null=null;
  void recoverVisitDraft(session.user.id,{id:work.id,report_id:work.report_id},{list:listDrafts,open:openDraft},draftId).then(item=>{
   if(!alive){if(item)releaseDraft(item);return;}setLoadedKey(workKey);setReviewed(false);setRestored(null);setQueued(false);setStage(initialStage);loaded=item;if(!loaded)return;
   if(loaded.state==='queued'){setQueued(true);return;}
   const d=loaded.details as Completion;setRestored(loaded);setRequestKey(loaded.id);setStage(visitStage(work.work_type,d.stage));
   setObserved(d.observed_on);setRemoved(d.removed_on??today());setPlanted(d.planted_on??today());setQuantity(d.quantity?.toString()??'');setNotes(d.notes);setConfirmed(d.removal_complete);setPendingReason(d.planting_pending_reason??'');
   setSuggested(d.suggested_species??'');setRecommendation(d.recommended_action??'none');setRemovalPlan(d.removal_recommendation??'');setReplacementPlan(d.replacement_recommendation??'');
  }).catch(()=>{if(alive)setError('Could not open saved evidence. Reopen this job to retry.');});
  return()=>{alive=false;if(loaded)releaseDraft(loaded);};
 },[session,mine,work.id,work.report_id,work.revision,work.work_type,workKey,initialStage,draftId]);
 if(!session)return null;
 const ended=['verified','cancelled'].includes(work.status);
 if(ended&&!expanded)return <View style={{padding:16,gap:8,borderRadius:12,backgroundColor:colors.paleGreen}}><Text variant="titleMedium">{workNames[work.work_type]??work.work_type} · {work.status}</Text><Text>{work.team_name} · {work.due_on}</Text>{work.verification&&<Text>{work.verification.notes}</Text>}<Button onPress={()=>setExpanded(true)}>View earlier job</Button></View>;
 const savedPhotos=visitPhotos(restored);
 const removalUri=photo.photo?.uri??savedPhotos.removal;
 const plantingUri=plantingPhoto.photo?.uri??savedPhotos.planting;
 const visitUri=photo.photo?.uri??savedPhotos.visit;
 const uri=stage==='replanting'?plantingUri:stage==='observation'?visitUri:removalUri;
 const primaryPhoto=stage==='replanting'?plantingPhoto:photo;
 const photos=packVisitPhotos({...savedPhotos,...(stage==='observation'?{visit:visitUri}:{removal:removalUri,planting:plantingUri})});
 const details:Completion={revision:work.revision,request_key:requestKey,stage,observed_on:observed,notes:notes.trim(),removal_complete:['removal','both'].includes(stage)&&confirmed,removed_on:['removal','both'].includes(stage)?removed:null,planted_on:['replanting','both'].includes(stage)?planted:null,planted_species:['replanting','both'].includes(stage)?work.replacement_species:'',quantity:['replanting','both'].includes(stage)?Number(quantity):null,...(restoration?{planting_pending_reason:stage==='removal'?pendingReason.trim():''}:{}),
  ...(work.work_type==='inspection'?{suggested_species:suggested.trim(),recommended_action:recommendation,removal_recommendation:removalPlan.trim(),replacement_recommendation:replacementPlan.trim()}:{})};
 async function persist(state:'saved'|'queued'){
  if(needsReview)throw new Error('Review the latest instructions and saved evidence before continuing.');
  if(!session||!uri)throw new Error('Add an evidence photo.');
  if(state==='queued'&&restoration&&stage==='both'&&!plantingUri)throw new Error('Add the replanting photo.');
  await saveDraft({id:requestKey,owner:session.user.id,kind:'completion',state,label:workNames[work.work_type]+' evidence',details,reportId:work.report_id,workId:work.id,...(restored?.continuationOf?{continuationOf:restored.continuationOf}:{}),...photos});
 }
 async function run(action:'accept'|'start'|'blocked'|'send'|'save'){
  if(!session||pending.current||selecting)return;
  if(action==='blocked'&&!notes.trim()){setError('Describe the problem first.');return;}
  if(action==='send'&&work.work_type==='inspection'&&(!suggested.trim()||(recommendation==='removal'&&!removalPlan.trim())||(recommendation==='replanting'&&!replacementPlan.trim()))){setError('Add the inspected species and the recommended plan.');return;}
  if(action==='send'&&restoration&&stage==='removal'&&!pendingReason.trim()){setError('Explain why replanting is pending.');return;}
  pending.current=true;setBusy(true);setError('');
  try{
   if(action==='send'||action==='save'){
    await persist(action==='send'?'queued':'saved');
    if(action==='save'){setError('Evidence draft saved.');return;}
    try{const result=await sendDraft(session,requestKey);photo.reset();plantingPhoto.reset();onUpdate(result);}catch(e){setQueued(true);throw e;}
   }else{
    if(uri&&action!=='accept')await persist('saved');
    onUpdate(await progressWork(session,work,action,notes.trim()));
   }
  }catch(e){if(e instanceof SessionExpired)endSession(session);setError(e instanceof Error?e.message:'Could not update this job.');}
  finally{pending.current=false;setBusy(false);}
 }
 return <View style={{padding:16,gap:12,borderRadius:12,backgroundColor:colors.paleGreen}}>
  <Text variant="titleMedium">{workNames[work.work_type]??work.work_type}</Text>
  <Text>{work.team_name} · {work.status.replaceAll('_',' ')}</Text>
  <Text>{work.due_on?'Due '+work.due_on:'Ask management for a visit date'}{work.overdue?' · Overdue':''}{work.priority==='high'?' · High priority':''}</Text>
  <Text>{work.notes}</Text>
  {!!work.confirmed_species&&<Text>Approved species: {work.confirmed_species}</Text>}
  {!!work.removal_instructions&&<><Text variant="labelLarge">Removal instructions</Text><Text>{work.removal_instructions}</Text></>}
  {!!work.replacement_species&&<><Text variant="labelLarge">Replacement: {work.replacement_species}</Text><Text>{work.replanting_instructions}</Text></>}
  {work.verification&&<Text>Management: {work.verification.notes}</Text>}
  {work.completions.map((item,index)=><View key={index} style={{gap:4,borderTopWidth:1,borderTopColor:colors.border,paddingTop:10}}>
   <Text variant="labelLarge">Evidence {index+1} · {item.stage}</Text><Text>{item.notes}</Text>
   {!!item.suggested_species&&<Text>Inspected species: {item.suggested_species}</Text>}
   {!!item.recommended_action&&<Text>Recommended action: {item.recommended_action}</Text>}
   {!!item.removal_recommendation&&<Text>{item.removal_recommendation}</Text>}{!!item.replacement_recommendation&&<Text>{item.replacement_recommendation}</Text>}
   {item.removed_on&&<Text>Removed: {item.removed_on}</Text>}{item.planted_on&&<Text>Planted: {item.planted_on} · {item.quantity} × {item.planted_species}</Text>}
   {!!item.planting_pending_reason&&<Text>Replanting pending: {item.planting_pending_reason}</Text>}{item.regrowth&&<Text>Regrowth: {item.regrowth}</Text>}{item.checked_count!=null&&<Text>Surviving: {item.surviving_count}/{item.checked_count}</Text>}
   <Text>{item.submitted_by} · {item.observed_on}</Text>
  </View>)}
  {(legacy||work.requires_reassignment)&&!ended&&<Text>This earlier assignment is read-only. Management needs to assign an ecology job.</Text>}
  {restored&&!editable&&<><Text variant="titleMedium">Saved evidence draft</Text><Text>{(restored.details as Completion).notes}</Text><Text>Visited on: {(restored.details as Completion).observed_on}</Text>{restored.uris[0]&&<Image source={{uri:restored.uris[0]}} resizeMode="contain" style={{width:'100%',height:180}} accessibilityLabel="Saved evidence preview"/>}<Text>Your local draft has been kept.</Text></>}
  {ready&&work.status==='assigned'&&<Button mode="contained" loading={busy} disabled={busy||loading||selecting} onPress={()=>{void run('accept');}}>Accept job</Button>}
  {editable&&!loading&&(queued?<><Text>Evidence saved for retry. Wait for the upload receipt.</Text><Button onPress={()=>router.push('/drafts')}>Open drafts & uploads</Button></>:<>
   {restored&&(restored.details as Completion).revision!==work.revision&&<><Text accessibilityLiveRegion="polite">This job changed after the evidence was saved. Check the current instructions, photo, dates and notes.</Text>{!!(restored.details as Completion).planted_species&&<Text>Saved planting species: {(restored.details as Completion).planted_species}</Text>}<CheckField label="I reviewed this evidence against the current job instructions" checked={reviewed} onChange={setReviewed} disabled={busy}/></>}
   {work.status==='accepted'&&<Button disabled={busy||needsReview||selecting} mode="outlined" onPress={()=>{void run('start');}}>Start work</Button>}
   <Button disabled={busy||selecting} onPress={()=>setProblem(!problem)}>{problem?'Back to evidence':'Report a problem'}</Button>
   {problem?<><TextInput mode="outlined" label="Problem or obstacle" accessibilityLabel="Problem or obstacle" multiline value={notes} onChangeText={setNotes} maxLength={1600}/><Button disabled={busy||needsReview||selecting} mode="contained" onPress={()=>{void run('blocked');}}>Send problem to management</Button></>:<>
    <Text variant="titleMedium">{work.work_type==='inspection'?'Inspection findings.':'Job evidence.'}</Text>
    {work.work_type==='inspection'&&<>
     <TextInput mode="outlined" label="Inspected species" accessibilityLabel="Inspected species" value={suggested} onChangeText={setSuggested} maxLength={160}/>
     <Text>Recommended next action</Text><View style={{flexDirection:'row',gap:8,flexWrap:'wrap'}}>{(['none','inspection','removal','replanting'] as const).map(value=><Chip key={value} selected={recommendation===value} onPress={()=>setRecommendation(value)}>{value==='none'?'No further work':workNames[value]}</Chip>)}</View>
     {(recommendation==='removal'||!!removalPlan)&&<TextInput mode="outlined" label="Recommended removal plan" accessibilityLabel="Recommended removal plan" multiline maxLength={1600} value={removalPlan} onChangeText={setRemovalPlan}/>}
     {(recommendation==='replanting'||recommendation==='removal'||!!replacementPlan)&&<TextInput mode="outlined" label="Replacement recommendation" accessibilityLabel="Replacement recommendation" multiline maxLength={1600} value={replacementPlan} onChangeText={setReplacementPlan}/>}
     <Text>Management approves the next plan before work begins.</Text>
    </>}
    {restoration&&<View style={{gap:8}}><Text>Record this restoration job</Text><View style={{flexDirection:'row',flexWrap:'wrap',gap:8}}>{(['both','removal',...(removalRecorded?['replanting'] as const:[])] as Completion['stage'][]).map(value=><Chip key={value} selected={stage===value} onPress={()=>setStage(value)}>{value==='both'?'Both completed':value==='removal'?'Planting pending':'Finish planting'}</Chip>)}</View>{stage==='removal'&&<TextInput mode="outlined" label="Why is replanting pending?" accessibilityLabel="Why is replanting pending?" value={pendingReason} onChangeText={setPendingReason} multiline maxLength={1600}/>}</View>}
    {['removal','both'].includes(stage)&&<><CheckField label="Removal completed as instructed" checked={confirmed} onChange={setConfirmed}/><TextInput mode="outlined" label="Removed on (YYYY-MM-DD)" accessibilityLabel="Removed on (YYYY-MM-DD)" value={removed} onChangeText={setRemoved}/></>}
    {['replanting','both'].includes(stage)&&<><Text>Approved replacement: {work.replacement_species}</Text><TextInput mode="outlined" label="Planted on (YYYY-MM-DD)" accessibilityLabel="Planted on (YYYY-MM-DD)" value={planted} onChangeText={setPlanted}/><TextInput mode="outlined" label="Quantity planted" accessibilityLabel="Quantity planted" keyboardType="number-pad" value={quantity} onChangeText={setQuantity}/></>}
    <TextInput mode="outlined" label="Visited on (YYYY-MM-DD)" accessibilityLabel="Visited on (YYYY-MM-DD)" value={observed} onChangeText={setObserved}/>
    <TextInput mode="outlined" label="Visit note" accessibilityLabel="Visit note" multiline maxLength={1600} value={notes} onChangeText={setNotes}/>
    {uri&&<Image source={{uri}} resizeMode="contain" style={{width:'100%',height:180}} accessibilityLabel="Removal or visit evidence preview"/>}
    <Button mode="outlined" disabled={busy||selecting} onPress={()=>{void primaryPhoto.selectPhoto('camera');}}>{restoration?(stage==='replanting'?'Take replanting photo':'Take removal photo'):'Take evidence photo'}</Button>
    <Button mode="outlined" disabled={busy||selecting} onPress={()=>{void primaryPhoto.selectPhoto('gallery');}}>{restoration?(stage==='replanting'?'Choose replanting photo':'Choose removal photo'):(uri?'Change evidence photo':'Choose evidence photo')}</Button>
    {restoration&&stage==='both'&&<>{plantingUri&&<Image source={{uri:plantingUri}} resizeMode="contain" style={{width:'100%',height:180}} accessibilityLabel="Replanting evidence preview"/>}<Button disabled={busy||selecting} onPress={()=>{void plantingPhoto.selectPhoto('camera');}}>Take replanting photo</Button><Button disabled={busy||selecting} onPress={()=>{void plantingPhoto.selectPhoto('gallery');}}>Choose replanting photo</Button>{!!plantingPhoto.error&&<Text>{plantingPhoto.error}</Text>}</>}
    {!!primaryPhoto.error&&<Text>{primaryPhoto.error}</Text>}
    <Button mode="contained" loading={busy} disabled={busy||selecting||needsReview||!uri||!notes.trim()||(restoration&&stage==='both'&&!plantingUri)} onPress={()=>{void run('send');}}>{restoration&&stage==='removal'?'Save removal progress':'Send to management'}</Button>
    <Button disabled={busy||selecting||needsReview||!uri} onPress={()=>{void run('save');}}>Save evidence draft</Button>
   </>}
  </>)}
  {work.status==='awaiting_verification'&&<Text>Management will review this evidence.</Text>}
  {ended&&<Button onPress={()=>setExpanded(false)}>Hide earlier job</Button>}
  {!!error&&<Text accessibilityLiveRegion="polite" style={{color:'#943A31'}}>{error}</Text>}
 </View>;
}
