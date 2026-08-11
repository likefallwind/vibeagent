'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { normalizeDiagnostics, selectionLineRange, workspaceRelativePath } = require('./core');

class IdeContextBridge {
  constructor(workspaceRoot) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vibeagent-ide-'));
    if (process.platform !== 'win32') fs.chmodSync(this.directory, 0o700);
    this.contextFile = path.join(this.directory, 'context.json');
    this.token = crypto.randomBytes(32).toString('hex');
    this.disposed = false;
    this.write({ file: null, dirty: false, selection: null, diagnostics: [] });
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
    } finally {
      try { fs.unlinkSync(temporary); } catch (error) {
        if (!error || error.code !== 'ENOENT') throw error;
      }
    }
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    fs.rmSync(this.directory, { recursive: true, force: true });
  }
}

module.exports = { IdeContextBridge };
