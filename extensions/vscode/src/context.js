'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { normalizeDiagnostics, selectionLineRange, workspaceRelativePath } = require('./core');

class IdeContextBridge {
  constructor(workspaceRoot, options = {}) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vibeagent-ide-'));
    if (process.platform !== 'win32') fs.chmodSync(this.directory, 0o700);
    this.contextFile = path.join(this.directory, 'context.json');
    this.token = crypto.randomBytes(32).toString('hex');
    this.disposed = false;
    this.registryRoot = options.registryRoot || defaultRegistryRoot();
    this.connectionFile = options.publish === false
      ? null
      : path.join(this.registryRoot, `${crypto.randomUUID()}.json`);
    this.write({ file: null, dirty: false, selection: null, diagnostics: [] });
    if (this.connectionFile) {
      publishConnection(this.connectionFile, this.workspaceRoot, this.contextFile, this.token);
      this.heartbeat = setInterval(() => this.touchConnection(), 30_000);
      if (typeof this.heartbeat.unref === 'function') this.heartbeat.unref();
    }
  }

  environment() {
    return {
      VIBEAGENT_IDE_CONTEXT_FILE: this.contextFile,
      VIBEAGENT_IDE_CONTEXT_TOKEN: this.token,
    };
  }

  update(editor, diagnostics) {
    if (!editor || editor.document.uri.scheme !== 'file') {
      this.write({ file: null, dirty: false, selection: null, diagnostics: [] });
      return;
    }
    const file = workspaceRelativePath(this.workspaceRoot, editor.document.uri.fsPath);
    const normalized = normalizeDiagnostics(diagnostics);
    this.write({
      file,
      dirty: Boolean(editor.document.isDirty),
      selection: selectionLineRange(editor.selection),
      diagnostics: normalized.items,
    });
  }

  write(context) {
    if (this.disposed) return;
    const payload = JSON.stringify({
      version: 1,
      token: this.token,
      workspaceRoot: this.workspaceRoot,
      ...context,
    });
    const temporary = path.join(this.directory, `.context-${crypto.randomUUID()}.tmp`);
    try {
      fs.writeFileSync(temporary, payload, { encoding: 'utf8', flag: 'wx', mode: 0o600 });
      if (process.platform !== 'win32') fs.chmodSync(temporary, 0o600);
      fs.renameSync(temporary, this.contextFile);
      this.touchConnection();
    } finally {
      try { fs.unlinkSync(temporary); } catch (error) {
        if (!error || error.code !== 'ENOENT') throw error;
      }
    }
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    if (this.heartbeat) clearInterval(this.heartbeat);
    if (this.connectionFile) {
      try { fs.unlinkSync(this.connectionFile); } catch (error) {
        if (!error || error.code !== 'ENOENT') throw error;
      }
    }
    fs.rmSync(this.directory, { recursive: true, force: true });
  }

  touchConnection() {
    if (!this.connectionFile || this.disposed) return;
    try {
      const now = new Date();
      fs.utimesSync(this.connectionFile, now, now);
    } catch (error) {
      if (!error || error.code !== 'ENOENT') throw error;
    }
  }
}

function defaultRegistryRoot() {
  const suffix = typeof process.getuid === 'function' ? String(process.getuid()) : 'user';
  return path.join(os.tmpdir(), `vibeagent-ide-connections-${suffix}`);
}

function publishConnection(connectionFile, workspaceRoot, contextFile, token) {
  const registryRoot = path.dirname(connectionFile);
  fs.mkdirSync(registryRoot, { recursive: true, mode: 0o700 });
  const metadata = fs.lstatSync(registryRoot);
  if (!metadata.isDirectory() || metadata.isSymbolicLink()) {
    throw new Error('VibeAgent IDE connection registry must be a regular directory.');
  }
  if (process.platform !== 'win32') fs.chmodSync(registryRoot, 0o700);
  pruneStaleConnections(registryRoot);
  const payload = JSON.stringify({
    version: 1,
    workspaceRoot,
    contextFile,
    token,
    pid: process.pid,
  });
  const temporary = path.join(registryRoot, `.connection-${crypto.randomUUID()}.tmp`);
  try {
    fs.writeFileSync(temporary, payload, { encoding: 'utf8', flag: 'wx', mode: 0o600 });
    if (process.platform !== 'win32') fs.chmodSync(temporary, 0o600);
    fs.renameSync(temporary, connectionFile);
  } finally {
    try { fs.unlinkSync(temporary); } catch (error) {
      if (!error || error.code !== 'ENOENT') throw error;
    }
  }
}

function pruneStaleConnections(registryRoot) {
  const cutoff = Date.now() - (24 * 60 * 60 * 1000);
  for (const name of fs.readdirSync(registryRoot)) {
    if (!name.endsWith('.json')) continue;
    const candidate = path.join(registryRoot, name);
    try {
      const metadata = fs.lstatSync(candidate);
      if (metadata.isFile() && !metadata.isSymbolicLink() && metadata.mtimeMs < cutoff) {
        fs.unlinkSync(candidate);
      }
    } catch (error) {
      if (!error || error.code !== 'ENOENT') throw error;
    }
  }
}

module.exports = { IdeContextBridge, defaultRegistryRoot };
