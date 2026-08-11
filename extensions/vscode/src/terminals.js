'use strict';

const { buildLaunchSpec } = require('./core');
const { requireSessionId } = require('./sessionCatalog');

class InteractiveTerminalManager {
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.prepareEnvironment = options.prepareEnvironment || (() => ({}));
    this.entries = new Map();
    this.primaryByRoot = new Map();
    this.resumedByKey = new Map();
    this.newSessionCount = 0;
  }

  openPrimary(config, root) {
    let terminal = this.primaryByRoot.get(root);
    if (!terminal) {
      terminal = this._create('VibeAgent', config, root);
      this.primaryByRoot.set(root, terminal);
      this._track(terminal, root, 'primary');
    }
    terminal.show(false);
    return terminal;
  }

  openNew(config, root) {
    this.newSessionCount += 1;
    const suffix = this.newSessionCount > 1 ? ` ${this.newSessionCount}` : '';
    const terminal = this._create(`VibeAgent Session${suffix}`, config, root);
    this._track(terminal, root, `new:${this.newSessionCount}`);
    terminal.show(false);
    return terminal;
  }

  resume(config, root, sessionId, sessionName = null) {
    const safeId = requireSessionId(sessionId);
    const key = `${root}\0${safeId}`;
    let terminal = this.resumedByKey.get(key);
    if (!terminal) {
      const title = boundedTerminalTitle(sessionName) || safeId.slice(0, 20);
      terminal = this._create(`VibeAgent: ${title}`, config, root, ['--resume', safeId]);
      this.resumedByKey.set(key, terminal);
      this._track(terminal, root, `resume:${safeId}`, key);
    }
    terminal.show(false);
    return terminal;
  }

  resumeTask(config, root, sessionId, sessionName, task) {
    const safeId = requireSessionId(sessionId);
    const title = boundedTerminalTitle(sessionName) || safeId.slice(0, 20);
    const terminal = this._create(
      `VibeAgent Plan: ${title}`,
      config,
      root,
      ['--resume', safeId],
      task,
    );
    terminal.show(false);
    return terminal;
  }

  openTask(name, config, root, task) {
    const terminal = this._create(name, config, root, [], task);
    terminal.show(false);
    return terminal;
  }

  referenceTarget(root) {
    const active = this.vscode.window.activeTerminal;
    const activeEntry = active && this.entries.get(active);
    if (activeEntry && activeEntry.root === root) return active;
    const primary = this.primaryByRoot.get(root);
    if (primary) return primary;
    const candidates = [...this.entries.entries()].reverse();
    const recent = candidates.find(([, entry]) => entry.root === root);
    return recent ? recent[0] : null;
  }

  closed(terminal) {
    const entry = this.entries.get(terminal);
    if (!entry) return;
    this.entries.delete(terminal);
    if (this.primaryByRoot.get(entry.root) === terminal) this.primaryByRoot.delete(entry.root);
    if (entry.resumeKey && this.resumedByKey.get(entry.resumeKey) === terminal) {
      this.resumedByKey.delete(entry.resumeKey);
    }
  }

  dispose() {
    this.entries.clear();
    this.primaryByRoot.clear();
    this.resumedByKey.clear();
  }

  _create(name, config, root, extraArgs = [], task = undefined) {
    const spec = buildLaunchSpec(config, root, task);
    if (extraArgs.length) {
      const insertion = task === undefined ? spec.shellArgs.length : spec.shellArgs.length - 1;
      spec.shellArgs.splice(insertion, 0, ...extraArgs);
    }
    return this.vscode.window.createTerminal({
      name,
      ...spec,
      env: this.prepareEnvironment(root),
    });
  }

  _track(terminal, root, kind, resumeKey = null) {
    this.entries.set(terminal, { root, kind, resumeKey });
  }
}

function boundedTerminalTitle(value) {
  if (typeof value !== 'string') return null;
  const normalized = value.replace(/[\x00-\x1f\x7f]+/g, ' ').trim();
  return normalized ? normalized.slice(0, 80) : null;
}

module.exports = { InteractiveTerminalManager, boundedTerminalTitle };
