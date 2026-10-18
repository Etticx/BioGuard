import assert from 'node:assert/strict';
import test from 'node:test';
import { parseSession, parseUser, sessionHeaders, workspaceFor } from '../src/services/roleAccess';
import { visitStage, requiresVisitReview } from '../src/services/draftRecovery';
import { workNames, type Completion, type Session, type WorkItem } from '../src/services/reportContract';
import type { Draft } from '../src/services/draftTypes';

const identity = { id: 'synthetic-three-role', username: 'synthetic', display_name: 'Synthetic staff' };

test('three canonical accounts route independently and all temporary passwords take precedence', () => {
  for (const role of ['ground', 'ecology', 'management'] as const) {
    const session = parseSession({ token: 'synthetic-session', user: { ...identity, role } });
    assert.equal(session.user.role, role);
    assert.equal(workspaceFor(session.user), role);
    assert.equal(workspaceFor({ ...session.user, must_change_password: true }), 'password');
  }
});

test('legacy stored officer accounts hydrate as management without acquiring a field-team role', () => {
  const user = parseUser({ ...identity, role: 'officer' });
  assert.equal(user.role, 'management');
  assert.equal(workspaceFor(user), 'management');
  assert.throws(() => parseUser({ ...identity, role: 'administrator' }));
});

test('all browser roles can restore through the private cookie without sending an empty bearer header', () => {
  for (const role of ['ground', 'ecology', 'management'] as const) {
    const session: Session = { token: '', user: { ...identity, role } };
    assert.deepEqual(sessionHeaders(session), {});
    assert.deepEqual(sessionHeaders({ ...session, token: 'synthetic-token' }), { Authorization: 'Bearer synthetic-token' });
  }
});

test('new work stages remain distinct and historical visits retain readable labels', () => {
  assert.equal(visitStage('inspection'), 'observation');
  assert.equal(visitStage('removal'), 'removal');
  assert.equal(visitStage('replanting'), 'replanting');
  for (const kind of ['inspection', 'removal', 'replanting', 'monitoring', 'removal_replanting', 'follow_up']) {
    assert.equal(typeof workNames[kind], 'string');
    assert.ok(workNames[kind].length > 0);
  }
});

test('saved ecology evidence still requires review against a revised management assignment', () => {
  const details: Completion = { revision: 2, request_key: 'synthetic_evidence', stage: 'observation',
    observed_on: '2026-10-17', notes: 'Synthetic inspection', removal_complete: false,
    suggested_species: 'Unknown', recommended_action: 'inspection',
    removal_recommendation: '', replacement_recommendation: '' };
  const draft: Draft = { id: 'synthetic_evidence', owner: 'synthetic-ecology', kind: 'completion', state: 'saved',
    label: 'Synthetic inspection', updated: '', workId: 'synthetic-work', reportId: 'synthetic-report',
    details, uris: ['synthetic-local-photo'] };
  const work = { id: 'synthetic-work', revision: 3, work_type: 'inspection' } as WorkItem;
  assert.equal(requiresVisitReview(draft, work, false), true);
  assert.equal(requiresVisitReview(draft, work, true), false);
  assert.equal((draft.details as Completion).suggested_species, 'Unknown');
  assert.deepEqual(draft.uris, ['synthetic-local-photo']);
});
