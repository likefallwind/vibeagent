'use strict';

const { sessionQuickPickItems } = require('./sessionCatalog');
const { SessionRewindClient } = require('./sessionRewindClient');

class RewindReviewManager {
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.catalog = options.catalog;
    this.client = options.client || new SessionRewindClient(options);
    this.terminals = options.terminals;
    this.reviews = new Map();
  }

  async open(config, root) {
    const session = await this._selectSession(config, root);
    if (!session) return null;
    const point = await this._selectPoint(config, root, session.session);
    if (!point) return null;
    const selectedMode = await this.vscode.window.showQuickPick(rewindModeQuickPickItems(), {
      title: 'Choose VibeAgent Rewind Mode',
      placeHolder: 'Choose what to rewind',
      ignoreFocusOut: true,
    });
    if (!selectedMode) return null;
    const [preview, diff] = await Promise.all([
      this.client.preview(config, root, session.session, point.checkpointId, selectedMode.mode),
      this.client.diff(config, root, point.checkpointId),
    ]);
    const document = await this.vscode.workspace.openTextDocument({
      language: 'markdown',
      content: renderRewindReview(session, point, preview, diff),
    });
    this.reviews.set(document.uri.toString(), {
      root,
      session: session.session,
      sessionName: session.name || session.task || session.session,
      checkpointId: point.checkpointId,
      mode: selectedMode.mode,
    });
    await this.vscode.window.showTextDocument(document, { preview: false });
    return document;
  }

  async executeActive(config) {
    const editor = this.vscode.window.activeTextEditor;
    if (!editor) throw new Error('Open a VibeAgent rewind review before executing it.');
    const review = this.reviews.get(editor.document.uri.toString());
    if (!review) throw new Error('The active editor is not a VibeAgent rewind review.');
    const preview = await this.client.preview(
      config,
      review.root,
      review.session,
      review.checkpointId,
      review.mode,
    );
    const confirmed = await this.vscode.window.showWarningMessage(
      'Rewind this VibeAgent session?',
      { modal: true, detail: rewindConfirmationDetail(review, preview) },
      'Rewind',
    );
    if (confirmed !== 'Rewind') return null;
    const result = await this.client.execute(
      config,
      review.root,
      review.session,
      review.checkpointId,
      review.mode,
    );
    if (result.newSession) {
      this.terminals.resume(
        config,
        review.root,
        result.newSession,
        `Rewind: ${review.sessionName}`,
      );
    } else {
      this.vscode.window.showInformationMessage(`Restored code from checkpoint ${review.checkpointId}.`);
    }
    return result;
  }

  closed(document) {
    if (document && document.uri) this.reviews.delete(document.uri.toString());
  }

  dispose() {
    this.reviews.clear();
  }

  async _selectSession(config, root) {
    const sessions = await this.catalog.list(config, root);
    if (!sessions.length) {
      this.vscode.window.showInformationMessage('No VibeAgent sessions are available in this workspace.');
      return null;
    }
    const selected = await this.vscode.window.showQuickPick(sessionQuickPickItems(sessions), {
      title: 'Review VibeAgent Session Rewind',
      placeHolder: 'Choose a recent workspace session',
      matchOnDescription: true,
      matchOnDetail: true,
      ignoreFocusOut: true,
    });
    if (!selected) return null;
    const session = sessions.find((item) => item.session === selected.session);
    if (!session) throw new Error('The selected VibeAgent session is no longer available.');
    return session;
  }

  async _selectPoint(config, root, sessionId) {
    const report = await this.client.points(config, root, sessionId);
    if (!report.points.length) {
      this.vscode.window.showInformationMessage('This VibeAgent session has no rewind checkpoints.');
      return null;
    }
    const selected = await this.vscode.window.showQuickPick(rewindPointQuickPickItems(report.points), {
      title: 'Choose VibeAgent Rewind Checkpoint',
      placeHolder: report.truncated
        ? 'Choose from the newest 100 checkpoints in this session'
        : 'Choose a checkpoint from this session',
      matchOnDescription: true,
      matchOnDetail: true,
      ignoreFocusOut: true,
    });
    if (!selected) return null;
    const point = report.points.find((item) => item.checkpointId === selected.checkpointId);
    if (!point) throw new Error('The selected VibeAgent checkpoint is no longer available.');
    return point;
  }
}

function renderRewindReview(session, point, preview, diff) {
  const impact = preview.codeWillChange && preview.conversationWillBranch
    ? 'Code and conversation'
    : preview.codeWillChange ? 'Code only' : 'Conversation only';
  const lines = [
    '# VibeAgent Rewind Review',
    '',
    `Session: \`${session.session}\``,
    `Checkpoint: \`${point.checkpointId}\``,
    `Label: ${point.label || '(none)'}`,
    `Created: ${point.createdAt || '(unknown)'}`,
    `Mode: ${preview.mode}`,
    `Impact: ${impact}`,
    `Conversation event boundary: ${preview.eventLine}`,
    '',
    '## Staged Patch',
    '',
    '```diff',
    diff.stagedPatch || '(no staged changes)',
    '```',
  ];
  if (diff.stagedTruncated) lines.push('_Staged patch truncated._');
  lines.push('', '## Unstaged Patch', '', '```diff', diff.unstagedPatch || '(no unstaged changes)', '```');
  if (diff.unstagedTruncated) lines.push('_Unstaged patch truncated._');
  return `${lines.join('\n')}\n`;
}

function rewindConfirmationDetail(review, preview) {
  const impacts = [];
  if (preview.codeWillChange) impacts.push('replace the current tracked and saved untracked worktree state');
  if (preview.conversationWillBranch) impacts.push('create a new conversation session at the recorded event boundary');
  return [
    `Session: ${review.session}`,
    `Checkpoint: ${review.checkpointId}`,
    `Mode: ${review.mode}`,
    `This will ${impacts.join(' and ')}.`,
  ].join('\n');
}

function rewindPointQuickPickItems(points) {
  return points.map((point) => ({
    label: point.label || point.checkpointId,
    description: point.createdAt || 'unknown time',
    detail: `${point.checkpointId} | event line ${point.eventLine}`,
    checkpointId: point.checkpointId,
  }));
}

function rewindModeQuickPickItems() {
  return [
    { label: 'Code and conversation', description: 'Restore files and create a conversation branch', mode: 'both' },
    { label: 'Code only', description: 'Restore files and keep the current conversation', mode: 'code' },
    { label: 'Conversation only', description: 'Create a conversation branch without changing files', mode: 'conversation' },
  ];
}

module.exports = {
  RewindReviewManager,
  renderRewindReview,
  rewindConfirmationDetail,
  rewindModeQuickPickItems,
  rewindPointQuickPickItems,
};
