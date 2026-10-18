import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';
import type { Draft } from '../src/services/draftTypes';
import { draftKey } from '../src/services/draftTypes';
import { completionPhotoUris, packVisitPhotos, unusedPhotoDraft, visitPhotos } from '../src/services/visitPhotos';
import { recoverVisitDraft } from '../src/services/draftRecovery';
import { uploadDraft, type UploadStorage } from '../src/services/outboxCore';
import type { Completion, FieldReport, Session } from '../src/services/reportContract';

function evidence(stage: Completion['stage'] = 'both'): Draft {
 return {id:'evidence_original',owner:'tester',kind:'completion',state:'saved',updated:'',label:'Restoration',reportId:'report',workId:'job',uris:['removal-photo','planting-photo'],
  details:{revision:3,request_key:'evidence_original',stage,observed_on:'2026-10-18',notes:'Test restoration evidence',removal_complete:true}};
}
const session: Session = {token:'synthetic-token',user:{id:'tester',username:'tester',display_name:'Tester',role:'ecology'}};

test('a positional Both draft restores distinct named removal and planting photos',()=>{
 const photos=visitPhotos(evidence());assert.equal(photos.removal,'removal-photo');assert.equal(photos.planting,'planting-photo');
});
test('Both -> Planting pending -> save -> reopen preserves both photos and queues removal only',()=>{
 const original=evidence();const saved:Draft={...original,...packVisitPhotos(visitPhotos(original)),details:{...original.details,stage:'removal'} as Completion};
 assert.deepEqual(saved.uris,['removal-photo','planting-photo']);assert.equal(visitPhotos(saved).planting,'planting-photo');
 assert.deepEqual(completionPhotoUris(saved),['removal-photo']);
 const finished:Draft={...saved,details:{...saved.details,stage:'replanting'} as Completion};
 assert.deepEqual(completionPhotoUris(finished),['planting-photo']);
 assert.deepEqual(completionPhotoUris({...finished,details:{...finished.details,stage:'both'} as Completion}),['removal-photo','planting-photo']);
});
test('named slots survive storage URI replacement and ordering instead of selecting position zero',()=>{
 const draft:Draft={...evidence('replanting'),uris:['blob:planting-copy','blob:removal-copy'],photoSlots:{removal:1,planting:0}};
 assert.equal(visitPhotos(draft).removal,'blob:removal-copy');assert.deepEqual(completionPhotoUris(draft),['blob:planting-copy']);
});
test('replacing a planting photo leaves the saved removal photo untouched',()=>{
 const original=evidence();const photos=visitPhotos(original);const edited={...original,...packVisitPhotos({...photos,planting:'new-planting-photo'})};
 assert.deepEqual(completionPhotoUris(edited),['removal-photo','new-planting-photo']);
});
test('legacy replanting drafts keep their primary photo and queued positional payloads stay exact',()=>{
 const planting={...evidence('replanting'),uris:['legacy-planting-photo']};
 assert.equal(visitPhotos(planting).planting,'legacy-planting-photo');assert.deepEqual(completionPhotoUris(planting),planting.uris);
 const queued={...evidence('removal'),state:'queued' as const};assert.equal(completionPhotoUris(queued),queued.uris);
});
test('missing named stage photos fail instead of substituting the other evidence photo',()=>{
 const draft={...evidence('replanting'),photoSlots:{removal:0},uris:['removal-only']};
 assert.throws(()=>completionPhotoUris(draft),/add the photo/);
});
test('unused planting evidence gets a saved continuation with a fresh deterministic submission key',()=>{
 const draft={...evidence('removal'),...packVisitPhotos(visitPhotos(evidence())),state:'queued' as const};
 const remaining=unusedPhotoDraft(draft);assert.ok(remaining);assert.equal(remaining.state,'saved');assert.equal(remaining.continuationOf,draft.id);
 assert.notEqual(remaining.details.request_key,draft.details.request_key);assert.equal(remaining.id,remaining.details.request_key);
 assert.equal(unusedPhotoDraft(draft)?.id,remaining.id);assert.deepEqual(remaining.uris,['planting-photo']);assert.deepEqual(completionPhotoUris(remaining),['planting-photo']);
 assert.equal(unusedPhotoDraft({...draft,details:{...draft.details,stage:'both'} as Completion}),null);
});

// Execute the actual native draft-store implementation against in-memory phone files.
function nativeStore(){
 const values=new Map<string,string>(),files=new Map<string,string>();
 class Directory{uri:string;constructor(parent:{uri:string},name:string){this.uri=parent.uri.replace(/\/$/,'')+'/'+name;}create(){}}
 class File{uri:string;constructor(parent:string|Directory,name?:string){this.uri=typeof parent==='string'?parent:parent.uri+'/'+name;}get exists(){return files.has(this.uri);}copy(target:File){assert.ok(this.exists,'A source evidence file must exist');files.set(target.uri,files.get(this.uri)!);}delete(){files.delete(this.uri);}}
 const asyncStorage={getItem:async(key:string)=>values.get(key)??null,setItem:async(key:string,value:string)=>{values.set(key,value);},removeItem:async(key:string)=>{values.delete(key);},getAllKeys:async()=>[...values.keys()],multiGet:async(keys:string[])=>keys.map(key=>[key,values.get(key)??null])};
 const module={exports:{} as Record<string,unknown>};
 const source=ts.transpileModule(readFileSync(new URL('../src/services/draftStore.native.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
 vm.runInNewContext(source,{module,exports:module.exports,require:(name:string)=>name==='@react-native-async-storage/async-storage'?asyncStorage:name==='expo-file-system'?{Directory,File,Paths:{document:{uri:'file:///documents'}}}:{draftKey},Date});
 const store=module.exports as {saveDraft:(draft:Draft)=>Promise<Draft>;openDraft:(owner:string,id:string)=>Promise<Draft|null>;removeDraft:(owner:string,id:string)=>Promise<void>;releaseDraft:(draft:Draft)=>void;listDrafts:(owner:string)=>Promise<Draft[]>};
 return {store,files,values};
}
test('native saves and partial receipts preserve the unused planting file independently of original cleanup',async()=>{
 const f=nativeStore();f.files.set('removal-photo','removal-bytes');f.files.set('planting-photo','planting-bytes');
 const queued=await f.store.saveDraft({...evidence('removal'),...packVisitPhotos(visitPhotos(evidence())),state:'queued'});
 const uploaded:string[][]=[];let lost=true;
 const storage:UploadStorage={open:f.store.openDraft,save:f.store.saveDraft,remove:f.store.removeDraft,release:f.store.releaseDraft,
  upload:async(_,draft)=>{uploaded.push(completionPhotoUris(draft).map(uri=>f.files.get(uri)!));if(lost){lost=false;throw new TypeError('Lost acknowledgement');}return {id:'receipt'} as FieldReport;}};
 await assert.rejects(uploadDraft(session,queued.id,storage));
 assert.equal((await f.store.openDraft('tester',queued.id))?.uris.length,2);
 await uploadDraft(session,queued.id,storage);
 assert.deepEqual(uploaded,[['removal-bytes'],['removal-bytes']]);assert.equal(await f.store.openDraft('tester',queued.id),null);
 const remaining=(await f.store.listDrafts('tester'))[0];assert.ok(remaining);assert.equal(remaining.state,'saved');
 assert.equal(f.files.get(remaining.uris[0]),'planting-bytes');assert.equal(queued.uris.includes(remaining.uris[0]),false);
 const recovered=await recoverVisitDraft('tester',{id:'job',report_id:'report'}, {list:f.store.listDrafts,open:f.store.openDraft},queued.id);
 assert.equal(recovered?.id,remaining.id);
 await f.store.saveDraft({...remaining,state:'queued'});await uploadDraft(session,remaining.id,storage);
 assert.deepEqual(uploaded.at(-1),['planting-bytes']);assert.equal((await f.store.listDrafts('tester')).length,0);
});
test('retrying receipt cleanup does not duplicate or overwrite an edited continuation',async()=>{
 const f=nativeStore();f.files.set('removal-photo','removal-bytes');f.files.set('planting-photo','planting-bytes');
 const draft=await f.store.saveDraft({...evidence('removal'),...packVisitPhotos(visitPhotos(evidence())),state:'queued'});let fail=true;
 const storage:UploadStorage={open:f.store.openDraft,save:f.store.saveDraft,release:f.store.releaseDraft,upload:async()=>({id:'receipt'} as FieldReport),remove:async(owner,id)=>{if(fail){fail=false;throw new Error('Storage temporarily unavailable');}await f.store.removeDraft(owner,id);}};
 await assert.rejects(uploadDraft(session,draft.id,storage));const continuation=(await f.store.listDrafts('tester')).find(item=>item.id!==draft.id);assert.ok(continuation);
 await f.store.saveDraft({...continuation,details:{...continuation.details,notes:'Edited planting note'}});
 await uploadDraft(session,draft.id,storage);const remaining=await f.store.listDrafts('tester');assert.equal(remaining.length,1);assert.equal(remaining[0].details.notes,'Edited planting note');assert.equal(f.files.get(remaining[0].uris[0]),'planting-bytes');
});
test('an explicit queued original draft takes priority over its newer saved continuation',async()=>{
 const original={...evidence(),state:'queued' as const},continuation={...evidence(),id:'remaining_evidence',continuationOf:original.id};
 const recovered=await recoverVisitDraft('tester',{id:'job',report_id:'report'},{list:async()=>[continuation,original],open:async()=>{assert.fail('Queued originals stay immutable');}},original.id);
 assert.equal(recovered,original);
});
