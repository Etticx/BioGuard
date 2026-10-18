import test from 'node:test';
import assert from 'node:assert/strict';
import { mayEditReport, recoverVisitDraft, requiresVisitReview, visitStage } from '../src/services/draftRecovery';
import { uploadDraft, type UploadStorage } from '../src/services/outboxCore';
import { RequestError } from '../src/services/requestErrors';
import type { Draft } from '../src/services/draftTypes';
import type { Completion, FieldReport, Session, WorkItem } from '../src/services/reportContract';

const work = { id: 'visit', report_id: 'report', revision: 2, work_type: 'removal' } as WorkItem;
const evidence: Draft = {
  id: 'evidence_key', owner: 'owner', kind: 'completion', state: 'saved',
  reportId: 'report', workId: 'visit', updated: '', label: 'Evidence', uris: ['durable-photo'],
  details: { revision: 1, request_key: 'evidence_key', stage: 'removal',
    observed_on: '2026-01-01', notes: 'Saved field notes', removal_complete: true },
};

test('a rejected report can be reopened, corrected and submitted with its original photo and key', async () => {
  const session: Session = { token: 'test', user: { id: 'owner', username: 'staff', display_name: 'Staff', role: 'ground' } };
  let stored: Draft | null = {
    ...evidence, kind: 'report', state: 'queued',
    details: { site: 'Old site', site_id: 'disabled', landmark: 'Drain', extent: 'one',
      observed_on: '2026-01-01', notes: '', request_key: 'evidence_key' },
  };
  let attempts = 0;
  const storage: UploadStorage = {
    open: async () => stored, save: async draft => { stored = draft; },
    remove: async () => { stored = null; }, release: () => {},
    upload: async (_, draft) => {
      if (++attempts === 1) throw new RequestError('Choose an active site.', 422);
      assert.equal(draft.details.request_key, 'evidence_key');
      assert.deepEqual(draft.uris, ['durable-photo']);
      assert.equal('site_id' in draft.details && draft.details.site_id, null);
      return { id: 'receipt' } as FieldReport;
    },
  };
  assert.equal(mayEditReport(stored), false);
  await assert.rejects(uploadDraft(session, stored.id, storage));
  const rejected = await storage.open('owner', 'evidence_key');
  assert.ok(rejected);
  assert.equal(rejected.state, 'attention');
  assert.equal(mayEditReport(rejected), true);
  // Opening the report retains the draft; only an explicit submission queues it again.
  assert.deepEqual(rejected.uris, ['durable-photo']);
  assert.equal(rejected.state, 'attention');
  await storage.save({ ...rejected, state: 'queued', details: { ...rejected.details, site_id: null } });
  assert.equal((await uploadDraft(session, rejected.id, storage)).id, 'receipt');
  assert.equal(stored, null);
  assert.equal(mayEditReport(evidence), false);
});

for (const state of ['saved', 'attention'] as const) {
  test(`${state} evidence survives a visit revision and requires explicit review`, async () => {
    const draft = { ...evidence, state };
    const restored = await recoverVisitDraft('owner', work, {
      list: async () => [{ ...draft, owner: 'other' }, { ...draft, reportId: 'other-report' }, draft],
      open: async (owner, id) => { assert.equal(owner, 'owner'); assert.equal(id, draft.id); return draft; },
    });
    assert.ok(restored);
    assert.equal((restored.details as Completion).notes, 'Saved field notes');
    assert.deepEqual(restored.uris, ['durable-photo']);
    assert.equal(requiresVisitReview(restored, work, false), true);
    assert.equal(requiresVisitReview(restored, work, true), false);
    assert.equal(requiresVisitReview(restored, { ...work, revision: 1 }, false), false);
    assert.equal((restored.details as Completion).revision, 1);
    assert.equal(restored.details.request_key, 'evidence_key');
  });
}

test('queued evidence is kept intact for idempotent retry instead of reopened for editing', async () => {
  const draft = { ...evidence, state: 'queued' as const };
  const restored = await recoverVisitDraft('owner', work, {
    list: async () => [draft], open: async () => { assert.fail('Queued evidence must not be opened for editing'); },
  });
  assert.equal(restored, draft);
  assert.equal((restored.details as Completion).revision, 1);
});

test('opening a specific older evidence draft does not silently choose the newest draft', async () => {
  const newer = { ...evidence, id: 'newer-evidence' };
  const restored = await recoverVisitDraft('owner', work, {
    list: async () => [newer, evidence],
    open: async (_, id) => { assert.equal(id, evidence.id); return evidence; },
  }, evidence.id);
  assert.equal(restored, evidence);
});

test('no draft from another work item or account is restored', async () => {
  assert.equal(await recoverVisitDraft('owner', { ...work, id: 'another-visit' }, {
    list: async () => [evidence], open: async () => { assert.fail('Unrelated draft'); },
  }), null);
  assert.equal(await recoverVisitDraft('other', work, {
    list: async () => [evidence], open: async () => { assert.fail('Other account'); },
  }), null);
});

test('a revised visit uses a valid evidence stage while preserving combined removal-only drafts', () => {
  assert.equal(visitStage('inspection', 'both'), 'observation');
  assert.equal(visitStage('removal', 'replanting'), 'removal');
  assert.equal(visitStage('replanting', 'removal'), 'replanting');
  assert.equal(visitStage('removal_replanting', 'removal'), 'removal');
  assert.equal(visitStage('removal_replanting', 'observation'), 'both');
});


test('restoration drafts retain their two photos and resume the same removal or planting stage', async () => {
  for (const stage of ['both', 'removal', 'replanting'] as const) {
    assert.equal(visitStage('restoration', stage), stage);
  }
  assert.equal(visitStage('restoration'), 'both');
  const item: Draft = { ...evidence, uris: ['synthetic-removal-photo', 'synthetic-planting-photo'],
    details: { ...evidence.details, stage: 'both', planting_pending_reason: '' } as Completion };
  const restored = await recoverVisitDraft('owner', work, { list: async () => [item], open: async () => item });
  assert.deepEqual(restored?.uris, ['synthetic-removal-photo', 'synthetic-planting-photo']);
  assert.equal((restored?.details as Completion).stage, 'both');
});
