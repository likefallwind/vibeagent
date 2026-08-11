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
  const client = {
    async get(path) {
      if (path === '/api/state') return {
        projectRoot: '/workspace/project',
        agents: [{
          id: '0123456789ab', status: 'needs-input', startedAt: 'now', task: 'test',
          sessionName: 'background-test', pending: 0, approval: null, question: null,
        }],
      };
      return { stdout: 'running', stderr: '' };
    },
    async post(path, payload) { apiCalls.push([path, payload]); return { message: 'ok' }; },
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
  };
  const manager = new AgentPanelManager(vscode, {
    processFactory: () => process,
    refreshIntervalMs: 60_000,
  });
  t.after(() => manager.dispose());
  await manager.open('/workspace/project', { executable: 'python', args: [] });

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
  manager.dispose();
  assert.equal(process.disposed, true);
});
