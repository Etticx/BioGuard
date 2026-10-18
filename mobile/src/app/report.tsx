import { useEffect, useState } from 'react';

import { Redirect, router, useLocalSearchParams } from 'expo-router';

import { Text } from 'react-native-paper';

import { ReportForm } from '../components/ReportForm';

import { ScreenShell } from '../components/ScreenShell';

import { TeamSignIn } from '../components/TeamSignIn';

import { useScan } from '../hooks/useScan';

import { useTeamSession } from '../hooks/useTeamSession';

import { openDraft, releaseDraft } from '../services/draftStore';

import type { Draft } from '../services/draftTypes';
import { mayEditReport } from '../services/draftRecovery';

export default function ReportScreen(){const {photo,result,reset}=useScan();const {session}=useTeamSession();const {id}=useLocalSearchParams<{id?:string}>();const [draft,setDraft]=useState<Draft|null>(null);const [error,setError]=useState('');

 useEffect(()=>{if(!id||!session)return;let active=true;let opened:Draft|null=null;void openDraft(session.user.id,id).then(item=>{opened=item;if(active){if(!item||!mayEditReport(item))setError('Open queued reports from Drafts.');else setDraft(item);}}).catch(()=>setError('Could not open draft.'));return()=>{active=false;if(opened)releaseDraft(opened);};},[id,session]);

 if(session&&session.user.role!=='ground')return <Redirect href="/"/>;

 if(id&&!session)return <ScreenShell><TeamSignIn/></ScreenShell>;

 if(id&&(!draft||draft.owner!==session?.user.id))return <ScreenShell><Text>{error||'Opening draft…'}</Text></ScreenShell>;

 if(!id&&!photo)return <Redirect href="/"/>;

 return <ScreenShell><ReportForm key={(id??photo!.uri)+':'+(session?.user.id??'signed-out')} uri={draft?.uris[0]??photo!.uri} prediction={draft?(draft.prediction??null):result} initial={draft??undefined} onCancel={()=>{if(router.canGoBack())router.back();else router.replace('/');}} onDone={()=>{reset();router.replace('/team');}}/></ScreenShell>;

}

