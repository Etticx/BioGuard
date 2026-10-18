import type { Session, Completion, ReportDetails } from './reportContract';
import { listDrafts, openDraft, releaseDraft, removeDraft, saveDraft } from './draftStore';
import { mayRetry } from './draftTypes';
import { SessionExpired, submitCompletion, submitReport } from './reports';
import { uploadDraft } from './outboxCore';
import { completionPhotoUris } from './visitPhotos';
const active=new Set<string>();
export async function sendDraft(session:Session,id:string){const lock=session.user.id+':'+id;if(active.has(lock))throw new Error('This upload is already running.');active.add(lock);
 try{return await uploadDraft(session,id,{open:openDraft,save:saveDraft,remove:removeDraft,release:releaseDraft,upload:async(s,draft)=>{if(draft.kind==='report')return submitReport(s,draft.details as ReportDetails,draft.uris[0],draft.uris[1]);const uris=completionPhotoUris(draft);return submitCompletion(s,draft.reportId!,draft.workId!,draft.details as Completion,uris[0],uris[1]);}});}finally{active.delete(lock);}}
export async function retryQueued(session:Session){for(const draft of await listDrafts(session.user.id)){if(!mayRetry(draft.state))continue;try{await sendDraft(session,draft.id);}catch(error){if(error instanceof SessionExpired)throw error;}}}
