import type { Draft, PhotoSlots } from './draftTypes';
import type { Completion } from './reportContract';
import { RequestError } from './requestErrors';

type Slot = keyof PhotoSlots;
export type VisitPhotos = Partial<Record<Slot, string>> & { retained?: string[] };
const names: Slot[] = ['removal', 'planting', 'visit'];

export function visitPhotos(draft: Draft | null): VisitPhotos {
  if (!draft || draft.kind !== 'completion') return {};
  const slots: PhotoSlots = draft.photoSlots ?? ((draft.details as Completion).stage === 'both'
    ? { removal: 0, planting: 1 } : (draft.details as Completion).stage === 'replanting'
      ? { planting: 0 } : (draft.details as Completion).stage === 'removal' ? { removal: 0 } : { visit: 0 });
  const photos: VisitPhotos = {};
  for (const name of names) {
    const index = slots[name];
    if (index !== undefined && Number.isInteger(index) && index >= 0 && draft.uris[index]) photos[name] = draft.uris[index];
  }
  const selected = new Set(names.map(name => photos[name]));
  photos.retained = draft.uris.filter(uri => !selected.has(uri));
  return photos;
}

export function packVisitPhotos(photos: VisitPhotos): { uris: string[]; photoSlots: PhotoSlots } {
  const uris: string[] = [], photoSlots: PhotoSlots = {};
  for (const name of names) {
    const uri = photos[name];
    if (!uri) continue;
    let index = uris.indexOf(uri);
    if (index < 0) { index = uris.length; uris.push(uri); }
    photoSlots[name] = index;
  }
  for (const uri of photos.retained ?? []) if (!uris.includes(uri)) uris.push(uri);
  return { uris, photoSlots };
}

export function completionPhotoUris(draft: Draft): string[] {
  // Positional queued drafts retain their exact original request body for retries.
  if (!draft.photoSlots) return draft.uris;
  const photos = visitPhotos(draft), stage = (draft.details as Completion).stage;
  const selected = stage === 'observation' && (draft.details as Completion).other_invasive === 'yes' ? [photos.visit,photos.planting] : stage === 'both' ? [photos.removal, photos.planting]
    : [stage === 'removal' ? photos.removal : stage === 'replanting' ? photos.planting : photos.visit];
  if (selected.some(uri => !uri)) throw new RequestError('Reopen this evidence draft and add the photo for its selected stage.', 422);
  return selected as string[];
}

export function unusedPhotoDraft(draft: Draft): Draft | null {
  if (draft.kind !== 'completion' || !draft.photoSlots) return null;
  const uploaded = new Set(completionPhotoUris(draft));
  if (draft.uris.every(uri => uploaded.has(uri))) return null;
  const photos = visitPhotos(draft);
  for (const name of names) if (photos[name] && uploaded.has(photos[name]!)) delete photos[name];
  photos.retained = (photos.retained ?? []).filter(uri => !uploaded.has(uri));
  // A deterministic continuation avoids duplicates when receipt cleanup is retried.
  const suffix = [...draft.id].reduce((hash, char) => Math.imul(hash ^ char.charCodeAt(0), 16777619) >>> 0, 2166136261).toString(36);
  const id = `remaining_${draft.id.slice(0, 72)}_${suffix}`;
  const details = draft.details as Completion;
  return { ...draft, id, continuationOf: draft.continuationOf ?? draft.id, state: 'saved', error: undefined,
    label: 'Saved remaining evidence', ...packVisitPhotos(photos),
    details: { ...details, request_key: id, stage: photos.planting ? 'replanting' : photos.removal ? 'removal' : 'observation',
      removal_complete: false, removed_on: null, planting_pending_reason: '' } };
}
