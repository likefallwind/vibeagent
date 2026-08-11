'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { SessionStatusBar, statusWorkspaceRoot } = require('../src/sessionStatusBar');

function testHarness() {
  const root = '/workspace/project';
  const item = {
    visible: false,
    disposed: false,
    show() { this.visible = true; },
    hide() { this.visible = false; },
    dispose() { this.disposed = true; },
  };
  const counts = new Map();
  const vscode = {
    StatusBarAlignment: { Left: 1 },
    window: {
      activeTextEditor: null,
      createStatusBarItem(alignment, priority) {
        assert.equal(alignment, 1);
        assert.equal(priority, 100);
        return item;
      },
    },
    workspace: {
      workspaceFolders: [{ uri: { fsPath: root } }],
      getWorkspaceFolder(uri) {
        return uri.fsPath.startsWith(root) ? { uri: { fsPath: root } } : null;
      },
    },
  };
  const terminals = { sessionCount: (value) => counts.get(value) || 0 };
  return { counts, item, root, terminals, vscode };
}

test('shows a bounded workspace session count and start state', () => {
  const { counts, item, root, terminals, vscode } = testHarness();
  const status = new SessionStatusBar(vscode, terminals);

  assert.equal(status.refresh(), root);
  assert.equal(item.command, 'vibeagent.showSession');
  assert.equal(item.name, 'VibeAgent Sessions');
  assert.equal(item.text, '$(sparkle) VibeAgent');
  assert.equal(item.tooltip, 'Start a VibeAgent session for this workspace');
  assert.equal(item.visible, true);

  counts.set(root, 2);
  status.refresh();
  assert.equal(item.text, '$(terminal) VibeAgent 2');
  assert.equal(item.tooltip, 'Show one of 2 open VibeAgent sessions for this workspace');
  assert.equal(item.accessibilityInformation.label, 'VibeAgent, 2 open workspace sessions');
  status.dispose();
  assert.equal(item.disposed, true);
});

test('tracks file workspaces, retains the root for inspector documents, and hides when ambiguous', () => {
  const { item, root, terminals, vscode } = testHarness();
  vscode.workspace.workspaceFolders.push({ uri: { fsPath: '/workspace/other' } });
  const status = new SessionStatusBar(vscode, terminals);
  const fileEditor = { document: { uri: { scheme: 'file', fsPath: `${root}/src/app.py` } } };
  const inspectorEditor = { document: { uri: { scheme: 'untitled' } } };

  assert.equal(status.refresh(), null);
  assert.equal(item.visible, false);
  assert.equal(status.refresh(fileEditor), root);
  assert.equal(status.refresh(inspectorEditor), root);
  vscode.workspace.workspaceFolders = [{ uri: { fsPath: '/workspace/other' } }];
  assert.equal(status.refresh(inspectorEditor), '/workspace/other');
  assert.equal(statusWorkspaceRoot(vscode, null, '/workspace/missing'), '/workspace/other');
});
