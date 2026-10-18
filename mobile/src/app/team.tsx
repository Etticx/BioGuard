import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { ScreenShell } from '../components/ScreenShell';
import { useTeamSession } from '../hooks/useTeamSession';
import { TeamReports } from '../components/TeamReports';
export default function TeamScreen() {
  const {session}=useTeamSession();
  const {reportId,draftId}=useLocalSearchParams<{reportId?:string;draftId?:string}>();
  if(!session)return <Redirect href="/"/>;
  if(session.user.role==='ecology'&&!reportId)return <Redirect href="/"/>;
  return <ScreenShell><TeamReports key={(session?.user.id??'signed-out')+':'+(reportId??'')+':'+(draftId??'')} initialReportId={reportId} draftId={draftId} onBack={() => { router.dismissTo(session.user.role==='ground'&&reportId?'/team':'/'); }}/></ScreenShell>;
}
