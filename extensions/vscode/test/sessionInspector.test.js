'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { SessionInspectorManager } = require('../src/sessionInspector');
const { SessionInspectorClient, parseSessionInspector } = require('../src/sessionInspectorClient');

const SESSION = 'run-inspect-1';

function envelope(report) {
  return { schemaVersion: 1, kind: 'local', sessionInspect: report };
}

function group(items = []) {
  return { total: items.length, shown: items.length, truncated: false, items };
}

function inspectorReport(overrides = {}) {
  return {
    projectRoot: '/workspace/project',
    session: SESSION,
    exists: true,
    ok: true,
    status: 'completed',
    overview: {
      status: 'completed',
      task: 'Repair parser',
      finalMessage: 'Parser repaired.',
      events: { total: 5, malformed: 0, iterations: 2 },
      toolCalls: 3,
      approvals: { requested: 1, approved: 1, denied: 0 },
      tokens: { input: 100, output: 20, total: 120 },
      completion: { ready: true, blockers: 0, warnings: 0, blockedAttempts: 0 },
      finalReview: { seen: true, ready: true, blockingIssues: 0, warnings: 0, files: 1 },
      checkpoints: { created: 1, latestId: 'checkpoint-1' },
    },
    plan: {
      status: 'completed', total: 1, shown: 1, truncated: false,
      items: [{ status: 'completed', step: 'Inspect parser', activeForm: null }],
    },
    transcript: {
      session: SESSION, exists: true, ok: true, status: 'ready',
      events: {
        total: 2, shown: 2, omitted: 0, truncated: false, malformed: 0,
        items: [
          { lineNumber: 1, type: 'task', malformed: false, summary: '    - #1 task: Repair parser' },
          { lineNumber: 2, type: 'result', malformed: false, summary: '    - #2 result: completed' },
        ],
      },
    },
    files: {
      session: SESSION, exists: true, ok: true, status: 'ready',
      files: {
        total: 1, shown: 1, omitted: 0, truncated: false,
        items: [{
          path: 'app.py', tools: ['read_file'], toolCount: 1, toolsTruncated: false,
          uses: ['read'], useCount: 1, usesTruncated: false,
          lines: [2], count: 1, linesTruncated: false,
        }],
      },
    },
    verification: {
      session: SESSION, exists: true, ok: true, ready: true, status: 'ready',
      verified: group(['python -m unittest']), pending: group(), failed: group(),
      truncated: false,
    },
    message: 'Read session inspector report.',
    ...overrides,
  };
}

test('loads one bounded inspector report with the exact provider-free CLI argument', async () => {
  const calls = [];
  const client = new SessionInspectorClient({
    client: {
      async run(_config, _root, args) {
        calls.push(args);
        return { code: 0, payload: envelope(inspectorReport()) };
      },
    },
  });
  const report = await client.get(
    { executable: 'python', args: ['-m', 'vibeagent'] },
    '/workspace/project',
    SESSION,
  );

  assert.deepEqual(calls, [['--session-inspect', SESSION]]);
  assert.equal(report.overview.task, 'Repair parser');
  assert.equal(report.files.items[0].path, 'app.py');
  assert.throws(
    () => parseSessionInspector(envelope(inspectorReport({ session: '../escape' })), SESSION),
    /session ID/,
  );
  assert.throws(
    () => parseSessionInspector(envelope(inspectorReport({
      plan: { ...inspectorReport().plan, total: 2 },
    })), SESSION),
    /inconsistent session plan counts/,
  );
  assert.throws(
    () => parseSessionInspector(envelope(inspectorReport({
      files: {
        ...inspectorReport().files,
        files: {
          ...inspectorReport().files.files,
          items: [{
            ...inspectorReport().files.files.items[0],
            count: 2,
          }],
        },
      },
    })), SESSION),
    /inconsistent session file detail counts/,
  );
});

test('preserves a bounded missing-session error from the local CLI', async () => {
  const report = inspectorReport({
    exists: false,
    ok: false,
    status: 'missing',
    overview: null,
    plan: null,
    transcript: null,
    files: null,
    verification: null,
    message: `Session not found: ${SESSION}`,
  });
  const client = new SessionInspectorClient({
    client: {
      async run() {
        return { code: 1, payload: envelope(report) };
      },
    },
  });

  await assert.rejects(
    client.get({ executable: 'python', args: ['-m', 'vibeagent'] }, '/workspace/project', SESSION),
    /Session not found/,
  );
});

test('opens an inspector document, resumes its exact session, and invalidates closed documents', async () => {
  const calls = [];
  const resumed = [];
  const document = { uri: { toString: () => 'untitled:session-inspector-1' } };
  const vscode = {
    window: {
      activeTextEditor: null,
      async showQuickPick(items, options) {
        calls.push(['quickPick', options]);
        return items[0];
      },
      async showTextDocument(value, options) {
        this.activeTextEditor = { document: value };
        calls.push(['showDocument', options]);
      },
      showInformationMessage(message) { calls.push(['information', message]); },
    },
    workspace: {
      async openTextDocument(options) {
        calls.push(['openDocument', options]);
        return document;
      },
    },
  };
  const manager = new SessionInspectorManager(vscode, {
    catalog: {
      async list() {
        return [{
          session: SESSION, status: 'completed', events: 5, malformed: 0,
          lastEventTime: '2026-08-11T00:00:00Z', name: 'Parser repair', task: 'Repair parser',
          completed: true, failed: false, blocked: false,
        }];
      },
    },
    client: { async get() { return parseSessionInspector(envelope(inspectorReport()), SESSION); } },
    terminals: {
      resume(config, root, session, name) {
        resumed.push({ config, root, session, name });
        return 'terminal';
      },
    },
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };
  await manager.open(config, '/workspace/project');
  const openCall = calls.find((item) => item[0] === 'openDocument');

  assert.match(openCall[1].content, /# VibeAgent Session Inspector/);
  assert.match(openCall[1].content, /## Verification/);
  assert.match(openCall[1].content, /`app\.py`/);
  assert.equal(manager.resumeActive(config), 'terminal');
  assert.deepEqual(resumed[0], {
    config, root: '/workspace/project', session: SESSION, name: 'Parser repair',
  });

  manager.closed(document);
  assert.throws(() => manager.resumeActive(config), /not a VibeAgent session inspector/);
});

test('refreshes, confirms, and reruns inspected verification in the exact session', async () => {
  const calls = [];
  const warnings = [];
  const runs = [];
  let confirm = true;
  const document = { uri: { toString: () => 'untitled:session-inspector-verification' } };
  const report = inspectorReport();
  report.verification = {
    ...report.verification,
    ok: false,
    ready: false,
    status: 'blocked',
    failed: group(['npm test (exit=1)']),
    pending: group(['npm run lint']),
  };
  const vscode = {
    window: {
      activeTextEditor: null,
      async showQuickPick(items) { return items[0]; },
      async showTextDocument(value) { this.activeTextEditor = { document: value }; },
      async showWarningMessage(message, options, action) {
        warnings.push({ message, options, action });
        return confirm ? action : null;
      },
      showInformationMessage() {},
    },
    workspace: {
      async openTextDocument() { return document; },
    },
  };
  const manager = new SessionInspectorManager(vscode, {
    catalog: {
      async list() {
        return [{
          session: SESSION, status: 'completed', events: 5, malformed: 0,
          lastEventTime: '2026-08-11T00:00:00Z', name: 'Parser repair', task: 'Repair parser',
          completed: true, failed: false, blocked: false,
        }];
      },
    },
    client: {
      async get(_config, root, session) {
        calls.push({ root, session });
        return parseSessionInspector(envelope(report), SESSION);
      },
    },
    terminals: {
      runVerification(config, root, session, name) {
        runs.push({ config, root, session, name });
        return 'verification-terminal';
      },
    },
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };

  await manager.open(config, '/workspace/project');
  assert.equal(await manager.runVerificationActive(config), 'verification-terminal');
  assert.equal(calls.length, 2);
  assert.equal(warnings[0].options.modal, true);
  assert.match(warnings[0].options.detail, /Session: run-inspect-1/);
  assert.match(warnings[0].options.detail, /npm test \(exit=1\)/);
  confirm = false;
  assert.equal(await manager.runVerificationActive(config), null);
  assert.equal(runs.length, 1);
  assert.deepEqual(runs[0], {
    config, root: '/workspace/project', session: SESSION, name: 'Parser repair',
  });
});
