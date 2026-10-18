import { useCallback, useEffect, useState } from 'react';
import { Image, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Card, Text, TextInput } from 'react-native-paper';
import { useIdentification } from '../hooks/useIdentification';
import { useTeamSession } from '../hooks/useTeamSession';
import { reportStatuses, type FieldReport } from '../services/reportContract';
import { addInformation, getReports, privatePhoto, SessionExpired } from '../services/reports';
import { Redirect, router, useFocusEffect } from 'expo-router';
import { WorkVisit } from './WorkVisit';
import { ActionButton as Button } from './ActionButton';
import { AccountActions } from './AccountActions';
import { Glyph } from './Glyph';
import { colors } from '../theme';
import { TeamSignIn } from './TeamSignIn';
import { ecologyJobGroup, ecologyJobLabel, type EcologyJobGroup } from '../services/ecologyJobs';
function Evidence({ path, label }: { path: string; label: string }) {
  const {session}=useTeamSession(); const [uri,setUri]=useState(''); const [failed,setFailed]=useState(false);
  useEffect(()=>{let cancelled=false;if(session)void privatePhoto(session,path).then(value=>{if(!cancelled)setUri(value);}).catch(()=>{if(!cancelled)setFailed(true);});return()=>{cancelled=true;};},[session,path]);
  return uri?<Image source={{uri}} style={styles.photo} resizeMode="contain" accessibilityLabel={label}/>:failed?<Text>Photo unavailable.</Text>:<ActivityIndicator/>;
}
export function TeamReports({ onBack, initialReportId, draftId, home = false }: {onBack:()=>void;initialReportId?:string;draftId?:string;home?:boolean}) {
  const {session,endSession}=useTeamSession();const [reports,setReports]=useState<FieldReport[]>([]);
  const [group,setGroup]=useState<EcologyJobGroup>('active');
  const [selected,setSelected]=useState<FieldReport|null>(null);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
  const extra=useIdentification();const [notes,setNotes]=useState('');const [sending,setSending]=useState(false);
  async function refresh(){if(!session||session.user.must_change_password)return;setLoading(true);setError('');try{const items=await getReports(session);setReports(items);setSelected(previous=>previous?items.find(item=>item.id===previous.id)??null:null);}catch(failure){if(failure instanceof SessionExpired)endSession(session);setError(failure instanceof Error?failure.message:'Could not load reports.');}finally{setLoading(false);}}
  useFocusEffect(useCallback(()=>{if(!session||session.user.must_change_password)return;let cancelled=false;void getReports(session).then(items=>{if(!cancelled){setReports(items);if(initialReportId){const report=items.find(item=>item.id===initialReportId);setSelected(report??null);if(!report)setError('This report is no longer available to your account. Your local draft has been kept.');}else setSelected(previous=>previous?items.find(item=>item.id===previous.id)??null:null);}}).catch(failure=>{if(!cancelled){if(failure instanceof SessionExpired)endSession(session);setError(failure instanceof Error?failure.message:'Could not load reports.');}}).finally(()=>{if(!cancelled)setLoading(false);});return()=>{cancelled=true;};},[session,endSession,initialReportId]));
  async function sendMore(){if(!session||!selected||!extra.photo||sending)return;setSending(true);setError('');try{const updated=await addInformation(session,selected,extra.photo.uri,notes);setSelected(updated);extra.reset();setNotes('');await refresh();}catch(failure){if(failure instanceof SessionExpired)endSession(session);setError(failure instanceof Error?failure.message:'Could not add information.');}finally{setSending(false);}}
  if(!session)return <Redirect href="/"/>;
  if(session.user.must_change_password)return <TeamSignIn/>;
  const ecology=session.user.role==='ecology';
  const counts={active:0,review:0,past:0};
  if(ecology)for(const report of reports)counts[ecologyJobGroup(report,session.user.team_id)]++;
  const visibleReports=ecology?reports.filter(report=>ecologyJobGroup(report,session.user.team_id)===group):reports;
  const groupNames={active:'Active jobs',review:'Awaiting review',past:'Past jobs'};
  const emptyNames={active:'No active jobs.',review:'Nothing awaiting review.',past:'No past jobs.'};
  const emptyHints={active:'Submitted and completed work stays in the other tabs.',review:'Work you send to management will appear here.',past:'Approved, closed or cancelled work will appear here.'};
  return <View style={styles.body}>
    <View style={styles.top}>
      <Text accessibilityRole="header" style={styles.title}>{selected?(session.user.role==='ecology'?'Job details.':'Report details.'):session.user.role==='ecology'?'My jobs.':'My sightings.'}</Text>
      {(!home||selected)&&<Button compact disabled={sending} icon={({size,color})=><Glyph name="back" size={size} color={color}/>} onPress={()=>{if(selected&&initialReportId){onBack();}else if(selected){setSelected(null);extra.reset();setNotes('');setError('');}else onBack();}}>Back</Button>}
    </View>
    {error&&<Text style={styles.error} accessibilityLiveRegion="polite">{error}</Text>}
    {selected?<>
      <Text style={styles.reference}>{selected.reference} · {reportStatuses[selected.status]}</Text>
      <Text style={styles.subtitle}>{selected.site}</Text><Text>{selected.landmark}</Text>
      {selected.photos.map(photo=><Evidence key={photo.id} path={photo.url} label={photo.kind==='work_evidence'?'Work evidence photo':'Sighting photo'}/>)}
      <Text style={styles.subtitle}>{selected.prediction?.common_name??'Plant to be reviewed'}</Text><Text style={styles.hint}>Model suggestion · {selected.prediction?.predicted_species??'Pending identification'}</Text>
      {selected.review&&!selected.work_items.length&&<View style={styles.plan}><Text style={styles.subtitle}>Management review</Text><Text>{selected.review.notes}</Text></View>}
      {(session.user.role==='ecology'?[...selected.work_items].filter(work=>work.team_id===session.user.team_id):[]).sort((a,b)=>Number(['verified','cancelled'].includes(a.status))-Number(['verified','cancelled'].includes(b.status))).map(work=><WorkVisit key={work.id+':'+work.revision+':'+(draftId??'')} work={work} draftId={draftId} onUpdate={updated=>{setSelected(updated);setReports(previous=>previous.map(item=>item.id===updated.id?updated:item));}}/>)}
      {selected.status==='needs_info'&&selected.reporter_id===session.user.id&&<>
        <Text style={styles.subtitle}>Add the requested information.</Text>
        <Button mode="outlined" disabled={sending||extra.selecting} onPress={()=>{void extra.selectPhoto('gallery');}}>{extra.photo?'Change additional photo':'Choose additional photo'}</Button>
        {extra.photo&&<Image source={{uri:extra.photo.uri}} style={styles.photo} resizeMode="contain" accessibilityLabel="Additional evidence preview"/>}
        <TextInput label="Note (optional)" accessibilityLabel="Note (optional)" value={notes} onChangeText={setNotes} mode="outlined" multiline maxLength={1200} disabled={sending}/>
        {extra.error&&<Text style={styles.error}>{extra.error}</Text>}
        <Button mode="contained" disabled={sending||!extra.photo||extra.selecting} loading={sending} onPress={()=>{void sendMore();}}>Send for review</Button>
      </>}
      <Button icon={({size,color})=><Glyph name="refresh" size={size} color={color}/>} disabled={loading||sending} onPress={()=>{void refresh();}}>Refresh report</Button>
    </>:<>
      <Text style={styles.hint}>{session.user.display_name}</Text>
      {home&&session.user.role==='ecology'&&<AccountActions disabled={sending}/>}
      <View style={styles.tools}>
        <Button mode="contained-tonal" style={styles.tool} icon={({size,color})=><Glyph name="drafts" size={size} color={color}/>} onPress={()=>router.push('/drafts')}>Drafts</Button>
        <Button mode="contained-tonal" style={styles.tool} icon={({size,color})=><Glyph name="updates" size={size} color={color}/>} onPress={()=>router.push('/updates')}>Updates</Button>
      </View>
      <Button icon={({size,color})=><Glyph name="refresh" size={size} color={color}/>} loading={loading} disabled={loading} onPress={()=>{void refresh();}}>Refresh</Button>
      {loading&&<ActivityIndicator/>}
      {ecology&&<>
        <View style={styles.filters}>{(['active','review','past'] as const).map(value=><Button key={value} compact mode={group===value?'contained':'outlined'} style={styles.filter} labelStyle={styles.filterLabel} accessibilityLabel={`${groupNames[value]}, ${counts[value]} jobs`} accessibilityState={{selected:group===value}} onPress={()=>setGroup(value)}>{value==='active'?'Active':value==='review'?'Review':'Past jobs'}</Button>)}</View>
        <Text style={styles.hint} accessibilityLiveRegion="polite">{groupNames[group]} · {counts[group]}</Text>
      </>}
      {!loading&&!visibleReports.length&&<View style={styles.empty}><Text style={styles.subtitle}>{ecology?emptyNames[group]:'No sightings yet.'}</Text><Text style={styles.hint}>{ecology?emptyHints[group]:'Your team’s reports will appear here.'}</Text></View>}
      {visibleReports.map(report=><Card key={report.id} mode="outlined" style={styles.card}>
        <Card.Content style={styles.body}><Text style={styles.reference}>{report.reference} · {ecology?ecologyJobLabel(report,session.user.team_id):reportStatuses[report.status]}</Text>
          <Text style={styles.subtitle}>{report.site}</Text><Text>{report.landmark}</Text>
          <Text style={styles.hint}>{report.prediction?.common_name??'Plant to be reviewed'}</Text><Button mode="contained-tonal" icon={({size,color})=><Glyph name="arrow" size={size} color={color}/>} onPress={()=>{setSelected(report);setError('');}}>{session.user.role==='ecology'?'Open job':'Open sighting'}</Button></Card.Content></Card>)}
    </>}
  </View>;
}
const styles=StyleSheet.create({body:{gap:14,paddingBottom:8},top:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',justifyContent:'space-between',gap:8},
  title:{fontSize:24,lineHeight:32,fontWeight:'600',color:colors.text},subtitle:{fontSize:18,lineHeight:26,fontWeight:'600',color:colors.text},
  hint:{fontSize:14,lineHeight:22,color:colors.muted},reference:{fontSize:13,lineHeight:21,color:colors.muted},
  filters:{flexDirection:'row',gap:8},filter:{flex:1,minWidth:0},filterLabel:{marginHorizontal:6},
  tools:{flexDirection:'row',flexWrap:'wrap',gap:12},tool:{flex:1,minWidth:140},empty:{padding:20,gap:8,borderRadius:14,borderWidth:1,borderColor:colors.border,backgroundColor:colors.surface},
  label:{fontSize:14,fontWeight:'600',marginTop:8},plan:{padding:16,gap:8,borderRadius:12,backgroundColor:colors.paleGreen},
  photo:{width:'100%',height:230,borderRadius:10,backgroundColor:colors.surface},card:{backgroundColor:colors.surface},error:{color:'#943A31',lineHeight:22}});
