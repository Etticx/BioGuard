import AsyncStorage from '@react-native-async-storage/async-storage';
import { Directory, File, Paths } from 'expo-file-system';
import { draftKey, type Draft, type DraftInput } from './draftTypes';
const folder=new Directory(Paths.document,'bioguard-drafts');
const prefix=folder.uri.replace(/\/+$/,'')+'/';
function removeOwned(uri:string){if(!uri.startsWith(prefix))return;const name=uri.slice(prefix.length);if(!/^[a-zA-Z0-9_.-]+$/.test(name))return;const file=new File(uri);if(file.exists)file.delete();}
export async function saveDraft(input:DraftInput):Promise<Draft>{const key=draftKey(input.owner,input.id);folder.create({idempotent:true,intermediates:true});const previous=await AsyncStorage.getItem(key);const old=previous?JSON.parse(previous) as Draft:null;const uris:string[]=[];
 try{for(const uri of input.uris){if(old?.uris.includes(uri)&&uri.startsWith(prefix)&&new File(uri).exists){uris.push(uri);continue;}const target=new File(folder,`${input.owner}_${input.id}_${Date.now()}_${uris.length}.jpg`);await new File(uri).copy(target);uris.push(target.uri);}const saved={...input,uris,updated:new Date().toISOString()};await AsyncStorage.setItem(key,JSON.stringify(saved));for(const uri of old?.uris??[])if(!uris.includes(uri))removeOwned(uri);return saved;}
 catch(error){for(const uri of uris)if(!old?.uris.includes(uri))removeOwned(uri);throw error;}}
export async function listDrafts(owner:string):Promise<Draft[]>{const keys=(await AsyncStorage.getAllKeys()).filter(key=>key.startsWith(`bioguard.draft.v1.${owner}.`));const values=await AsyncStorage.multiGet(keys);return values.flatMap(([,value])=>value?[JSON.parse(value) as Draft]:[]).filter(item=>item.owner===owner).sort((a,b)=>b.updated.localeCompare(a.updated));}
export async function openDraft(owner:string,id:string):Promise<Draft|null>{const value=await AsyncStorage.getItem(draftKey(owner,id));const draft=value?JSON.parse(value) as Draft:null;return draft?.owner===owner?draft:null;}
export function releaseDraft(_draft:Draft){}
export async function removeDraft(owner:string,id:string){const draft=await openDraft(owner,id);await AsyncStorage.removeItem(draftKey(owner,id));for(const uri of draft?.uris??[]){try{removeOwned(uri);}catch{ /* Receipt already acknowledged; orphaned app copies can be cleared later. */ }}}
