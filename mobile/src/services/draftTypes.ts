import type { Identification } from './contract';
import type { Completion, ReportDetails } from './reportContract';
export type PhotoSlots=Partial<Record<'removal'|'planting'|'visit',number>>;
export type Draft={id:string;owner:string;kind:'report'|'completion';state:'saved'|'queued'|'attention';updated:string;label:string;details:ReportDetails|Completion;prediction?:Identification|null;reportId?:string;workId?:string;error?:string;photoSlots?:PhotoSlots;continuationOf?:string;uris:string[]};
export type DraftInput=Omit<Draft,'updated'>;
export function draftKey(owner:string,id:string){if(!/^[a-zA-Z0-9_-]+$/.test(owner)||!/^[a-zA-Z0-9_-]+$/.test(id))throw new Error('Invalid draft key');return `bioguard.draft.v1.${owner}.${id}`;}
export function mayRetry(state:Draft['state']){return state==='queued';}
