import {useEffect,useRef,useState} from 'react';
import {Image,Linking,View} from 'react-native';
import {Text,TextInput} from 'react-native-paper';
import {ActionButton as Button} from './ActionButton';
import {useIdentification} from '../hooks/useIdentification';
import {useTeamSession} from '../hooks/useTeamSession';
import {DemoLocationPicker} from './DemoLocationPicker';
import {isElminaPoint,type GeoPoint} from '../services/elminaMap';
import {submitInspection,SessionExpired} from '../services/reports';
import {today,type FieldReport,type WorkItem,type InspectionSubmission} from '../services/reportContract';
import {colors} from '../theme';
type FindingDraft={id:string;point:GeoPoint|null;uri?:string;notes:string;selecting?:boolean};
function FindingEditor({value,initial,onChange,onRemove,disabled}:{value:FindingDraft;initial:GeoPoint|null;onChange:(value:FindingDraft)=>void;onRemove:()=>void;disabled:boolean}){
 const photo=useIdentification();const [pinning,setPinning]=useState(false);
 useEffect(()=>{if((photo.photo?.uri&&photo.photo.uri!==value.uri)||Boolean(photo.selecting)!==Boolean(value.selecting))onChange({...value,uri:photo.photo?.uri??value.uri,selecting:photo.selecting});},[photo.photo?.uri,photo.selecting,value,onChange]);
 return <View style={{gap:10,padding:12,borderWidth:1,borderColor:colors.border,borderRadius:10}}>
  {value.uri&&<Image source={{uri:value.uri}} resizeMode="contain" style={{height:160,width:'100%'}} accessibilityLabel="Additional plant photo"/>}
  <Button disabled={disabled||photo.selecting} onPress={()=>{void photo.selectPhoto('camera');}}>Take plant photo</Button>
  <Button disabled={disabled||photo.selecting} onPress={()=>{void photo.selectPhoto('gallery');}}>{value.uri?'Change plant photo':'Choose plant photo'}</Button>
  <Button disabled={disabled||photo.selecting} mode="contained-tonal" onPress={()=>setPinning(true)}>{value.point?'Change plant pin':'Pin additional plant'}</Button>
  {value.point&&<Text>Pin saved: {value.point.latitude.toFixed(6)}, {value.point.longitude.toFixed(6)}</Text>}
  <TextInput label="Plant location note (optional)" value={value.notes} onChangeText={notes=>onChange({...value,notes})} maxLength={500} disabled={disabled} mode="outlined"/>
  <Button disabled={disabled||photo.selecting} onPress={onRemove}>Remove this finding</Button>
  {!!photo.error&&<Text accessibilityRole="alert">{photo.error}</Text>}
  {pinning&&<DemoLocationPicker initial={value.point??initial} onDone={point=>{onChange({...value,point});setPinning(false);}} onCancel={()=>setPinning(false)}/>}
 </View>;
}
export function InspectionResultForm({work,report,onUpdate}:{work:WorkItem;report:FieldReport;onUpdate:(report:FieldReport)=>void}){
 const {session,endSession}=useTeamSession();const [outcome,setOutcome]=useState<InspectionSubmission['outcome']|null>(null);const [notes,setNotes]=useState('');const [date,setDate]=useState(today());const [findings,setFindings]=useState<FindingDraft[]>([]);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const pending=useRef(false);const [recording,setRecording]=useState(!(work.inspections??[]).length);const [requestKey]=useState(()=>`inspection_${Date.now()}_${Math.random().toString(36).slice(2)}`);
 const plan=work.inspection;const p=plan?.point;const initial=isElminaPoint(p)?p:isElminaPoint(report)?report:null;
 const editable=!!session&&session.user.role==='ecology'&&session.user.team_id===work.team_id&&['accepted','in_progress','blocked','correction_requested'].includes(work.status);
 const selecting=findings.some(f=>f.selecting);
 if(!plan)return null;
 async function send(){
  if(!session||pending.current||!outcome||selecting)return;
  if(!notes.trim()){setError(outcome==='unable'?'Explain why inspection was not possible.':'Add a short inspection note.');return;}
  const selected=outcome==='found'?findings:[];
  if(outcome==='found'&&(!selected.length||selected.some(f=>!isElminaPoint(f.point)||!f.uri))){setError('Add a photo and pin for each additional plant.');return;}
  pending.current=true;setBusy(true);setError('');
  try{const details:InspectionSubmission={revision:work.revision,request_key:requestKey,outcome,observed_on:date,notes:notes.trim(),findings:selected.map(f=>({...f.point!,notes:f.notes.trim()}))};const result=await submitInspection(session,work,details,selected.map(f=>f.uri!));onUpdate(result);}
  catch(e){if(e instanceof SessionExpired)endSession(session);setError(e instanceof Error?e.message:'Could not send the inspection. Your photos and pins remain here for retry.');}
  finally{pending.current=false;setBusy(false);}
 }
 return <View style={{gap:12,padding:14,borderWidth:1,borderColor:colors.border,borderRadius:12,backgroundColor:colors.surface}}>
  <Text variant="titleMedium">Approved inspection guidance</Text><Text>{plan.species} · {plan.location.block_ids.length?'Block '+plan.location.block_ids.join(' / '):'Reported location'}</Text>
  <Text>{plan.brief}</Text>
  <Text style={{color:colors.green}} onPress={()=>{void Linking.openURL(plan.source.url);}}>Source: {plan.source.title}</Text>
  {(work.inspections??[]).map(item=><View key={item.id} style={{gap:4,paddingVertical:10,borderTopWidth:1,borderTopColor:colors.border}}>
   <Text variant="labelLarge">{item.outcome==='found'?'Additional plants found':item.outcome==='none'?'No additional plants found':'Unable to inspect'} · {item.observed_on}</Text><Text>{item.notes}</Text>
   <Text>{item.review_status==='reviewed'?'Reviewed by management':'Awaiting management review'}</Text>
   {item.review_notes&&<Text>{item.review_notes}</Text>}
   {item.findings.map((finding,index)=><Text key={index}>Plant {index+1}: {finding.latitude.toFixed(6)}, {finding.longitude.toFixed(6)}{finding.notes?' · '+finding.notes:''}</Text>)}
  </View>)}
  {editable&&!recording&&<Button onPress={()=>setRecording(true)}>Record another inspection</Button>}
  {editable&&recording&&<>
   <Text variant="titleMedium">Inspection result</Text>
   {(['found','none','unable'] as const).map(value=><Button key={value} disabled={busy||selecting} mode={outcome===value?'contained':'outlined'} onPress={()=>setOutcome(value)}>{value==='found'?'More plants found':value==='none'?'No more plants found':'Unable to inspect'}</Button>)}
   {outcome==='found'&&<><Text>Additional plants need management review before removal.</Text>{findings.map(value=><FindingEditor key={value.id} value={value} initial={initial} disabled={busy} onChange={next=>setFindings(previous=>previous.map(f=>f.id===next.id?next:f))} onRemove={()=>setFindings(previous=>previous.filter(f=>f.id!==value.id))}/>)}<Button disabled={busy||selecting||findings.length>=5} onPress={()=>setFindings(previous=>[...previous,{id:`finding_${Date.now()}_${Math.random()}`,point:null,notes:''}])}>Add plant photo and pin</Button></>}
   {outcome&&<><TextInput mode="outlined" label="Inspected on (YYYY-MM-DD)" value={date} onChangeText={setDate} disabled={busy}/><TextInput mode="outlined" label={outcome==='unable'?'Why unable to inspect?':'Inspection note'} multiline value={notes} onChangeText={setNotes} maxLength={1600} disabled={busy}/><Button mode="contained" disabled={busy||selecting} loading={busy} onPress={()=>{void send();}}>Send inspection result</Button></>}
  </>}
  {work.status==='assigned'&&<Text>Accept this job to record the inspection result.</Text>}
  {!!error&&<Text accessibilityRole="alert" style={{color:'#943A31'}}>{error}</Text>}
 </View>;
}
