import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { PaperProvider, Text } from 'react-native-paper';
import { PaperIcon } from '../components/PaperIcon';
import { theme } from '../theme';
import { TeamSessionProvider, useTeamSession } from '../hooks/useTeamSession';
import { OutboxSync } from '../hooks/useOutbox';
import { ScanProvider } from '../hooks/useScan';
import { ScreenShell } from '../components/ScreenShell';
import { TeamSignIn } from '../components/TeamSignIn';
import { OfficerWorkspace } from '../components/OfficerWorkspace';
import { workspaceFor } from '../services/roleAccess';

SplashScreen.setOptions({ duration: 250, fade: true });

export default function RootLayout(){return <TeamSessionProvider><SessionApp/></TeamSessionProvider>;}
function SessionApp() {
  const {session,restoring}=useTeamSession();
  const scope=process.env.EXPO_PUBLIC_PRIVATE_BETA==='1'?(session?session.user.id+':'+session.user.role:'signed-out'):'prototype';
  return (
    <ScanProvider key={scope}><PaperProvider theme={theme} settings={{icon:PaperIcon}}>
      <OutboxSync/><StatusBar style="dark" />
      {restoring ? <ScreenShell><Text>Opening BioGuard…</Text></ScreenShell> : session && workspaceFor(session.user)==='password' ? <ScreenShell><TeamSignIn/></ScreenShell> : session?.user.role==='management' ? <OfficerWorkspace/> : <Stack screenOptions={{ headerShown: false, contentStyle: {
        backgroundColor: theme.colors.background,
      } }} />}
    </PaperProvider></ScanProvider>
  );
}
