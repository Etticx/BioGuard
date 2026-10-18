import { Redirect, usePathname } from 'expo-router';
import { useEffect, useState } from 'react';

import { Platform, StyleSheet, View } from 'react-native';

import { Button, Text, TextInput } from 'react-native-paper';

import { useTeamSession } from '../hooks/useTeamSession';

import { PasswordChange } from './PasswordChange';

import { base, signIn } from '../services/reports';

import { colors } from '../theme';
import { canonicalWebEntry } from '../services/roleAccess';

export function TeamSignIn() {

  const { session, setSession, restoring } = useTeamSession();

  const [username, setUsername] = useState(''); const [password, setPassword] = useState('');

  const [busy, setBusy] = useState(false); const [error, setError] = useState('');

  const pathname = usePathname();
  const entry = Platform.OS === 'web' && typeof window !== 'undefined' ? canonicalWebEntry(base, window.location.origin, process.env.EXPO_PUBLIC_PRIVATE_BETA === '1') : null;
  useEffect(() => { if (entry) window.location.replace(entry); }, [entry]);

  async function submit() {

    if (busy) return; setBusy(true); setError('');

    try { setSession(await signIn(username.trim(), password)); setPassword(''); }

    catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not sign in.'); }

    finally { setBusy(false); }

  }

  if(!restoring && !session && pathname !== '/')return <Redirect href="/"/>;

  if(entry)return <Text>Opening BioGuard sign in…</Text>;

  if(restoring)return <Text>Opening your team session…</Text>;

  if(session?.user.must_change_password)return <PasswordChange/>;

  return <View style={styles.body}>

    <Text accessibilityRole="header" style={styles.title}>Sign in.</Text>

    <Text style={styles.hint}>Your account opens your workspace.</Text>

    <TextInput mode="outlined" label="Username" accessibilityLabel="Username" value={username} onChangeText={setUsername}

      autoCapitalize="none" autoCorrect={false} autoComplete="username" disabled={busy} />

    <TextInput mode="outlined" label="Password" accessibilityLabel="Password" value={password} onChangeText={setPassword}

      secureTextEntry autoComplete="current-password" disabled={busy} onSubmitEditing={() => { void submit(); }} />

    {error ? <Text accessibilityLiveRegion="polite" style={styles.error}>{error}</Text> : null}

    <Button mode="contained" disabled={busy || !username.trim() || !password} loading={busy}

      contentStyle={styles.button} onPress={() => { void submit(); }}>Sign in</Button>

  </View>;

}

const styles = StyleSheet.create({body:{gap:16},title:{fontSize:26,lineHeight:34,fontWeight:'600',color:colors.text},

  hint:{fontSize:15,lineHeight:23,color:colors.muted},error:{color:'#943A31',lineHeight:22},button:{minHeight:52}});

