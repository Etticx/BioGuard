import { useEffect } from 'react';
import { AppState } from 'react-native';
import { useTeamSession } from './useTeamSession';
import { retryQueued } from '../services/outbox';
import { SessionExpired } from '../services/reports';
export function OutboxSync(){const {session,endSession}=useTeamSession();useEffect(()=>{if(!session||!['ground','ecology'].includes(session.user.role)||session.user.must_change_password)return;let busy=false;let alive=true;const run=async()=>{if(busy||AppState.currentState==='background')return;busy=true;try{await retryQueued(session);}catch(e){if(alive&&e instanceof SessionExpired)endSession(session);}finally{busy=false;}};void run();const timer=setInterval(()=>{void run();},30000);const listener=AppState.addEventListener('change',state=>{if(state==='active')void run();});return()=>{alive=false;clearInterval(timer);listener.remove();};},[session,endSession]);return null;}
