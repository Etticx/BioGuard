import { ActionButton as Button } from './ActionButton';
import { useState } from 'react';
import { View } from 'react-native';
import { Text, TextInput } from 'react-native-paper';
import { useTeamSession } from '../hooks/useTeamSession';
import { SessionExpired, changePassword } from '../services/reports';
export function PasswordChange({onCancel}:{onCancel?:()=>void}){
 const {session,endSession}=useTeamSession();const [current,setCurrent]=useState('');const [password,setPassword]=useState('');const [confirm,setConfirm]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function save(){if(!session)return;if(password.length<10||password!==confirm){setError('Use at least 10 characters and matching passwords.');return;}setBusy(true);try{await changePassword(session,current,password);endSession(session);}catch(e){if(e instanceof SessionExpired)endSession(session);else setError(e instanceof Error?e.message:'Could not change password.');}finally{setBusy(false);}}
 return <View style={{gap:16}}><Text variant="headlineSmall">Change password.</Text><Text>Sign in again after saving.</Text><TextInput label="Current password" accessibilityLabel="Current password" secureTextEntry value={current} onChangeText={setCurrent}/><TextInput label="New password" accessibilityLabel="New password" secureTextEntry value={password} onChangeText={setPassword}/><TextInput label="Confirm new password" accessibilityLabel="Confirm new password" secureTextEntry value={confirm} onChangeText={setConfirm}/>{!!error&&<Text accessibilityLiveRegion="polite">{error}</Text>}<Button mode="contained" loading={busy} disabled={busy} onPress={()=>{void save();}}>Save password</Button>{onCancel&&<Button disabled={busy} onPress={onCancel}>Back</Button>}</View>;
}
