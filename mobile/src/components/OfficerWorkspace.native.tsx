import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Text } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { useTeamSession } from '../hooks/useTeamSession';
import { base, SessionExpired, signOut } from '../services/reports';
import { isOfficerPage, officerUrl, sessionHeaders } from '../services/roleAccess';
import { colors } from '../theme';

export function OfficerWorkspace() {
  const { session, endSession } = useTeamSession();
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [attempt, setAttempt] = useState(0);
  const url = officerUrl(base);
  const source = useMemo(() => ({ uri: url, headers: sessionHeaders(session ?? undefined) }), [url, session]);
  if (!session) return null;
  return <SafeAreaView style={styles.screen}>
    <View style={styles.header}><Text variant="titleMedium">BioGuard · Ecology Management</Text><Button onPress={() => {
      void signOut(session).then(() => endSession(session)).catch(failure => { if(failure instanceof SessionExpired)endSession(session);else setError('Could not sign out. Check your connection and retry.'); });
    }}>Log out</Button></View>
    {!!notice && <View style={styles.error}><Text accessibilityLiveRegion="polite">{notice}</Text><Button onPress={() => setNotice('')}>Dismiss</Button></View>}
    {error ? <View style={styles.error}><Text>{error}</Text><Button onPress={() => { setError(''); setAttempt(value => value + 1); }}>Retry</Button></View> :
      <WebView key={attempt} source={source} style={styles.web} incognito cacheEnabled={false}
        originWhitelist={['*']}
        onShouldStartLoadWithRequest={request => {
          if (isOfficerPage(request.url, url)) return true;
          try {
            const target = new URL(request.url);
            if (target.origin === new URL(url).origin && target.pathname.startsWith('/admin/backups/')) {
              setNotice('Download backups from the management dashboard on your laptop.');
            }
          } catch { /* Unrecognised navigation stays blocked. */ }
          return false;
        }}
        onMessage={event => {
          if (isOfficerPage(event.nativeEvent.url, url) && event.nativeEvent.data === 'bioguard:session-ended') endSession(session);
        }}
        onHttpError={event => {
          if (isOfficerPage(event.nativeEvent.url, url) && [401, 403].includes(event.nativeEvent.statusCode)) endSession(session);
          else setError('Could not open management. Please retry.');
        }}
        onError={() => setError('Could not open management. Check your connection and retry.')}
        startInLoadingState />}
  </SafeAreaView>;
}
const styles = StyleSheet.create({screen:{flex:1,backgroundColor:colors.background},header:{paddingHorizontal:16,flexDirection:'row',alignItems:'center',justifyContent:'space-between'},web:{flex:1,backgroundColor:colors.background},error:{padding:24,gap:16}});
