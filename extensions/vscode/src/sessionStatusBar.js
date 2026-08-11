'use strict';

const STATUS_BAR_PRIORITY = 100;

class SessionStatusBar {
  constructor(vscode, terminals) {
    this.vscode = vscode;
    this.terminals = terminals;
    this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, STATUS_BAR_PRIORITY);
    this.item.command = 'vibeagent.showSession';
    this.item.name = 'VibeAgent Sessions';
  }

  refresh(editor = this.vscode.window.activeTextEditor) {
    const root = statusWorkspaceRoot(this.vscode, editor, this.root);
    this.root = root;
    if (!root) {
      this.item.hide();
      return null;
    }
    const count = this.terminals.sessionCount(root);
    if (count) {
      this.item.text = `$(terminal) VibeAgent ${count}`;
      this.item.tooltip = count === 1
        ? 'Show the open VibeAgent session for this workspace'
        : `Show one of ${count} open VibeAgent sessions for this workspace`;
      this.item.accessibilityInformation = {
        label: `VibeAgent, ${count} open workspace ${count === 1 ? 'session' : 'sessions'}`,
      };
    } else {
      this.item.text = '$(sparkle) VibeAgent';
      this.item.tooltip = 'Start a VibeAgent session for this workspace';
      this.item.accessibilityInformation = { label: 'VibeAgent, no open workspace sessions' };
    }
    this.item.show();
    return root;
  }

  dispose() {
    this.item.dispose();
  }
}

function statusWorkspaceRoot(vscode, editor, previousRoot = null) {
  if (editor && editor.document && editor.document.uri && editor.document.uri.scheme === 'file') {
    const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
    if (folder) return folder.uri.fsPath;
  }
  const folders = vscode.workspace.workspaceFolders || [];
  if (previousRoot && folders.some((folder) => folder.uri.fsPath === previousRoot)) return previousRoot;
  return folders.length === 1 ? folders[0].uri.fsPath : null;
}

module.exports = { SessionStatusBar, STATUS_BAR_PRIORITY, statusWorkspaceRoot };
