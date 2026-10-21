import { useEffect, useRef, useState } from 'react';
import { Image, StyleSheet, View } from 'react-native';
import { Button, Chip, Text, TextInput } from 'react-native-paper';
import { router } from 'expo-router';
import { useIdentification } from '../hooks/useIdentification';
import { useTeamSession } from '../hooks/useTeamSession';
import type { Identification } from '../services/contract';
import { type Catalog, type Extent, type FieldReport, type ReportDetails, today, validateReportDetails } from '../services/reportContract';
import { getCatalog, SessionExpired } from '../services/reports';
import { saveDraft } from '../services/draftStore';
import type { Draft } from '../services/draftTypes';
import { sendDraft } from '../services/outbox';
import { colors } from '../theme';
import { DemoLocationPicker } from './DemoLocationPicker';
import { isElminaPoint, ELMINA_MAP_ID, type GeoPoint } from '../services/elminaMap';
import { CheckField } from './CheckField';
import { SelectField } from './SelectField';
import { TeamSignIn } from './TeamSignIn';
export function ReportForm({uri,prediction,initial,onDone,onCancel}:{uri:string;prediction:Identification|null;initial?:Draft;onDone:()=>void;onCancel:()=>void}){
 const {session,endSession}=useTeamSession();const overview=useIdentification();const original=initial?.details as ReportDetails|undefined;
 const [site,setSite]=useState(original?.site??'');const [siteId,setSiteId]=useState(original?.site_id??'');const [blockId,setBlockId]=useState(original?.block_id??'');const [catalog,setCatalog]=useState<Catalog>({sites:[],blocks:[]});
 const [landmark,setLandmark]=useState(original?.landmark??'');const [extent,setExtent]=useState<Extent>(original?.extent??'unsure');const [notes,setNotes]=useState(original?.notes??'');const [date,setDate]=useState(original?.observed_on??today());const [questioned,setQuestioned]=useState(original?.identification_questioned??false);
 const [mapPoint,setMapPoint]=useState<GeoPoint|null>(original?.location_mode==='osm'&&isElminaPoint(original)?{latitude:original.latitude,longitude:original.longitude}:null);const [pickerOpen,setPickerOpen]=useState(false);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [saved,setSaved]=useState('');const [receipt,setReceipt]=useState<FieldReport|null>(null);const [queued,setQueued]=useState(false);
 const [requestKey]=useState(()=>initial?.id??`report_${Date.now()}_${Math.random().toString(36).slice(2)}`);const chain=useRef<Promise<unknown>>(Promise.resolve());const pending=useRef(false);
 const overviewUri=overview.photo?.uri??initial?.uris[1];
 const details:ReportDetails={site:site.trim(),landmark:landmark.trim(),extent,observed_on:date,notes:notes.trim(),request_key:requestKey,identify_requested:original?.identify_requested??Boolean(prediction),identification_questioned:questioned,site_id:siteId||null,block_id:blockId||null,latitude:mapPoint?.latitude??null,longitude:mapPoint?.longitude??null,location_mode:'osm',map_id:ELMINA_MAP_ID,demo_pin:null};
 const serialized=JSON.stringify(details);
 useEffect(()=>{if(session&&!session.user.must_change_password)void getCatalog(session).then(setCatalog).catch(()=>{});},[session]);
 useEffect(()=>{if(!session||session.user.must_change_password||busy||receipt||queued)return;let active=true;const timer=setTimeout(()=>{const task=chain.current.catch(()=>{}).then(()=>saveDraft({id:requestKey,owner:session.user.id,kind:'report',state:'saved',label:site||'Sighting draft',details:JSON.parse(serialized) as ReportDetails,prediction,uris:[uri,...(overviewUri?[overviewUri]:[])]}));chain.current=task;void task.then(()=>{if(active)setSaved('Draft saved on this device.');}).catch(()=>{if(active)setSaved('Draft could not be saved. Keep this screen open.');});},700);return()=>{active=false;clearTimeout(timer);};},[serialized,uri,overviewUri,session,busy,receipt,queued,requestKey,prediction,site]);
 async function persist(state:'saved'|'queued'){if(!session)return;await chain.current.catch(()=>{});return saveDraft({id:requestKey,owner:session.user.id,kind:'report',state,label:site||'Sighting draft',details,prediction,uris:[uri,...(overviewUri?[overviewUri]:[])]});}
 async function submit(){if(!session||pending.current||overview.selecting)return;const invalid=validateReportDetails(details);if(invalid){setError(invalid);return;}
  pending.current=true;setBusy(true);setError('');try{await persist('queued');try{setReceipt(await sendDraft(session,requestKey));}catch(failure){setQueued(true);if(failure instanceof SessionExpired)endSession(session);setError(failure instanceof Error?failure.message:'Not sent yet. Retry from Drafts.');}}catch{setError('Could not save your report for upload. Check device storage.');}finally{pending.current=false;setBusy(false);}}
 if(receipt||queued)return <View style={styles.body}><Text variant="headlineSmall">{receipt?'Report sent.':'Saved for retry.'}</Text><Text>{receipt?.reference??'Your report has not been confirmed as received.'}</Text>{!!error&&<Text style={styles.error}>{error}</Text>}<Text style={styles.hint}>{receipt?'Management will review your sighting.':'Keep the app open to retry automatically, or open Drafts after signing in.'}</Text>{queued&&<Button mode="outlined" onPress={()=>router.replace('/drafts')}>Open drafts</Button>}<Button mode="contained" onPress={onDone}>Done</Button></View>;
 if(!session||session.user.must_change_password)return <View style={styles.body}><TeamSignIn/><Button onPress={onCancel}>Back</Button></View>;
 return <View style={styles.body}><Text accessibilityRole="header" style={styles.title}>Report sighting.</Text><Image source={{uri}} style={styles.overview} resizeMode="contain" accessibilityLabel="Sighting photo"/>
 <View style={styles.summary}><Text variant="titleMedium">{prediction?.common_name??'Plant to be reviewed'}</Text><Text style={styles.hint}>{prediction?.predicted_species??'The ecology team can inspect this sighting.'}</Text></View>
 {prediction&&<CheckField label="I am unsure about this match" checked={questioned} onChange={setQuestioned} disabled={busy}/>}
 {(catalog.sites.length>0||!!siteId)&&<SelectField label="Site" value={siteId} disabled={busy} options={[{value:'',label:'Other site'},...catalog.sites.map(item=>({value:item.id,label:item.name}))]} onChange={id=>{setSiteId(id);setBlockId('');setSite(catalog.sites.find(item=>item.id===id)?.name??'');}}/>}
 {!siteId&&<TextInput label="Site or block" accessibilityLabel="Site or block" mode="outlined" value={site} onChangeText={setSite} maxLength={100} disabled={busy}/>}
 {siteId&&(!!blockId||catalog.blocks.some(item=>item.site_id===siteId))&&<SelectField label="Block (optional)" value={blockId} disabled={busy} options={[{value:'',label:'No block'},...catalog.blocks.filter(item=>item.site_id===siteId).map(item=>({value:item.id,label:item.name}))]} onChange={setBlockId}/>}
 <TextInput label="Nearby landmark" accessibilityLabel="Nearby landmark" mode="outlined" value={landmark} onChangeText={setLandmark} maxLength={200} disabled={busy}/>
 <Text>How much is there?</Text><View style={styles.choices}>{([['one','One plant'],['few','A few plants'],['patch','A patch'],['unsure','Not sure']] as [Extent,string][]).map(([value,label])=><Chip key={value} selected={extent===value} onPress={()=>setExtent(value)} disabled={busy}>{label}</Chip>)}</View>
 <TextInput label="Observed on (YYYY-MM-DD)" accessibilityLabel="Observed on (YYYY-MM-DD)" mode="outlined" value={date} onChangeText={setDate} maxLength={10} disabled={busy}/>
 <TextInput label="Note (optional)" accessibilityLabel="Note (optional)" mode="outlined" value={notes} onChangeText={setNotes} maxLength={1200} multiline disabled={busy}/>
 <View style={styles.summary}><Text variant="titleMedium">Plant location</Text><Text style={styles.hint}>{mapPoint?'Location pinned near Elmina Lakeside Mall.':original?.demo_pin?'Older image-map draft. Pin the plant again on the live map.':'Pin where the plant was found.'}</Text><Button mode="outlined" disabled={busy} onPress={()=>setPickerOpen(true)}>{mapPoint?'Change plant location':'Pin plant location'}</Button></View>
 {pickerOpen&&<DemoLocationPicker initial={mapPoint} onCancel={()=>setPickerOpen(false)} onDone={pin=>{setMapPoint(pin);setPickerOpen(false);setError('');}}/>}
 {overviewUri&&<Image source={{uri:overviewUri}} style={styles.overview} accessibilityLabel="Overview photo" resizeMode="contain"/>}<Button mode="outlined" disabled={busy||overview.selecting} onPress={()=>{void overview.selectPhoto('gallery');}}>{overviewUri?'Change overview photo':'Add overview photo (optional)'}</Button>
 {!!(error||overview.error)&&<Text accessibilityLiveRegion="assertive" style={styles.error}>{error||overview.error}</Text>}<Text style={styles.hint}>{saved||'A draft will be saved on this device.'}</Text><Text style={styles.hint}>Sending saves these photos and details for ecology review.</Text>
 <Button mode="contained" loading={busy} disabled={busy||overview.selecting||!mapPoint} contentStyle={{minHeight:52}} onPress={()=>{void submit();}}>Submit report</Button><Button disabled={busy} onPress={()=>{setBusy(true);void persist('saved').then(()=>router.replace('/drafts')).catch(()=>setError('Could not save draft.')).finally(()=>setBusy(false));}}>Save & finish later</Button><Button disabled={busy} onPress={onCancel}>Back</Button></View>;
}
const styles=StyleSheet.create({body:{gap:16,paddingBottom:12},title:{fontSize:26,fontWeight:'600',color:colors.text},hint:{fontSize:14,lineHeight:22,color:colors.muted},summary:{padding:14,borderRadius:10,backgroundColor:colors.paleGreen,gap:4},choices:{flexDirection:'row',flexWrap:'wrap',gap:8},overview:{width:'100%',height:180},error:{color:'#943A31',lineHeight:22}});
