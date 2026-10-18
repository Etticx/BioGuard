import type { Session, FieldReport } from './reportContract';
import type { Draft } from './draftTypes';
import { mayRetry } from './draftTypes';
import { unusedPhotoDraft } from './visitPhotos';
import { RequestError, SessionExpired } from './requestErrors';
export type UploadStorage={open:(owner:string,id:string)=>Promise<Draft|null>;save:(draft:Draft)=>Promise<unknown>;remove:(owner:string,id:string)=>Promise<void>;release:(draft:Draft)=>void;upload:(session:Session,draft:Draft)=>Promise<FieldReport>};
export async function uploadDraft(session:Session,id:string,storage:UploadStorage){let draft:Draft|null=null;
 try{draft=await storage.open(session.user.id,id);if(!draft||draft.owner!==session.user.id){draft=null;throw new Error('Draft not found.');}if(!mayRetry(draft.state)){draft=null;throw new Error('Open this saved draft before sending.');}
 const result=await storage.upload(session,draft);
 const remaining=unusedPhotoDraft(draft);
 if(remaining){const existing=await storage.open(session.user.id,remaining.id);if(existing)storage.release(existing);else await storage.save(remaining);}
 await storage.remove(session.user.id,id);return result;
 }catch(error){if(draft){const failed=error instanceof RequestError&&error.status>=400&&error.status<500;await storage.save({...draft,state:failed?'attention':'queued',error:error instanceof SessionExpired?'Sign in again to retry.':failed?(error as Error).message:'Not sent yet. We will retry while the app is open.'});}throw error;
 }finally{if(draft)storage.release(draft);}}
