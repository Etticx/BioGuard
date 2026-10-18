import { ActionButton as Button } from '../components/ActionButton';
import { useEffect, useState } from 'react';

import { View } from 'react-native';

import { Card, Text } from 'react-native-paper';

import { router } from 'expo-router';

import { ScreenShell } from '../components/ScreenShell';

import { TeamSignIn } from '../components/TeamSignIn';

import { useTeamSession } from '../hooks/useTeamSession';

import { getNotices, readNotice, SessionExpired } from '../services/reports';

import type { Notice } from '../services/reportContract';

export default function UpdatesScreen(){const {session,endSession}=useTeamSession();const [items,setItems]=useState<Notice[]>([]);const [owner,setOwner]=useState('');const [error,setError]=useState('');useEffect(()=>{if(!session||session.user.must_change_password)return;let alive=true;const run=()=>{void getNotices(session).then(value=>{if(alive){setItems(value);setOwner(session.user.id);}}).catch(e=>{if(e instanceof SessionExpired)endSession(session);if(alive)setError('Could not load updates.');});};run();const timer=setInterval(run,30000);return()=>{alive=false;clearInterval(timer);};},[session,endSession]);if(!session||session.user.must_change_password)return <ScreenShell><TeamSignIn/></ScreenShell>;return <ScreenShell><View style={{gap:16}}><Text variant="headlineSmall">Team updates.</Text><Text>New assignments, changed plans and overdue visits.</Text>{!!error&&<Text>{error}</Text>}{!(owner===session.user.id?items:[]).length&&<Text>No updates yet.</Text>}{(owner===session.user.id?items:[]).map(item=><Card key={item.id} mode="outlined"><Card.Content style={{gap:10}}><Text>{item.message}</Text><Text>{new Date(item.created_at).toLocaleString()}{!item.read_at?' · Unread':''}</Text>{!item.read_at&&<Button onPress={()=>{void readNotice(session,item.id).then(()=>setItems(previous=>previous.map(n=>n.id===item.id?{...n,read_at:new Date().toISOString()}:n))).catch(()=>setError('Could not mark as read.'));}}>Mark as read</Button>}{item.report_id&&<Button onPress={()=>router.push({pathname:'/team',params:{reportId:item.report_id!}})}>{session.user.role==='ecology'?'Open job':'Open sighting'}</Button>}</Card.Content></Card>)}<Button onPress={()=>router.dismissTo(session.user.role==='ecology'?'/':'/team')}>{session.user.role==='ecology'?'Back to jobs':'Back to sightings'}</Button></View></ScreenShell>;}

