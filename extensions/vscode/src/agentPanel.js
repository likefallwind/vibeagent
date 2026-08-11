'use strict';

const crypto = require('node:crypto');
const path = require('node:path');
const { RemoteControlProcess } = require('./remote');
const { getAgentPanelHtml } = require('./agentPanelView');

const AGENT_ID = /^[0-9a-f]{12}$/;
const REQUEST_ID = /^[0-9a-f]{32}$/;
const MAX_TEXT_CHARS = 8_000;
const AGENT_ACTIONS = new Set([
  'messages', 'approval', 'answer', 'stop', 'respawn', 'remove', 'logs', 'changes', 'change',
]);

class AgentPanelManager {
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.processFactory = options.processFactory || (() => new RemoteControlProcess());
    this.changeProvider = options.changeProvider || null;
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
      changes: new Map(),
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
          await this._refreshAgentDetails(session);
          return;
        case 'reviewFile':
          await this._reviewFile(session, message.agentId, message.path);
          return;
        case 'openWorktree':
          await this._openWorktree(session, message.agentId);
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
      await this._refreshAgentDetails(session);
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

  async _refreshAgentDetails(session) {
    await this._refreshLogs(session);
    await this._refreshChanges(session);
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

  async _refreshChanges(session) {
    if (!session.client || !session.selectedId || session.disposed) return;
    const agentId = requireAgentId(session.selectedId);
    try {
      const changes = await session.client.get(agentPath(agentId, 'changes'));
      if (!validChanges(changes, agentId)) {
        throw new Error('Remote Control returned invalid agent changes.');
      }
      session.changes.set(agentId, changes);
      const { sessionRoot: _privateRoot, ...publicChanges } = changes;
      this._post(session, { type: 'changes', agentId, changes: publicChanges, error: null });
    } catch (error) {
      session.changes.delete(agentId);
      const message = error instanceof Error ? error.message : String(error);
      this._post(session, { type: 'changes', agentId, changes: null, error: message.slice(0, 1_000) });
    }
  }

  async _reviewFile(session, rawAgentId, rawPath) {
    if (!this.changeProvider) throw new Error('VibeAgent change document provider is unavailable.');
    const agentId = requireAgentId(rawAgentId);
    const changes = session.changes.get(agentId);
    const filePath = requireChangedPath(changes, rawPath);
    const [base, current] = await Promise.all([
      session.client.get(changeContentPath(agentId, filePath, 'base')),
      session.client.get(changeContentPath(agentId, filePath, 'current')),
    ]);
    if (!validContent(base, filePath, 'base') || !validContent(current, filePath, 'current')) {
      throw new Error('Remote Control returned invalid change content.');
    }
    const original = this.changeProvider.track(filePath, 'base', base.content);
    const modified = this.changeProvider.track(filePath, 'current', current.content);
    await this.vscode.commands.executeCommand(
      'vscode.diff',
      original,
      modified,
      `${filePath} (Agent base to current)`,
    );
  }

  async _openWorktree(session, rawAgentId) {
    const agentId = requireAgentId(rawAgentId);
    const changes = session.changes.get(agentId);
    const root = changes && changes.sessionRoot;
    if (!changes || !changes.isolated || typeof root !== 'string' || !path.isAbsolute(root) || root.includes('\0')) {
      throw new Error('This agent does not have an isolated worktree to open.');
    }
    await this.vscode.commands.executeCommand(
      'vscode.openFolder',
      this.vscode.Uri.file(root),
      { forceNewWindow: true },
    );
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

function changeContentPath(agentId, filePath, side) {
  const query = new URLSearchParams({ path: filePath, side });
  return `${agentPath(agentId, 'change')}?${query.toString()}`;
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

function validChanges(value, agentId) {
  return Boolean(
    value
    && typeof value === 'object'
    && value.agentId === agentId
    && typeof value.sessionRoot === 'string'
    && path.isAbsolute(value.sessionRoot)
    && typeof value.isolated === 'boolean'
    && (value.branch === null || typeof value.branch === 'string')
    && typeof value.baseCommit === 'string'
    && typeof value.headCommit === 'string'
    && Number.isInteger(value.omittedFiles)
    && value.omittedFiles >= 0
    && Array.isArray(value.files)
    && value.files.length <= 200
    && value.files.every((item) => (
      item
      && typeof item === 'object'
      && typeof item.path === 'string'
      && item.path.length > 0
      && item.path.length <= 1_000
      && !path.isAbsolute(item.path)
      && !item.path.split(/[\\/]/).includes('..')
      && ['committed', 'staged', 'unstaged', 'untracked', 'deleted'].every(
        (field) => typeof item[field] === 'boolean',
      )
    )),
  );
}

function requireChangedPath(changes, value) {
  if (!changes || typeof value !== 'string' || !changes.files.some((item) => item.path === value)) {
    throw new Error('Changed file is invalid or stale.');
  }
  return value;
}

function validContent(value, filePath, side) {
  return Boolean(
    value
    && typeof value === 'object'
    && value.path === filePath
    && value.side === side
    && typeof value.content === 'string'
    && Buffer.byteLength(value.content, 'utf8') <= 1_048_576,
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
  validChanges,
  validState,
};
