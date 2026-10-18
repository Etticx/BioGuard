import type { Draft } from './draftTypes';
import type { Completion, WorkItem } from './reportContract';

export function mayEditReport(draft: Draft) {
  return draft.kind === 'report' && draft.state !== 'queued';
}

type RecoveryStorage = {
  list: (owner: string) => Promise<Draft[]>;
  open: (owner: string, id: string) => Promise<Draft | null>;
};

export async function recoverVisitDraft(owner: string, work: Pick<WorkItem, 'id' | 'report_id'>, storage: RecoveryStorage, draftId?: string) {
  const candidates = (await storage.list(owner)).filter(draft =>
    draft.owner === owner && draft.kind === 'completion' &&
    draft.reportId === work.report_id && draft.workId === work.id);
  const item = draftId ? candidates.find(draft => draft.id === draftId) ?? candidates.find(draft => draft.continuationOf === draftId) : candidates[0];
  if (!item) return null;
  // Queued evidence must retain its original payload until acknowledged.
  if (item.state === 'queued') return item;
  // Older revisions remain recoverable; the form requires review before saving/sending.
  return storage.open(owner, item.id);
}

export function visitStage(workType: string, saved?: Completion['stage']): Completion['stage'] {
  if (workType === 'restoration') return saved && ['removal', 'replanting', 'both'].includes(saved) ? saved : 'both';
  if (workType === 'removal') return 'removal';
  if (workType === 'replanting') return 'replanting';
  if (workType === 'removal_replanting') return saved === 'removal' ? 'removal' : 'both';
  return 'observation';
}

export function requiresVisitReview(draft: Draft | null, work: WorkItem, reviewed: boolean) {
  return Boolean(draft && (draft.details as Completion).revision !== work.revision && !reviewed);
}
