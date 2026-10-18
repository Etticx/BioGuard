import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { Redirect, router } from 'expo-router';
import { ScreenShell } from '../components/ScreenShell';
import { ActionButton } from '../components/ActionButton';
import { PasswordChange } from '../components/PasswordChange';
import { useTeamSession } from '../hooks/useTeamSession';
import { colors } from '../theme';

export default function SettingsScreen() {
  const { session } = useTeamSession();
  const [changing, setChanging] = useState(false);
  if (!session) return <Redirect href="/" />;
  return <ScreenShell><View style={styles.body}>
    {changing ? <PasswordChange onCancel={() => setChanging(false)} /> : <>
      <Text accessibilityRole="header" style={styles.title}>Settings.</Text>
      <View style={styles.card}><Text variant="titleMedium">{session.user.display_name}</Text><Text style={styles.hint}>@{session.user.username}</Text></View>
      <ActionButton mode="contained-tonal" onPress={() => setChanging(true)}>Change password</ActionButton>
      <ActionButton onPress={() => router.dismissTo('/')}>Back</ActionButton>
    </>}
  </View></ScreenShell>;
}
const styles = StyleSheet.create({ body: { gap: 18 }, title: { fontSize: 26, fontWeight: '600', color: colors.text }, hint: { color: colors.muted }, card: { padding: 18, gap: 6, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, borderRadius: 14 } });
