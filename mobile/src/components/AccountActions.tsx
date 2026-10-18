import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { router } from 'expo-router';
import { useTeamSession } from '../hooks/useTeamSession';
import { useScan } from '../hooks/useScan';
import { SessionExpired, signOut } from '../services/reports';
import { ActionButton } from './ActionButton';
import { Glyph } from './Glyph';

export function AccountActions({ disabled = false }: { disabled?: boolean }) {
  const { session, endSession } = useTeamSession();
  const { reset } = useScan();
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function logout() {
    if (!session || busy || disabled) return;
    setBusy(true); setError('');
    try { await signOut(session); if (endSession(session)) { reset(); router.dismissTo('/'); } }
    catch (failure) {
      if (failure instanceof SessionExpired) { if (endSession(session)) { reset(); router.dismissTo('/'); } }
      else setError('Could not log out. Check your connection and try again.');
    } finally { setBusy(false); }
  }
  if (!session) return null;
  return <View style={styles.group}>
    <View style={styles.row}>
      <ActionButton style={styles.action} disabled={disabled || busy} icon={({ size, color }) => <Glyph name="settings" size={size} color={color} />} onPress={() => router.push('/settings')}>Settings</ActionButton>
      <ActionButton style={styles.action} disabled={disabled || busy} loading={busy} onPress={() => { void logout(); }}>Log out</ActionButton>
    </View>
    {!!error && <Text accessibilityLiveRegion="polite" style={styles.error}>{error}</Text>}
  </View>;
}
const styles = StyleSheet.create({ group: { gap: 8 }, row: { flexDirection: 'row', gap: 12, flexWrap: 'wrap' }, action: { flex: 1, minWidth: 125 }, error: { color: '#943A31', lineHeight: 22 } });
