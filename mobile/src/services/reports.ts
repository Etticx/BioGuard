import { SessionExpired, RequestError } from './requestErrors';
import { parseSession, parseUser, sessionHeaders } from './roleAccess';
import Constants from 'expo-constants';
import { File } from 'expo-file-system';
import { fetch } from 'expo/fetch';
import { Platform } from 'react-native';
import { resolveApiUrl } from './contract';
import { parseReport, type FieldReport, type ReportDetails, type Session, type Completion, type WorkItem, type Notice, type Catalog } from './reportContract';

export const base = resolveApiUrl(process.env.EXPO_PUBLIC_API_URL, Constants.expoConfig?.hostUri);
export { SessionExpired, RequestError } from './requestErrors';
export async function request(path: string, session?: Session, options: RequestInit = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(base + path, { credentials: 'same-origin', ...options, signal: controller.signal,
      headers: { Accept: 'application/json', ...sessionHeaders(session), ...options.headers } });
    if (!response.ok) {
      let message = 'Could not complete this action. Please retry.';
      try { const body = await response.json() as { detail?: unknown }; if (typeof body.detail === 'string') message = body.detail; } catch {}
      if (response.status === 401 && session) throw new SessionExpired('Your session ended. Sign in again.');
      throw new RequestError(message,response.status);
    }
    return response;
  } finally { clearTimeout(timer); }
}
export async function signIn(username: string, password: string): Promise<Session> {
  const response = await request('/auth/login', undefined, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
  return parseSession(await response.json());
}
export async function signOut(session: Session) { await request('/auth/logout', session, { method: 'POST' }); }
async function photo(uri: string) {
  const file = Platform.OS === 'web' ? await (await fetch(uri)).blob() : new File(uri);
  if (file.size > 12 * 1024 * 1024) throw new Error('This photo is too large. Choose a smaller photo.');
  return file;
}
export async function submitReport(session: Session, details: ReportDetails, uri: string, overview?: string) {
  const body = new FormData(); body.append('details', JSON.stringify(details));
  body.append('photo', await photo(uri), 'plant.jpg');
  if (overview) body.append('overview', await photo(overview), 'overview.jpg');
  return parseReport(await (await request('/reports', session, { method: 'POST', body })).json());
}
export async function getReports(session: Session): Promise<FieldReport[]> {
  const value: unknown = await (await request('/reports', session)).json();
  if (!Array.isArray(value)) throw new Error('Could not read the reports.');
  return value.map(parseReport);
}
export async function addInformation(session: Session, report: FieldReport, uri: string, notes: string) {
  const body = new FormData(); body.append('revision', String(report.revision)); body.append('notes', notes);
  body.append('photo', await photo(uri), 'additional.jpg');
  return parseReport(await (await request(`/reports/${report.id}/information`, session, { method: 'POST', body })).json());
}
export async function privatePhoto(session: Session, path: string): Promise<string> {
  const blob = await (await request(path, session)).blob();
  return new Promise((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('Could not load the photo.')); reader.readAsDataURL(blob);
  });
}

export async function me(session?:Session){return parseUser(await (await request('/auth/me',session)).json());}
export async function changePassword(session:Session,current_password:string,new_password:string){await request('/auth/password',session,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password,new_password})});}
export async function getCatalog(session:Session):Promise<Catalog>{return (await request('/catalog',session)).json() as Promise<Catalog>;}
export async function getNotices(session:Session):Promise<Notice[]>{return (await request('/notifications',session)).json() as Promise<Notice[]>;}
export async function readNotice(session:Session,id:string){await request(`/notifications/${id}/read`,session,{method:'POST'});}
export async function progressWork(session:Session,work:WorkItem,action:'accept'|'start'|'blocked',notes:string){return parseReport(await (await request(`/reports/${work.report_id}/work/${work.id}/progress`,session,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:work.revision,action,notes})})).json());}
export async function submitCompletion(session:Session,reportId:string,workId:string,details:Completion,uri:string,overview?:string){
 const body=new FormData();body.append('details',JSON.stringify(details));body.append('photo',await photo(uri),'evidence.jpg');if(overview)body.append('overview',await photo(overview),'overview.jpg');
 return parseReport(await (await request(`/reports/${reportId}/work/${workId}/complete`,session,{method:'POST',body})).json());
}
