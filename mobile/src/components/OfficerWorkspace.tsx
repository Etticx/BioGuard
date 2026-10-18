import { useEffect, useState } from 'react';
import { Button, Text } from 'react-native-paper';
import { ScreenShell } from './ScreenShell';
import { useTeamSession } from '../hooks/useTeamSession';
import { base, SessionExpired, signOut } from '../services/reports';
import { officerUrl } from '../services/roleAccess';

export function OfficerWorkspace() {
  const [error, setError] = useState('');
  const { session, endSession } = useTeamSession();
  useEffect(() => { window.location.replace(officerUrl(base, window.location.origin)); }, []);
  return <ScreenShell><Text>Opening management…</Text>{!!error&&<Text>{error}</Text>}<Button onPress={() => {
    if (session) void signOut(session).then(() => endSession(session)).catch(failure=>{if(failure instanceof SessionExpired)endSession(session);else setError('Could not log out. Please retry.');});
  }}>Log out</Button></ScreenShell>;
}
