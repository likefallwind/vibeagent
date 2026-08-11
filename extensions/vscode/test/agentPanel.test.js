'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const vm = require('node:vm');
const test = require('node:test');
const { AgentPanelManager } = require('../src/agentPanel');
const { getAgentPanelHtml } = require('../src/agentPanelView');

function disposable() { return { dispose() {} }; }

test('webview has a strict CSP, valid script, and no bearer token channel', () => {
  const html = getAgentPanelHtml('fixed-nonce');
  assert.match(html, /default-src 'none'/);
  assert.match(html, /script-src 'nonce-fixed-nonce'/);
  assert.doesNotMatch(html, /Bearer|#token|Authorization/);
  const script = html.match(/<script nonce="fixed-nonce">([\s\S]*?)<\/script>/)[1];
  assert.doesNotThrow(() => new vm.Script(script));
});

test('panel routes only validated actions and preserves exact request IDs', async (t) => {
  let receiveMessage;
  let disposePanel;
  const posted = [];
  const apiCalls = [];
  const getCalls = [];
  const executed = [];
  const client = {
    async get(apiPath) {
      getCalls.push(apiPath);
      if (apiPath === '/api/state') return {
        projectRoot: '/workspace/project',
        agents: [{
          id: '0123456789ab', status: 'needs-input', startedAt: 'now', task: 'test',
          sessionName: 'background-test', pending: 0, approval: null, question: null,
        }],
      };
      if (apiPath.endsWith('/logs')) return { stdout: 'running', stderr: '' };
      if (apiPath.endsWith('/changes')) return {
        agentId: '0123456789ab',
        sessionRoot: '/workspace/project/.vibeagent/worktrees/review',
        isolated: true,
        branch: 'vibeagent/review',
        baseCommit: 'a'.repeat(40),
        headCommit: 'b'.repeat(40),
        snapshotId: 'c'.repeat(64),
        omittedFiles: 0,
        files: [{
          path: 'src/app.py', committed: true, staged: false, unstaged: false,
          untracked: false, deleted: false,
        }],
      };
      const url = new URL(apiPath, 'http://127.0.0.1');
      return {
        path: url.searchParams.get('path'),
        side: url.searchParams.get('side'),
        content: url.searchParams.get('side') === 'base' ? 'old\n' : 'new\n',
      };
    },
    async post(path, payload) {
      apiCalls.push([path, payload]);
      if (path.endsWith('/integrate')) return {
        message: 'Applied 1 background agent file(s); 0 already matched.',
        agentId: '0123456789ab', snapshotId: 'c'.repeat(64),
        appliedFiles: ['src/app.py'], skippedFiles: [],
      };
      return { message: 'ok' };
    },
  };
  const process = { async start() { return client; }, dispose() { this.disposed = true; } };
  const panel = {
    webview: {
      html: '',
      onDidReceiveMessage(callback) { receiveMessage = callback; return disposable(); },
      postMessage(message) { posted.push(message); },
    },
    onDidDispose(callback) { disposePanel = callback; return disposable(); },
    reveal() {},
    dispose() { disposePanel(); },
  };
  const vscode = {
    ViewColumn: { Beside: 2 },
    window: { createWebviewPanel() { return panel; } },
    commands: { async executeCommand(...args) { executed.push(args); } },
    Uri: { file(value) { return { fsPath: value }; } },
  };
  const tracked = [];
  const changeProvider = {
    track(filePath, side, content) {
      const uri = { filePath, side, content };
      tracked.push(uri);
      return uri;
    },
  };
  const manager = new AgentPanelManager(vscode, {
    processFactory: () => process,
    changeProvider,
    refreshIntervalMs: 60_000,
  });
  t.after(() => manager.dispose());
  await manager.open('/workspace/project', { executable: 'python', args: [] });
  const changesMessage = posted.find((message) => message.type === 'changes');
  assert.equal(Object.hasOwn(changesMessage.changes, 'sessionRoot'), false);

  await receiveMessage({
    type: 'approval', agentId: '0123456789ab', requestId: 'a'.repeat(32), approved: true, scope: 'once',
  });
  assert.deepEqual(apiCalls[0], [
    '/api/agents/0123456789ab/approval',
    { requestId: 'a'.repeat(32), approved: true, scope: 'once' },
  ]);

  await receiveMessage({ type: 'stop', agentId: '../unsafe' });
  assert.equal(apiCalls.length, 1);
  assert.match(posted.findLast((message) => message.type === 'error').message, /agent ID is invalid/);

  await receiveMessage({ type: 'reviewFile', agentId: '0123456789ab', path: 'src/app.py' });
  assert.equal(tracked[0].content, 'old\n');
  assert.equal(tracked[1].content, 'new\n');
  assert.equal(executed.at(-1)[0], 'vscode.diff');
  assert.match(getCalls.at(-2), /path=src%2Fapp.py&side=base/);

  await receiveMessage({ type: 'openWorktree', agentId: '0123456789ab' });
  assert.deepEqual(executed.at(-1), [
    'vscode.openFolder',
    { fsPath: '/workspace/project/.vibeagent/worktrees/review' },
    { forceNewWindow: true },
  ]);

  await receiveMessage({
    type: 'integrate', agentId: '0123456789ab', snapshotId: 'c'.repeat(64),
  });
  assert.deepEqual(apiCalls.at(-1), [
    '/api/agents/0123456789ab/integrate', { snapshotId: 'c'.repeat(64) },
  ]);
  assert.match(posted.findLast((message) => message.type === 'notice').message, /Applied 1/);

  const callCount = apiCalls.length;
  await receiveMessage({
    type: 'integrate', agentId: '0123456789ab', snapshotId: 'C'.repeat(64),
  });
  assert.equal(apiCalls.length, callCount);
  assert.match(posted.findLast((message) => message.type === 'error').message, /invalid or stale/);

  await receiveMessage({ type: 'reviewFile', agentId: '0123456789ab', path: '../secret' });
  assert.match(posted.findLast((message) => message.type === 'error').message, /invalid or stale/);
  manager.dispose();
  assert.equal(process.disposed, true);
});
