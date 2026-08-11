'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const {
  PlanReviewManager,
  SessionPlanClient,
  buildReviewedPlanPrompt,
  parseSessionPlan,
  renderPlanDocument,
} = require('../src/sessionPlan');

function payload(overrides = {}) {
  return {
    schemaVersion: 1,
    kind: 'local',
    sessionPlan: {
      session: 'run-1',
      exists: true,
      ok: true,
      status: 'in_progress',
      message: 'Found 2 plan item(s).',
      task: 'Repair parser',
      items: [
        { status: 'completed', step: 'Inspect parser' },
        { status: 'in_progress', step: 'Implement fix', activeForm: 'Implementing fix' },
      ],
      ...overrides,
    },
  };
}

test('validates and renders structured session plans', () => {
  const plan = parseSessionPlan(payload(), 'run-1');
  assert.equal(plan.items.length, 2);
  const markdown = renderPlanDocument(plan);
  assert.match(markdown, /Session: `run-1`/);
  assert.match(markdown, /- \[x\] completed: Inspect parser/);
  assert.match(markdown, /- \[ \] in_progress: Implement fix/);
  assert.throws(() => parseSessionPlan(payload({ session: 'run-2' }), 'run-1'), /wrong session/);
  assert.throws(
    () => parseSessionPlan(payload({ items: [{ status: 'unknown', step: 'bad' }] }), 'run-1'),
    /invalid session plan item/,
  );
  assert.throws(
    () => parseSessionPlan(payload({ task: 'x'.repeat(10_000) }), 'run-1'),
    /exceeds 10000 rendered characters/,
  );
  assert.throws(() => buildReviewedPlanPrompt('bad\u001bplan'), /invalid Reviewed plan/);
});

test('loads a selected plan and keeps review metadata outside editable text', async () => {
  const calls = [];
  const client = new SessionPlanClient({
    client: {
      async run(config, root, args) {
        calls.push({ config, root, args });
        return { code: 0, payload: payload() };
      },
    },
  });
  const opened = [];
  const shown = [];
  const vscode = {
    workspace: {
      async openTextDocument(options) {
        const document = {
          uri: { toString: () => 'untitled:VibeAgent-Plan-1' },
          getText: () => `${options.content}\n- [ ] pending: Run tests`,
        };
        opened.push(options);
        return document;
      },
    },
    window: {
      activeTextEditor: null,
      async showTextDocument(document, options) {
        shown.push({ document, options });
        this.activeTextEditor = { document };
      },
    },
  };
  const manager = new PlanReviewManager(vscode, { client });
  const document = await manager.open(
    { executable: 'python', args: ['-m', 'vibeagent'] },
    '/workspace/project',
    { session: 'run-1', name: 'Parser repair' },
  );
  const execution = manager.activeExecution();
  assert.deepEqual(calls[0].args, ['--plan', 'run-1']);
  assert.equal(opened[0].language, 'markdown');
  assert.equal(shown[0].options.preview, false);
  assert.equal(execution.session, 'run-1');
  assert.equal(execution.root, '/workspace/project');
  assert.match(execution.prompt, /pending: Run tests/);
  manager.closed(document);
  assert.throws(() => manager.activeExecution(), /not a VibeAgent plan review/);
});
