import { reportStatuses, type FieldReport } from './reportContract';

export type EcologyJobGroup = 'active' | 'review' | 'past' | 'upcoming';
const ended = new Set(['verified', 'cancelled']);
const closed = new Set(['completed', 'closed', 'cancelled', 'duplicate']);

export function ecologyJobGroup(report: FieldReport, teamId?: string | null): EcologyJobGroup {
  if (closed.has(report.status)) return 'past';
  const jobs = report.work_items.filter(job => job.team_id === teamId);
  const unfinished = jobs.filter(job => !ended.has(job.status));
  if (unfinished.some(job => job.followup_of && job.status !== 'awaiting_verification')) return 'upcoming';
  if (unfinished.some(job => job.status !== 'awaiting_verification')) return 'active';
  if (unfinished.length) return 'review';
  if (jobs.length) return 'past';
  return report.status === 'awaiting_verification' ? 'review' : 'active';
}

export function ecologyJobLabel(report: FieldReport, teamId?: string | null): string {
  if (report.status === 'completed' || report.status === 'closed') return 'Completed';
  if (report.status === 'cancelled' || report.status === 'duplicate') return reportStatuses[report.status];
  const group = ecologyJobGroup(report, teamId);
  if (group === 'upcoming') return 'Restoration approved - follow-up pending';
  if (group === 'review') return 'Awaiting review';
  if (group === 'past') return report.work_items.filter(job => job.team_id === teamId).every(job => job.status === 'verified') ? 'Previous work approved' : 'Previous assignment';
  const job = report.work_items.find(item => item.team_id === teamId && !ended.has(item.status));
  return ({ assigned: 'Assigned', accepted: 'Accepted', in_progress: 'In progress', blocked: 'Problem reported', correction_requested: 'Changes requested' } as Record<string, string>)[job?.status ?? ''] ?? reportStatuses[report.status];
}
