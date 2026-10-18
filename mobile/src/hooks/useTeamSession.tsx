import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import type { Session } from '../services/reportContract';
import { me } from '../services/reports';
import { parseSession, shouldForgetSession } from '../services/roleAccess';
const key=process.env.EXPO_PUBLIC_PRIVATE_BETA==='1'?'bioguard.beta.session.v1':'bioguard.session.v1';
const Context = createContext<{ session: Session | null; setSession: (session: Session | null) => void; endSession: (expected: Session) => boolean; restoring:boolean } | null>(null);
export function TeamSessionProvider({ children }: { children: ReactNode }) {
 const [session,update]=useState<Session|null>(null);const [restoring,setRestoring]=useState(true);const generation=useRef(0);const activeSession=useRef<Session|null>(null);
 const setSession=useCallback((value:Session|null)=>{generation.current++;activeSession.current=value;update(value);if(Platform.OS!=='web')void(value?SecureStore.setItemAsync(key,JSON.stringify(value),{keychainAccessible:SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY}):SecureStore.deleteItemAsync(key)).catch(()=>{});},[]);
 const endSession=useCallback((expected:Session)=>{if(activeSession.current!==expected)return false;setSession(null);return true;},[setSession]);
 useEffect(()=>{let alive=true;const initial=generation.current;
  async function restore(){
   if(Platform.OS==='web'){
    try{const user=await me();if(alive&&initial===generation.current){const value={token:'',user};activeSession.current=value;update(value);}}catch{/* A new browser session starts at sign in. */}
    return;
   }
   const value=await SecureStore.getItemAsync(key);if(!value)return;
   let stored:Session;
   try{stored=parseSession(JSON.parse(value));}catch{await SecureStore.deleteItemAsync(key);return;}
   try{stored.user=await me(stored);}catch(error){
    if(shouldForgetSession(error)){await SecureStore.deleteItemAsync(key);return;}
    // Preserve a validated saved session through a temporary network interruption.
   }
   if(alive&&initial===generation.current){activeSession.current=stored;update(stored);}
  }
  void restore().catch(()=>{}).finally(()=>{if(alive)setRestoring(false);});return()=>{alive=false;};},[]);
 return <Context.Provider value={{session,setSession,endSession,restoring}}>{children}</Context.Provider>;
}
export function useTeamSession(){const context=useContext(Context);if(!context)throw new Error('Team session provider missing');return context;}
