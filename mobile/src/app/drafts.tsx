import { ActionButton as Button } from '../components/ActionButton';
import { useCallback, useState } from 'react';

import { View } from 'react-native';

import { Card, Text } from 'react-native-paper';

import { router, useFocusEffect } from 'expo-router';

import { ScreenShell } from '../components/ScreenShell';

import { TeamSignIn } from '../components/TeamSignIn';

import { useTeamSession } from '../hooks/useTeamSession';

import { listDrafts, removeDraft } from '../services/draftStore';

import { sendDraft } from '../services/outbox';

import { SessionExpired } from '../services/reports';

import type { Draft } from '../services/draftTypes';
import { mayEditReport } from '../services/draftRecovery';

export default function DraftsScreen(){const {session,endSession}=useTeamSession();const [items,setItems]=useState<Draft[]>([]);const [error,setError]=useState('');const [busy,setBusy]=useState('');const [discard,setDiscard]=useState('');const refresh=useCallback(async()=>{if(session)setItems(await listDrafts(session.user.id));},[session]);useFocusEffect(useCallback(()=>{void refresh().catch(()=>setError('Could not open drafts.'));const timer=setInterval(()=>{void refresh().catch(()=>{});},5000);return()=>clearInterval(timer);},[refresh]));

 if(!session||session.user.must_change_password)return <ScreenShell><TeamSignIn/></ScreenShell>;

 return <ScreenShell><View style={{gap:16}}><Text variant="headlineSmall">Drafts & uploads.</Text><Text>Saved on this device for your account.</Text>{!!error&&<Text accessibilityLiveRegion="polite">{error}</Text>}{!items.filter(item=>item.owner===session.user.id).length&&<Text>No saved drafts.</Text>}{items.filter(item=>item.owner===session.user.id).map(item=><Card key={item.id} mode="outlined"><Card.Content style={{gap:12}}><Text variant="titleMedium">{item.label}</Text><Text>{item.state==='queued'?'Waiting to send':item.state==='attention'?'Needs attention':'Draft saved'} · {new Date(item.updated).toLocaleString()}</Text>{!!item.error&&<Text>{item.error}</Text>}{mayEditReport(item)&&<Button disabled={!!busy} onPress={()=>router.push({pathname:'/report',params:{id:item.id}})}>Continue report</Button>}{item.state==='queued'&&<Button disabled={!!busy} loading={busy===item.id} mode="contained" onPress={()=>{setBusy(item.id);setError('');void sendDraft(session,item.id).then(()=>setError('Sent successfully.')).catch(e=>{if(e instanceof SessionExpired)endSession(session);setError(e instanceof Error?e.message:'Not sent yet.');}).finally(()=>{setBusy('');void refresh();});}}>Retry now</Button>}{item.kind==='completion'&&item.state!=='queued'&&<Button onPress={()=>router.push({pathname:'/team',params:{reportId:item.reportId,draftId:item.id}})}>Open saved evidence</Button>}{item.state==='attention'&&<Text>Check your sightings or jobs for a receipt first. Reopen this report to correct it, or open team work to review saved evidence against the latest visit instructions.</Text>}{discard===item.id?<><Text>Discard this local draft and its copied photos?</Text><Button disabled={!!busy} onPress={()=>{void removeDraft(session.user.id,item.id).then(()=>{setDiscard('');void refresh();}).catch(()=>setError('Could not discard draft.'));}}>Discard draft</Button><Button onPress={()=>setDiscard('')}>Keep draft</Button></>:<Button disabled={!!busy} onPress={()=>setDiscard(item.id)}>Discard</Button>}</Card.Content></Card>)}<Text>Queued uploads retry while the app is open and you are signed in. Keep drafts until you see a report receipt.</Text><Button onPress={()=>router.dismissTo(session.user.role==='ecology'?'/':'/team')}>{session.user.role==='ecology'?'Back to jobs':'Back to sightings'}</Button></View></ScreenShell>;

}

