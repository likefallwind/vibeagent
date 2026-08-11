'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const test = require('node:test');
const {
  RemoteControlProcess,
  parseRemoteControlUrl,
  requestJson,
} = require('../src/remote');

test('accepts only authenticated loopback Remote Control URLs', () => {
  const token = 't'.repeat(43);
  assert.deepEqual(
    parseRemoteControlUrl(`http://127.0.0.1:43123/#token=${token}`),
    { baseUrl: 'http://127.0.0.1:43123/', token },
  );
  for (const value of [
    `http://localhost:43123/#token=${token}`,
    `https://127.0.0.1:43123/#token=${token}`,
    'http://127.0.0.1:43123/#token=short',
    `http://192.168.1.2:43123/#token=${token}`,
  ]) assert.throws(() => parseRemoteControlUrl(value), /127\.0\.0\.1/);
});

test('starts Remote Control without a shell and keeps credentials in the client', async () => {
  const stdout = new EventEmitter();
  const stderr = new EventEmitter();
  const child = new EventEmitter();
  child.stdout = stdout;
  child.stderr = stderr;
  child.killed = false;
  child.exitCode = null;
  child.signalCode = null;
  child.kill = (signal) => { child.killed = true; child.signal = signal; };
  let invocation;
  const process = new RemoteControlProcess({
    spawn(executable, args, options) {
      invocation = { executable, args, options };
      queueMicrotask(() => stdout.emit('data', Buffer.from(`  open: http://127.0.0.1:4123/#token=${'a'.repeat(43)}\n`)));
      return child;
    },
    startupTimeoutMs: 100,
  });

  const client = await process.start(
    { executable: 'python3', args: ['-m', 'vibeagent'] },
    '/workspace/project',
    { VIBEAGENT_IDE_CONTEXT_TOKEN: 'private' },
  );

  assert.equal(invocation.executable, 'python3');
  assert.deepEqual(invocation.args, [
    '-m', 'vibeagent', 'remote-control', '--cwd', '/workspace/project', '--remote-control-port', '0',
  ]);
  assert.equal(invocation.options.shell, undefined);
  assert.equal(invocation.options.env.PYTHONUNBUFFERED, '1');
  assert.equal(invocation.options.env.VIBEAGENT_IDE_CONTEXT_TOKEN, 'private');
  assert.equal(client.token, 'a'.repeat(43));
  process.dispose();
  assert.equal(child.signal, 'SIGTERM');
});

test('sends bounded authenticated JSON API requests', async () => {
  let observed;
  let responsePayload = '{"message":"ok"}';
  function fakeRequest(url, options, callback) {
    const request = new EventEmitter();
    const chunks = [];
    request.setTimeout = () => {};
    request.write = (chunk) => chunks.push(chunk);
    request.destroy = (error) => request.emit('error', error);
    request.end = () => {
      observed = { url: url.toString(), options, body: Buffer.concat(chunks).toString('utf8') };
      const response = new EventEmitter();
      response.statusCode = 200;
      callback(response);
      response.emit('data', Buffer.from(responsePayload));
      response.emit('end');
    };
    return request;
  }

  const result = await requestJson(
    'http://127.0.0.1:4123/',
    's'.repeat(43),
    'POST',
    '/api/agents',
    { task: 'test' },
    fakeRequest,
  );

  assert.deepEqual(result, { message: 'ok' });
  assert.equal(observed.url, 'http://127.0.0.1:4123/api/agents');
  assert.equal(observed.options.headers.Authorization, `Bearer ${'s'.repeat(43)}`);
  assert.equal(observed.options.agent, false);
  assert.equal(observed.body, '{"task":"test"}');

  responsePayload = JSON.stringify({
    path: 'large.txt',
    side: 'current',
    content: '\n'.repeat(1024 * 1024),
  });
  const large = await requestJson(
    'http://127.0.0.1:4123/',
    's'.repeat(43),
    'GET',
    '/api/agents/0123456789ab/change?path=large.txt&side=current',
    undefined,
    fakeRequest,
  );
  assert.equal(large.content.length, 1024 * 1024);

  await assert.rejects(
    requestJson('http://127.0.0.1:4123/', 's'.repeat(43), 'GET', 'http://example.com/api/state', undefined, fakeRequest),
    /path is invalid/,
  );
});
