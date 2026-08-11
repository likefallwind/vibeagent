'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const test = require('node:test');
const {
  MAX_JSON_BYTES,
  LocalJsonClient,
  parseLocalEnvelope,
} = require('../src/localCli');

function fakeChild(run) {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.killSignals = [];
  child.kill = (signal) => child.killSignals.push(signal);
  process.nextTick(() => run(child));
  return child;
}

test('runs bounded provider-free local JSON commands without a shell', async () => {
  const calls = [];
  const client = new LocalJsonClient({
    spawn(executable, args, options) {
      calls.push({ executable, args, options });
      return fakeChild((child) => {
        child.stdout.emit('data', Buffer.from(JSON.stringify({
          schemaVersion: 1,
          kind: 'local',
          sessionPlan: { exists: true },
        })));
        child.emit('close', 0);
      });
    },
  });
  const previousFile = process.env.VIBEAGENT_IDE_CONTEXT_FILE;
  const previousToken = process.env.VIBEAGENT_IDE_CONTEXT_TOKEN;
  process.env.VIBEAGENT_IDE_CONTEXT_FILE = '/tmp/private';
  process.env.VIBEAGENT_IDE_CONTEXT_TOKEN = 'private';
  let result;
  try {
    result = await client.run(
      { executable: 'python', args: ['-m', 'vibeagent'] },
      '/workspace/project',
      ['--plan', 'run-1'],
    );
  } finally {
    if (previousFile === undefined) delete process.env.VIBEAGENT_IDE_CONTEXT_FILE;
    else process.env.VIBEAGENT_IDE_CONTEXT_FILE = previousFile;
    if (previousToken === undefined) delete process.env.VIBEAGENT_IDE_CONTEXT_TOKEN;
    else process.env.VIBEAGENT_IDE_CONTEXT_TOKEN = previousToken;
  }
  assert.equal(result.code, 0);
  assert.deepEqual(calls[0].args, [
    '-m', 'vibeagent', '--json', '--cwd', '/workspace/project', '--plan', 'run-1',
  ]);
  assert.equal(calls[0].options.shell, false);
  assert.equal(calls[0].options.env.VIBEAGENT_IDE_CONTEXT_FILE, undefined);
  assert.equal(calls[0].options.env.VIBEAGENT_IDE_CONTEXT_TOKEN, undefined);
});

test('rejects invalid, oversized, and timed-out local command output', async () => {
  assert.throws(() => parseLocalEnvelope('{}'), /invalid local command envelope/);
  assert.throws(() => parseLocalEnvelope('{'), /invalid JSON/);

  const oversized = new LocalJsonClient({
    spawn: () => fakeChild((child) => child.stdout.emit('data', Buffer.alloc(MAX_JSON_BYTES + 1))),
  });
  await assert.rejects(
    oversized.run({ executable: 'python', args: [] }, '/workspace', ['--sessions']),
    /exceeded 2 MiB/,
  );

  const timedOut = new LocalJsonClient({ spawn: () => fakeChild(() => {}), timeoutMs: 5 });
  await assert.rejects(
    timedOut.run({ executable: 'python', args: [] }, '/workspace', ['--sessions']),
    /timed out/,
  );
});
