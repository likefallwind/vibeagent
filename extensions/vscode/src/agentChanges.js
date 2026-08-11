'use strict';

const crypto = require('node:crypto');
const path = require('node:path');

const MAX_TRACKED_DOCUMENTS = 100;

class AgentChangeContentProvider {
  constructor(vscode) {
    this.vscode = vscode;
    this.entries = new Map();
    this.order = [];
    this.changeEmitter = new vscode.EventEmitter();
    this.onDidChange = this.changeEmitter.event;
  }

  track(filePath, side, content) {
    const name = path.basename(filePath) || 'change';
    const id = crypto.randomUUID();
    const uri = this.vscode.Uri.parse(
      `vibeagent-change:/${encodeURIComponent(name)}?id=${id}&side=${encodeURIComponent(side)}`,
    );
    const key = uri.toString();
    this.entries.set(key, content);
    this.order.push(key);
    while (this.order.length > MAX_TRACKED_DOCUMENTS) {
      this.entries.delete(this.order.shift());
    }
    return uri;
  }

  provideTextDocumentContent(uri) {
    const content = this.entries.get(uri.toString());
    if (content === undefined) throw new Error('The VibeAgent change document is no longer available.');
    return content;
  }

  dispose() {
    this.entries.clear();
    this.order = [];
    this.changeEmitter.dispose();
  }
}

module.exports = { AgentChangeContentProvider, MAX_TRACKED_DOCUMENTS };
