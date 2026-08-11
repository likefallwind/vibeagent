'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { RewindReviewManager } = require('../src/sessionRewind');
const {
  SessionRewindClient,
  parseRewindPoints,
  parseRewindPreview,
  parseRewindResult,
} = require('../src/sessionRewindClient');

const SESSION = 'run-123';
const CHECKPOINT = '2026-08-11T00-00-00-000Z-rewind01';

function envelope(key, report) {
  return { schemaVersion: 1, kind: 'local', [key]: report };
}

function pointsReport(overrides = {}) {
  return {
    projectRoot: '/workspace/project',
    ok: true,
    exists: true,
    session: SESSION,
    total: 1,
    truncated: false,
    points: [{
      checkpointId: CHECKPOINT,
      label: 'before parser edit',
      createdAt: '2026-08-11T00:00:00Z',
      eventLine: 12,
    }],
    message: 'Found 1 rewind point.',
    ...overrides,
  };
}

function previewReport(overrides = {}) {
  return {
    ok: true,
    canRewind: true,
    session: SESSION,
    checkpointId: CHECKPOINT,
    mode: 'both',
    eventLine: 12,
    codeWillChange: true,
    conversationWillBranch: true,
    message: 'Session rewind preflight passed.',
    ...overrides,
  };
}

function resultReport(overrides = {}) {
  return {
    ok: true,
    rewound: true,
    changed: true,
    sourceSession: SESSION,
    newSession: 'run-rewound',
    checkpointId: CHECKPOINT,
    mode: 'both',
    codeRestored: true,
    conversationBranched: true,
    message: 'Rewound both.\n  newSession: run-rewound',
    ...overrides,
  };
}

test('uses exact provider-free rewind CLI arguments and validates target identity', async () => {
  const calls = [];
  const local = {
    async run(_config, _root, args) {
      calls.push(args);
      if (args[0] === '--session-rewind-points') {
        return { code: 0, payload: envelope('sessionRewindPoints', pointsReport()) };
      }
      if (args[0] === '--checkpoint-diff') {
        return {
          code: 0,
          payload: envelope('checkpointDiff', {
            ok: true,
            exists: true,
            checkpoint: { id: CHECKPOINT },
            diff: {
              stagedPatch: '', stagedTruncated: false,
              unstagedPatch: 'diff --git a/app.py b/app.py\n', unstagedTruncated: false,
            },
            message: 'Read checkpoint diff.',
          }),
        };
      }
      if (args[0] === '--check-session-rewind') {
        return { code: 0, payload: envelope('checkSessionRewind', previewReport()) };
      }
      return { code: 0, payload: envelope('sessionRewind', resultReport()) };
    },
  };
  const client = new SessionRewindClient({ client: local });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };
  await client.points(config, '/workspace/project', SESSION);
  await client.diff(config, '/workspace/project', CHECKPOINT);
  await client.preview(config, '/workspace/project', SESSION, CHECKPOINT, 'both');
  const result = await client.execute(config, '/workspace/project', SESSION, CHECKPOINT, 'both');

  assert.deepEqual(calls, [
    ['--session-rewind-points', SESSION],
    ['--checkpoint-diff', CHECKPOINT],
    ['--check-session-rewind', SESSION, CHECKPOINT, 'both'],
    ['--session-rewind', SESSION, CHECKPOINT, 'both'],
  ]);
  assert.equal(result.newSession, 'run-rewound');
  assert.throws(
    () => parseRewindPoints(envelope('sessionRewindPoints', pointsReport({ session: '../bad' })), SESSION),
    /session ID/,
  );
  assert.throws(
    () => parseRewindPreview(envelope('checkSessionRewind', previewReport({ mode: 'code' })), SESSION, CHECKPOINT, 'both'),
    /wrong target/,
  );
  assert.throws(
    () => parseRewindResult(envelope('sessionRewind', resultReport({ checkpointId: '../bad' })), SESSION, CHECKPOINT, 'both'),
    /checkpoint ID/,
  );
});

test('reviews checkpoint patches, rechecks safety, confirms, and resumes the new branch', async () => {
  const calls = [];
  const quickPickTitles = [];
  const warnings = [];
  const resumed = [];
  let documentCount = 0;
  const vscode = {
    window: {
      activeTextEditor: null,
      async showQuickPick(items, options) {
        quickPickTitles.push(options.title);
        return items[0];
      },
      async showTextDocument(document, options) {
        this.activeTextEditor = { document };
        calls.push(['showDocument', options]);
      },
      async showWarningMessage(message, options, action) {
        warnings.push({ message, options, action });
        return action;
      },
      showInformationMessage(message) { calls.push(['information', message]); },
    },
    workspace: {
      async openTextDocument(options) {
        documentCount += 1;
        calls.push(['openDocument', options]);
        return {
          uri: { toString: () => `untitled:rewind-${documentCount}` },
          getText: () => 'user edits do not control rewind metadata',
        };
      },
    },
  };
  const client = {
    async points() { calls.push(['points']); return { points: pointsReport().points }; },
    async preview(_config, _root, session, checkpoint, mode) {
      calls.push(['preview', session, checkpoint, mode]);
      return previewReport();
    },
    async diff() {
      calls.push(['diff']);
      return {
        stagedPatch: 'diff --git a/app.py b/app.py\n',
        unstagedPatch: '',
        stagedTruncated: false,
        unstagedTruncated: false,
      };
    },
    async execute(_config, _root, session, checkpoint, mode) {
      calls.push(['execute', session, checkpoint, mode]);
      return parseRewindResult(envelope('sessionRewind', resultReport()), SESSION, CHECKPOINT, 'both');
    },
  };
  const manager = new RewindReviewManager(vscode, {
    catalog: {
      async list() {
        return [{
          session: SESSION, status: 'completed', events: 10, malformed: 0,
          lastEventTime: '2026-08-11T00:00:00Z', name: 'Parser repair', task: 'Fix parser',
          completed: true, failed: false, blocked: false,
        }];
      },
    },
    client,
    terminals: {
      resume(config, root, session, name) { resumed.push({ config, root, session, name }); },
    },
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };
  const document = await manager.open(config, '/workspace/project');
  const openCall = calls.find((item) => item[0] === 'openDocument');
  assert.match(openCall[1].content, /## Staged Patch/);
  assert.match(openCall[1].content, /diff --git a\/app.py/);
  assert.deepEqual(quickPickTitles, [
    'Review VibeAgent Session Rewind',
    'Choose VibeAgent Rewind Checkpoint',
    'Choose VibeAgent Rewind Mode',
  ]);

  const result = await manager.executeActive(config);
  assert.equal(calls.filter((item) => item[0] === 'preview').length, 2);
  assert.deepEqual(calls.find((item) => item[0] === 'execute'), [
    'execute', SESSION, CHECKPOINT, 'both',
  ]);
  assert.equal(warnings[0].options.modal, true);
  assert.match(warnings[0].options.detail, /replace the current tracked/);
  assert.equal(result.newSession, 'run-rewound');
  assert.equal(resumed[0].session, 'run-rewound');
  assert.match(resumed[0].name, /Rewind: Parser repair/);

  manager.closed(document);
  await assert.rejects(manager.executeActive(config), /not a VibeAgent rewind review/);
});
