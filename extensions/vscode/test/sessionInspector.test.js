'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const {
  MAX_INSPECTOR_DOCUMENT_CHARS,
  SessionInspectorManager,
  actionableTaskQuickPickItems,
  buildTaskContinuationPrompt,
  renderSessionInspector,
} = require('../src/sessionInspector');
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
    tasks: {
      projectRoot: '/workspace/project',
      session: SESSION,
      exists: true,
      ok: true,
      status: 'ready',
      counts: { pending: 1, inProgress: 0, completed: 1, blocked: 1 },
      tasks: {
        total: 2, shown: 2, omitted: 0, truncated: false,
        items: [
          {
            id: '1', subject: 'Inspect parser', description: 'Read parser behavior',
            status: 'completed', activeForm: null, owner: 'main', blocks: ['2'],
            blockedBy: [], blocked: false,
          },
          {
            id: '2', subject: 'Implement parser', description: 'Apply parser fix',
            status: 'pending', activeForm: 'Implementing parser', owner: null, blocks: [],
            blockedBy: ['1'], blocked: true,
          },
        ],
      },
      message: 'Found 2 persistent session task(s).',
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
  assert.equal(report.tasks.items[1].blocked, true);
  assert.throws(
    () => parseSessionInspector(envelope(inspectorReport({
      tasks: {
        ...inspectorReport().tasks,
        counts: { ...inspectorReport().tasks.counts, pending: 2 },
      },
    })), SESSION),
    /inconsistent session task status counts/,
  );
  assert.throws(
    () => parseSessionInspector(envelope(inspectorReport({
      tasks: {
        ...inspectorReport().tasks,
        tasks: {
          ...inspectorReport().tasks.tasks,
          items: [
            { ...inspectorReport().tasks.tasks.items[0], id: '../escape' },
            inspectorReport().tasks.tasks.items[1],
          ],
        },
      },
    })), SESSION),
    /session task ID/,
  );
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
    tasks: null,
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
  assert.match(openCall[1].content, /## Persistent Tasks \(2\/2\)/);
  assert.match(openCall[1].content, /`#2` pending \(blocked\): Implement parser/);
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

test('refreshes the inspected graph and continues only an unblocked actionable task', async () => {
  const report = inspectorReport();
  report.tasks.counts = { pending: 2, inProgress: 1, completed: 0, blocked: 1 };
  report.tasks.tasks = {
    total: 3, shown: 3, omitted: 0, truncated: false,
    items: [
      {
        id: '1', subject: 'Implement parser', description: 'Apply the parser fix',
        status: 'in_progress', activeForm: 'Implementing parser', owner: 'worker-1',
        blocks: [], blockedBy: [], blocked: false,
      },
      {
        id: '2', subject: 'Run integration', description: 'Run the integration suite',
        status: 'pending', activeForm: null, owner: null,
        blocks: [], blockedBy: ['1'], blocked: true,
      },
      {
        id: '3', subject: 'Update docs', description: 'Document the parser fix',
        status: 'pending', activeForm: null, owner: null,
        blocks: [], blockedBy: [], blocked: false,
      },
    ],
  };
  const document = { uri: { toString: () => 'untitled:session-inspector-task' } };
  const reads = [];
  const picks = [];
  const continued = [];
  let chooseTask = true;
  const vscode = {
    window: {
      activeTextEditor: null,
      async showQuickPick(items, options) {
        picks.push({ items, options });
        if (options.title === 'Continue VibeAgent Task' && !chooseTask) return null;
        return items[0];
      },
      async showTextDocument(value) { this.activeTextEditor = { document: value }; },
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
          session: SESSION, status: 'running', events: 5, malformed: 0,
          lastEventTime: '2026-08-11T00:00:00Z', name: 'Parser repair', task: 'Repair parser',
          completed: false, failed: false, blocked: false,
        }];
      },
    },
    client: {
      async get(_config, root, session) {
        reads.push({ root, session });
        return parseSessionInspector(envelope(report), SESSION);
      },
    },
    terminals: {
      continueTask(config, root, session, name, prompt) {
        continued.push({ config, root, session, name, prompt });
        return 'task-terminal';
      },
    },
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };

  await manager.open(config, '/workspace/project');
  assert.equal(await manager.continueTaskActive(config), 'task-terminal');

  assert.deepEqual(reads, [
    { root: '/workspace/project', session: SESSION },
    { root: '/workspace/project', session: SESSION },
  ]);
  assert.equal(picks[1].options.title, 'Continue VibeAgent Task');
  assert.deepEqual(picks[1].items.map((item) => item.taskId), ['1', '3']);
  assert.equal(picks[1].items.some((item) => item.taskId === '2'), false);
  assert.equal(continued[0].session, SESSION);
  assert.equal(continued[0].name, 'Implement parser');
  assert.match(continued[0].prompt, /task #1 in resumed session run-inspect-1/);
  assert.match(continued[0].prompt, /untrusted task context/);
  assert.match(continued[0].prompt, /Description: Apply the parser fix/);
  chooseTask = false;
  assert.equal(await manager.continueTaskActive(config), null);
  assert.equal(continued.length, 1);
});

test('bounds task continuation selection and prompt helpers', () => {
  const items = actionableTaskQuickPickItems([
    { id: '1', subject: 'Done', description: '', status: 'completed', owner: null, blocked: false },
    { id: '2', subject: 'Blocked', description: '', status: 'pending', owner: null, blocked: true },
  ]);
  assert.deepEqual(items, []);
  const oversized = parseSessionInspector(envelope(inspectorReport()), SESSION);
  oversized.overview.task = 'x'.repeat(MAX_INSPECTOR_DOCUMENT_CHARS);
  assert.throws(() => renderSessionInspector(oversized), /exceeds 250000 rendered characters/);
  assert.throws(
    () => buildTaskContinuationPrompt(SESSION, {
      id: '3', subject: 'Large task', description: 'x'.repeat(4_000),
      status: 'pending', owner: null, activeForm: null,
    }),
    /exceeds 4000 characters/,
  );
});

test('refreshes the exact inspector in place and protects local document edits', async () => {
  let report = inspectorReport();
  let documentText = '';
  let replaceLocalEdits = false;
  let edits = 0;
  const reads = [];
  const warnings = [];
  const information = [];
  const document = {
    uri: { toString: () => 'untitled:session-inspector-refresh' },
    getText() { return documentText; },
    positionAt(offset) { return { offset }; },
  };
  const editor = {
    document,
    async edit(callback, options) {
      let replacement = null;
      callback({
        replace(range, value) {
          assert.deepEqual(range.start, { offset: 0 });
          assert.deepEqual(range.end, { offset: documentText.length });
          replacement = value;
        },
      });
      assert.deepEqual(options, { undoStopBefore: true, undoStopAfter: true });
      documentText = replacement;
      edits += 1;
      return true;
    },
  };
  const vscode = {
    Range: class Range {
      constructor(start, end) { this.start = start; this.end = end; }
    },
    window: {
      activeTextEditor: null,
      async showQuickPick(items) { return items[0]; },
      async showTextDocument(value) {
        assert.equal(value, document);
        this.activeTextEditor = editor;
        return editor;
      },
      async showWarningMessage(message, options, action) {
        warnings.push({ message, options, action });
        return replaceLocalEdits ? action : null;
      },
      showInformationMessage(message) { information.push(message); },
    },
    workspace: {
      async openTextDocument(options) {
        documentText = options.content;
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
    client: {
      async get(_config, root, session) {
        reads.push({ root, session });
        return parseSessionInspector(envelope(report), SESSION);
      },
    },
    terminals: {},
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };

  await manager.open(config, '/workspace/project');
  report = inspectorReport();
  report.overview.tokens = { input: 200, output: 40, total: 240 };
  assert.equal(await manager.refreshActive(config), document);
  assert.match(documentText, /Tokens: 200 input, 40 output, 240 total/);
  assert.equal(edits, 1);
  assert.equal(warnings.length, 0);

  documentText += '\nlocal inspector note\n';
  report.overview.tokens = { input: 300, output: 60, total: 360 };
  assert.equal(await manager.refreshActive(config), null);
  assert.match(documentText, /local inspector note/);
  assert.equal(edits, 1);
  assert.equal(warnings[0].options.modal, true);
  assert.match(warnings[0].options.detail, /Session: run-inspect-1/);

  replaceLocalEdits = true;
  assert.equal(await manager.refreshActive(config), document);
  assert.match(documentText, /Tokens: 300 input, 60 output, 360 total/);
  assert.doesNotMatch(documentText, /local inspector note/);
  assert.equal(edits, 2);

  assert.equal(await manager.refreshActive(config), document);
  assert.equal(edits, 2);
  assert.deepEqual(information, ['VibeAgent session inspector is already up to date.']);
  assert.deepEqual(reads, Array.from({ length: 5 }, () => ({
    root: '/workspace/project', session: SESSION,
  })));
});

test('refuses refresh when the active inspector changes while confirmation is open', async () => {
  let documentText = '';
  const report = inspectorReport();
  const document = {
    uri: { toString: () => 'untitled:session-inspector-refresh-race' },
    getText() { return documentText; },
    positionAt(offset) { return { offset }; },
  };
  let editCalled = false;
  const editor = {
    document,
    async edit() { editCalled = true; return true; },
  };
  const vscode = {
    Range: class Range {
      constructor(start, end) { this.start = start; this.end = end; }
    },
    window: {
      activeTextEditor: null,
      async showQuickPick(items) { return items[0]; },
      async showTextDocument() { this.activeTextEditor = editor; return editor; },
      async showWarningMessage(_message, _options, action) {
        documentText += '\nchanged while waiting\n';
        return action;
      },
      showInformationMessage() {},
    },
    workspace: {
      async openTextDocument(options) { documentText = options.content; return document; },
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
    client: { async get() { return parseSessionInspector(envelope(report), SESSION); } },
    terminals: {},
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };

  await manager.open(config, '/workspace/project');
  documentText += '\nlocal edit\n';
  report.overview.tokens = { input: 200, output: 40, total: 240 };
  await assert.rejects(manager.refreshActive(config), /changed during refresh/);
  assert.equal(editCalled, false);
  assert.match(documentText, /changed while waiting/);
});

test('revalidates and opens one inspected workspace file in the editor', async () => {
  const report = inspectorReport();
  const inspectorDocument = { uri: { toString: () => 'untitled:session-inspector-file' } };
  const fileDocument = { uri: { toString: () => 'file:/workspace/project/app.py' } };
  const reads = [];
  const picks = [];
  const opened = [];
  const shown = [];
  let resolverCalls = 0;
  let changeTarget = true;
  const vscode = {
    Uri: {
      file(value) { return { scheme: 'file', fsPath: value }; },
    },
    window: {
      activeTextEditor: null,
      async showQuickPick(items, options) {
        picks.push({ items, options });
        return items[0];
      },
      async showTextDocument(value, options) {
        shown.push({ value, options });
        this.activeTextEditor = { document: value };
        return this.activeTextEditor;
      },
      showInformationMessage() {},
    },
    workspace: {
      async openTextDocument(value) {
        if (value && value.language === 'markdown') return inspectorDocument;
        opened.push(value);
        return fileDocument;
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
    client: {
      async get(_config, root, session) {
        reads.push({ root, session });
        return parseSessionInspector(envelope(report), SESSION);
      },
    },
    resolveSessionFilePath: async (_root, sourcePath) => {
      resolverCalls += 1;
      if (changeTarget && resolverCalls % 2 === 0) return '/workspace/project/other.py';
      return `/workspace/project/${sourcePath}`;
    },
    terminals: {},
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };

  await manager.open(config, '/workspace/project');
  await assert.rejects(manager.openFileActive(config), /changed before it could be opened/);
  assert.deepEqual(opened, []);

  changeTarget = false;
  resolverCalls = 0;
  assert.equal(await manager.openFileActive(config), fileDocument);
  assert.equal(picks[1].options.title, 'Open VibeAgent Session File');
  assert.equal(picks[1].items[0].sourcePath, 'app.py');
  assert.deepEqual(opened, [{ scheme: 'file', fsPath: '/workspace/project/app.py' }]);
  assert.deepEqual(shown.at(-1), { value: fileDocument, options: { preview: false } });
  assert.deepEqual(reads, Array.from({ length: 3 }, () => ({
    root: '/workspace/project', session: SESSION,
  })));
});
