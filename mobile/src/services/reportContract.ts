import { parseIdentification, type Identification } from './contract';

export type User = { id: string; username: string; display_name: string; role: 'ground' | 'ecology' | 'management'; team_id?: string | null; must_change_password?: boolean };
export type Session = { token: string; user: User };
export type Extent = 'one' | 'few' | 'patch' | 'unsure';
export type ReportDetails = { site: string; landmark: string; extent: Extent; observed_on: string; notes: string; request_key: string; identify_requested?: boolean; identification_questioned?: boolean; site_id?: string | null; block_id?: string | null; latitude?: number | null; longitude?: number | null };
export type FieldReport = {
  id: string; reference: string; status: 'submitted' | 'needs_info' | 'assigned' | 'closed' | 'in_progress' | 'blocked' | 'awaiting_verification' | 'follow_up' | 'completed' | 'cancelled' | 'duplicate';
  revision: number; site: string; landmark: string; extent: Extent; observed_on: string;
  notes: string; reporter_name: string; reporter_id: string; assigned_team_id: string | null;
  prediction: Identification | null; created_at: string; identification_questioned?: boolean; block_name?: string; latitude?: number; longitude?: number; work_items: WorkItem[];
  photos: { id: string; kind: string; url: string; work_id?: string | null }[];
  review: null | { confirmed_species: string; notes: string; reviewer_name: string;
    assigned_team_name?: string; removal_instructions: string; replacement_species: string;
    replanting_instructions: string };
};
export const reportStatuses: Record<FieldReport['status'], string> = {
  submitted: 'New', needs_info: 'More info needed', assigned: 'Assigned', closed: 'Closed', in_progress: 'In progress', blocked: 'Problem reported', awaiting_verification: 'Ready for review', follow_up: 'Follow-up due', completed: 'Closed', cancelled: 'Cancelled', duplicate: 'Linked duplicate',
};
export function parseReport(value: unknown): FieldReport {
  if (!value || typeof value !== 'object') throw new Error('Invalid report');
  const report = value as FieldReport;
  if (typeof report.id !== 'string' || !report.id || typeof report.reference !== 'string' ||
    !Object.prototype.hasOwnProperty.call(reportStatuses, report.status) ||
    typeof report.site !== 'string' || typeof report.landmark !== 'string' ||
    !Number.isInteger(report.revision) || report.revision < 1 || !Array.isArray(report.photos)) {
    throw new Error('Invalid report');
  }
  if (report.prediction !== null) parseIdentification(report.prediction);
  report.work_items ??= [];
  return report;
}
export function validateReportDetails(details: ReportDetails): string | null {
  if (!details.site.trim()) return 'Add the site or block.';
  if (!details.landmark.trim()) return 'Add a nearby landmark.';
  if (details.site.trim().length > 100 || details.landmark.trim().length > 200) return 'Shorten the location details.';
  if (!['one', 'few', 'patch', 'unsure'].includes(details.extent)) return 'Choose the amount seen.';
  const date = new Date(details.observed_on + 'T00:00:00');
  const today = new Date(); today.setHours(23, 59, 59, 999);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(details.observed_on) || !Number.isFinite(date.getTime()) ||
    date.getFullYear() !== Number(details.observed_on.slice(0, 4)) ||
    date.getMonth() + 1 !== Number(details.observed_on.slice(5, 7)) ||
    date.getDate() !== Number(details.observed_on.slice(8, 10)) || date > today) {
    return 'Use a valid observation date, today or earlier (YYYY-MM-DD).';
  }
  if (details.notes.trim().length > 1200) return 'Keep your note under 1,200 characters.';
  return null;
}

export type WorkItem = {id:string; report_id:string; team_id:string; team_name:string; revision:number; status:string; work_type:string; due_on:string|null; priority:string; overdue:boolean; legacy?:boolean; requires_reassignment?:boolean; notes:string; confirmed_species:string; removal_instructions:string; replacement_species:string; replanting_instructions:string; completions:Completion[]; verification:null|{notes:string;decision:string;verified_by:string}; history:{at:string;action:string;by?:string;notes?:string}[]};
export type Completion = {revision:number;request_key:string;stage:'removal'|'replanting'|'both'|'observation';observed_on:string;notes:string;removal_complete:boolean;removed_on?:string|null;planted_on?:string|null;planted_species?:string;quantity?:number|null;regrowth?:'yes'|'no'|'unknown'|null;surviving_count?:number|null;checked_count?:number|null;planting_pending_reason?:string;suggested_species?:string;recommended_action?:'none'|'inspection'|'removal'|'replanting';removal_recommendation?:string;replacement_recommendation?:string;submitted_by?:string;submitted_at?:string;photo_ids?:string[]};
export type Notice={id:string;report_id:string|null;message:string;created_at:string;read_at:string|null};
export type Catalog={sites:{id:string;name:string}[];blocks:{id:string;site_id:string;name:string}[]};
export const workNames:Record<string,string>={restoration:'Restoration',inspection:'Inspection',monitoring:'Monitoring',removal:'Removal',replanting:'Replanting',removal_replanting:'Removal & replanting',follow_up:'Follow-up'};
export function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
