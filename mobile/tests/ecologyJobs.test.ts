import assert from 'node:assert/strict';
import test from 'node:test';
import { ecologyJobGroup, ecologyJobLabel } from '../src/services/ecologyJobs';
import type { FieldReport, WorkItem } from '../src/services/reportContract';

function report(status: FieldReport['status'], jobs: [string, string][] = []): FieldReport {
  return { status, work_items: jobs.map(([state, team]) => ({ status: state, team_id: team } as WorkItem)) } as FieldReport;
}

test('work moves from active to review only after evidence submission, and back for requested changes', () => {
  for (const status of ['assigned', 'accepted', 'in_progress', 'blocked', 'correction_requested']) {
    assert.equal(ecologyJobGroup(report('assigned', [[status, 'eco']]), 'eco'), 'active');
  }
  const submitted = report('awaiting_verification', [['awaiting_verification', 'eco']]);
  assert.equal(ecologyJobGroup(submitted, 'eco'), 'review');
  assert.equal(ecologyJobLabel(submitted, 'eco'), 'Awaiting review');
  assert.equal(ecologyJobLabel(report('assigned', [['correction_requested', 'eco']]), 'eco'), 'Changes requested');
});

test('management closure moves the whole ticket to past jobs, even when old job states remain', () => {
  for (const status of ['completed', 'closed'] as const) {
    const item = report(status, [['awaiting_verification', 'eco']]);
    assert.equal(ecologyJobGroup(item, 'eco'), 'past');
    assert.equal(ecologyJobLabel(item, 'eco'), 'Completed');
  }
});

test('a next assigned step keeps an open ticket active instead of hiding it with the approved earlier step', () => {
  const item = report('assigned', [['verified', 'eco'], ['assigned', 'eco']]);
  assert.equal(ecologyJobGroup(item, 'eco'), 'active');
  assert.equal(ecologyJobLabel(item, 'eco'), 'Assigned');
});

test('other teams current work does not turn this teams approved history into an active job', () => {
  const item = report('assigned', [['verified', 'eco'], ['in_progress', 'other']]);
  assert.equal(ecologyJobGroup(item, 'eco'), 'past');
  assert.equal(ecologyJobLabel(item, 'eco'), 'Previous work approved');
});

test('cancelled and linked tickets remain in history without being labelled completed', () => {
  for (const status of ['cancelled', 'duplicate'] as const) {
    const item = report(status, [['cancelled', 'eco']]);
    assert.equal(ecologyJobGroup(item, 'eco'), 'past');
    assert.notEqual(ecologyJobLabel(item, 'eco'), 'Completed');
  }
  assert.equal(ecologyJobLabel(report('assigned', [['cancelled', 'eco']]), 'eco'), 'Previous assignment');
});

test('classification preserves historical evidence and keeps unrecognised unfinished work visible', () => {
  const item = report('assigned', [['legacy_status', 'eco']]);
  const saved = structuredClone(item);
  assert.equal(ecologyJobGroup(item, 'eco'), 'active');
  assert.deepEqual(item, saved);
  assert.equal(ecologyJobGroup(report('awaiting_verification'), 'eco'), 'review');
});
