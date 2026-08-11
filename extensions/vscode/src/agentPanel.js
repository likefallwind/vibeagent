'use strict';

const crypto = require('node:crypto');
const { RemoteControlProcess } = require('./remote');
const { getAgentPanelHtml } = require('./agentPanelView');

const AGENT_ID = /^[0-9a-f]{12}$/;
const REQUEST_ID = /^[0-9a-f]{32}$/;
const MAX_TEXT_CHARS = 8_000;
const AGENT_ACTIONS = new Set(['messages', 'approval', 'answer', 'stop', 'respawn', 'remove', 'logs']);

class AgentPanelManager {
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.processFactory = options.processFactory || (() => new RemoteControlProcess());
    this.refreshIntervalMs = options.refreshIntervalMs || 1_000;
    this.sessions = new Map();
  }

  async open(workspaceRoot, launch, environment = {}) {
    const existing = this.sessions.get(workspaceRoot);
    if (existing) {
      existing.panel.reveal(this.vscode.ViewColumn.Beside, true);
      if (!existing.client) await this._start(existing);
      return;
    }
    const panel = this.vscode.window.createWebviewPanel(
      'vibeagent.agentPanel',
      'VibeAgent Agents',
      this.vscode.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true },
    );
    panel.webview.html = getAgentPanelHtml(crypto.randomBytes(24).toString('base64url'));
    const session = {
      panel,
      process: null,
      client: null,
      workspaceRoot,
      launch,
      environment,
      starting: false,
      selectedId: null,
      disposed: false,
      refreshing: false,
      timer: null,
      subscriptions: [],
    };
    this.sessions.set(workspaceRoot, session);
    session.subscriptions.push(
      panel.webview.onDidReceiveMessage((message) => this._handle(session, message)),
      panel.onDidDispose(() => this._disposeSession(workspaceRoot, session)),
    );
    await this._start(session);
  }

  async _handle(session, message) {
    if (session.disposed || !message || typeof message !== 'object') return;
    if (!session.client) {
      if (message.type === 'refresh') await this._start(session);
      return;
    }
    try {
      switch (message.type) {
        case 'refresh':
          await this._refresh(session);
          return;
        case 'select':
          session.selectedId = requireAgentId(message.agentId);
          await this._refreshLogs(session);
          return;
        case 'dispatch':
          await session.client.post('/api/agents', { task: requireText(message.task, 'Task') });
          break;
        case 'message':
          await session.client.post(agentPath(message.agentId, 'messages'), {
            message: requireText(message.message, 'Message'),
          });
          break;
        case 'approval':
          await session.client.post(agentPath(message.agentId, 'approval'), {
            requestId: requireRequestId(message.requestId),
            approved: requireBoolean(message.approved, 'approved'),
            scope: requireScope(message.scope),
          });
          break;
        case 'answer':
          await session.client.post(agentPath(message.agentId, 'answer'), {
            requestId: requireRequestId(message.requestId),
            answer: requireText(message.answer, 'Answer'),
          });
          break;
        case 'stop':
        case 'respawn':
        case 'remove':
          await session.client.post(agentPath(message.agentId, message.type), {});
          break;
        default:
          throw new Error('Agent Panel message type is not allowed.');
      }
      this._post(session, { type: 'notice', message: 'Action completed.' });
      await this._refresh(session);
    } catch (error) {
      this._postError(session, error);
      await this._refresh(session);
    }
  }

  async _start(session) {
    if (session.disposed || session.starting || session.client) return;
    session.starting = true;
    if (session.process) session.process.dispose();
    session.process = this.processFactory();
    this._post(session, { type: 'notice', message: 'Starting local control service...' });
    try {
      session.client = await session.process.start(
        session.launch,
        session.workspaceRoot,
        session.environment,
      );
      if (session.disposed) return;
      await this._refresh(session);
      if (!session.timer) {
        session.timer = setInterval(() => this._refresh(session), this.refreshIntervalMs);
      }
    } catch (error) {
      session.client = null;
      session.process.dispose();
      this._postError(session, error);
    } finally {
      session.starting = false;
    }
  }

  async _refresh(session) {
    if (!session.client || session.disposed || session.refreshing) return;
    session.refreshing = true;
    try {
      const state = await session.client.get('/api/state');
      if (!validState(state)) throw new Error('Remote Control returned an invalid agent state.');
      if (session.selectedId && !state.agents.some((agent) => agent.id === session.selectedId)) {
        session.selectedId = null;
      }
      if (!session.selectedId && state.agents.length) session.selectedId = state.agents[0].id;
      this._post(session, { type: 'state', state });
      await this._refreshLogs(session);
    } catch (error) {
      this._postError(session, error);
      if (isConnectionFailure(error)) {
        session.client = null;
        session.process.dispose();
        if (session.timer) clearInterval(session.timer);
        session.timer = null;
      }
    } finally {
      session.refreshing = false;
    }
  }

  async _refreshLogs(session) {
    if (!session.client || !session.selectedId || session.disposed) return;
    const agentId = requireAgentId(session.selectedId);
    const logs = await session.client.get(agentPath(agentId, 'logs'));
    if (!logs || typeof logs.stdout !== 'string' || typeof logs.stderr !== 'string') {
      throw new Error('Remote Control returned invalid agent logs.');
    }
    this._post(session, { type: 'logs', agentId, stdout: logs.stdout, stderr: logs.stderr });
  }

  _post(session, payload) {
    if (!session.disposed) session.panel.webview.postMessage(payload);
  }

  _postError(session, error) {
    const message = error instanceof Error ? error.message : String(error);
    this._post(session, { type: 'error', message: message.slice(0, 1_000) });
  }

  _disposeSession(workspaceRoot, session) {
    if (session.disposed) return;
    session.disposed = true;
    if (session.timer) clearInterval(session.timer);
    if (session.process) session.process.dispose();
    for (const subscription of session.subscriptions) subscription.dispose();
    if (this.sessions.get(workspaceRoot) === session) this.sessions.delete(workspaceRoot);
  }

  dispose() {
    for (const [root, session] of this.sessions) {
      this._disposeSession(root, session);
      session.panel.dispose();
    }
  }
}

function agentPath(agentId, suffix) {
  if (!AGENT_ACTIONS.has(suffix)) throw new Error('Background agent action is invalid.');
  return `/api/agents/${requireAgentId(agentId)}/${suffix}`;
}

function requireAgentId(value) {
  if (typeof value !== 'string' || !AGENT_ID.test(value)) throw new Error('Background agent ID is invalid.');
  return value;
}

function requireRequestId(value) {
  if (typeof value !== 'string' || !REQUEST_ID.test(value)) throw new Error('Agent request ID is invalid or stale.');
  return value;
}

function requireText(value, label) {
  if (typeof value !== 'string' || !value.trim() || value.includes('\0') || value.length > MAX_TEXT_CHARS) {
    throw new Error(`${label} must contain 1 to ${MAX_TEXT_CHARS} characters.`);
  }
  return value.trim();
}

function requireBoolean(value, label) {
  if (typeof value !== 'boolean') throw new Error(`${label} must be boolean.`);
  return value;
}

function requireScope(value) {
  if (value !== 'once' && value !== 'session') throw new Error('Approval scope is invalid.');
  return value;
}

function validState(value) {
  return Boolean(
    value
    && typeof value === 'object'
    && typeof value.projectRoot === 'string'
    && Array.isArray(value.agents)
    && value.agents.every((agent) => agent && typeof agent === 'object' && AGENT_ID.test(agent.id)),
  );
}

function isConnectionFailure(error) {
  return Boolean(
    error
    && typeof error === 'object'
    && ['ECONNREFUSED', 'ECONNRESET', 'EPIPE'].includes(error.code),
  );
}

module.exports = {
  AgentPanelManager,
  agentPath,
  requireRequestId,
  requireText,
  validState,
};
