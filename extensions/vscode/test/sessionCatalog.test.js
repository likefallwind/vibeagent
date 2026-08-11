'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const test = require('node:test');
const {
  MAX_CATALOG_BYTES,
  SessionCatalog,
  parseSessionCatalog,
  sessionQuickPickItems,
} = require('../src/sessionCatalog');

function payload(items) {
  return Buffer.from(JSON.stringify({
    schemaVersion: 1,
    kind: 'local',
    sessions: { exists: Boolean(items.length), sessions: { items } },
  }));
}

function session(overrides = {}) {
  return {
    session: '019e9234-d1ac-72b1-b9bf-4dd7287446df',
    status: 'completed',
    events: 42,
    malformed: 0,
    lastEventTime: '2026-08-11T20:00:00+00:00',
    name: 'Fix parser',
    task: 'Repair the parser and run tests',
    completed: true,
    failed: false,
    blocked: false,
    ...overrides,
  };
}

function fakeChild(run) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.killSignals = [];
  child.kill = (signal) => child.killSignals.push(signal);
  process.nextTick(() => run(child));
  return child;
}

test('parses bounded session metadata into safe quick pick items', () => {
  const sessions = parseSessionCatalog(payload([session({ name: 'Review $(zap)' })]));
  assert.equal(sessions[0].name, 'Review [zap)');
  assert.deepEqual(sessionQuickPickItems(sessions)[0], {
    label: 'Review [zap)',
    description: 'completed | 2026-08-11T20:00:00+00:00',
    detail: '019e9234-d1ac-72b1-b9bf-4dd7287446df | Repair the parser and run tests',
    session: '019e9234-d1ac-72b1-b9bf-4dd7287446df',
  });
  assert.throws(() => parseSessionCatalog(payload([session({ session: '../escape' })])), /session ID/);
  assert.throws(() => parseSessionCatalog(payload([session({ name: '\n\t' })])), /session name/);
  assert.throws(() => parseSessionCatalog(payload([session(), session()])), /duplicate/);
  assert.throws(() => parseSessionCatalog(Buffer.from('{}')), /invalid session catalog/);
});

test('runs the provider-free catalog command without a shell', async () => {
  const calls = [];
  const previousToken = process.env.VIBEAGENT_IDE_CONTEXT_TOKEN;
  const previousFile = process.env.VIBEAGENT_IDE_CONTEXT_FILE;
  process.env.VIBEAGENT_IDE_CONTEXT_TOKEN = 'must-not-propagate';
  process.env.VIBEAGENT_IDE_CONTEXT_FILE = '/tmp/must-not-propagate';
  const catalog = new SessionCatalog({
    spawn(executable, args, options) {
      calls.push({ executable, args, options });
      return fakeChild((child) => {
        child.stdout.emit('data', payload([session()]));
        child.emit('close', 0);
      });
    },
  });
  let sessions;
  try {
    sessions = await catalog.list(
      { executable: 'python', args: ['-m', 'vibeagent'] },
      '/workspace/project',
    );
  } finally {
    if (previousToken === undefined) delete process.env.VIBEAGENT_IDE_CONTEXT_TOKEN;
    else process.env.VIBEAGENT_IDE_CONTEXT_TOKEN = previousToken;
    if (previousFile === undefined) delete process.env.VIBEAGENT_IDE_CONTEXT_FILE;
    else process.env.VIBEAGENT_IDE_CONTEXT_FILE = previousFile;
  }
  assert.equal(sessions.length, 1);
  assert.deepEqual(calls[0].args, [
    '-m', 'vibeagent', '--json', '--cwd', '/workspace/project', '--sessions',
  ]);
  assert.equal(calls[0].options.shell, false);
  assert.equal(calls[0].options.cwd, '/workspace/project');
  assert.equal(calls[0].options.env.VIBEAGENT_IDE_CONTEXT_TOKEN, undefined);
  assert.equal(calls[0].options.env.VIBEAGENT_IDE_CONTEXT_FILE, undefined);

  const emptyCatalog = new SessionCatalog({
    spawn() {
      return fakeChild((child) => {
        child.stdout.emit('data', payload([]));
        child.emit('close', 1);
      });
    },
  });
  assert.deepEqual(await emptyCatalog.list({ executable: 'python', args: [] }, '/workspace'), []);
});

test('bounds catalog output and execution time', async () => {
  const oversized = new SessionCatalog({
    spawn() {
      return fakeChild((child) => child.stdout.emit('data', Buffer.alloc(MAX_CATALOG_BYTES + 1)));
    },
  });
  await assert.rejects(
    oversized.list({ executable: 'python', args: [] }, '/workspace'),
    /exceeded 2 MiB/,
  );

  const timedOut = new SessionCatalog({ spawn: () => fakeChild(() => {}), timeoutMs: 5 });
  await assert.rejects(
    timedOut.list({ executable: 'python', args: [] }, '/workspace'),
    /timed out/,
  );
});
