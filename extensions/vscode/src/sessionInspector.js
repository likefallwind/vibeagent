'use strict';

const { sessionQuickPickItems } = require('./sessionCatalog');
const { SessionInspectorClient } = require('./sessionInspectorClient');

const MAX_INSPECTOR_DOCUMENT_CHARS = 250_000;
const MAX_VERIFICATION_RUNS = 10;

class SessionInspectorManager {
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.catalog = options.catalog;
    this.client = options.client || new SessionInspectorClient(options);
    this.terminals = options.terminals;
    this.documents = new Map();
  }

  async open(config, root) {
    const sessions = await this.catalog.list(config, root);
    if (!sessions.length) {
      this.vscode.window.showInformationMessage('No VibeAgent sessions are available in this workspace.');
      return null;
    }
    const selected = await this.vscode.window.showQuickPick(sessionQuickPickItems(sessions), {
      title: 'Inspect VibeAgent Session',
      placeHolder: 'Choose a recent workspace session',
      matchOnDescription: true,
      matchOnDetail: true,
      ignoreFocusOut: true,
    });
    if (!selected) return null;
    const session = sessions.find((item) => item.session === selected.session);
    if (!session) throw new Error('The selected VibeAgent session is no longer available.');
    const report = await this.client.get(config, root, session.session);
    const content = renderSessionInspector(report);
    if (content.length > MAX_INSPECTOR_DOCUMENT_CHARS) {
      throw new Error(`VibeAgent session inspector exceeds ${MAX_INSPECTOR_DOCUMENT_CHARS} rendered characters.`);
    }
    const document = await this.vscode.workspace.openTextDocument({ language: 'markdown', content });
    this.documents.set(document.uri.toString(), {
      root,
      session: report.session,
      name: session.name || session.task || report.overview.task || report.session,
    });
    await this.vscode.window.showTextDocument(document, { preview: false });
    return document;
  }

  resumeActive(config) {
    const inspected = this._activeInspection('resuming it');
    return this.terminals.resume(config, inspected.root, inspected.session, inspected.name);
  }

  async runVerificationActive(config) {
    const inspected = this._activeInspection('running its verification');
    const report = await this.client.get(config, inspected.root, inspected.session);
    const selection = verificationRunSelection(report.verification);
    if (!selection.total) {
      this.vscode.window.showInformationMessage('This VibeAgent session has no failed or pending verification checks.');
      return null;
    }
    const confirmed = await this.vscode.window.showWarningMessage(
      'Run recorded verification checks?',
      { modal: true, detail: verificationConfirmationDetail(inspected, selection) },
      'Run Checks',
    );
    if (confirmed !== 'Run Checks') return null;
    return this.terminals.runVerification(
      config,
      inspected.root,
      inspected.session,
      inspected.name,
    );
  }

  closed(document) {
    if (document && document.uri) this.documents.delete(document.uri.toString());
  }

  dispose() {
    this.documents.clear();
  }

  _activeInspection(action) {
    const editor = this.vscode.window.activeTextEditor;
    if (!editor) throw new Error(`Open a VibeAgent session inspector before ${action}.`);
    const inspected = this.documents.get(editor.document.uri.toString());
    if (!inspected) throw new Error('The active editor is not a VibeAgent session inspector.');
    return inspected;
  }
}

function verificationRunSelection(verification) {
  const failed = verification.failed;
  const pending = verification.pending;
  return {
    failed: failed.total,
    pending: pending.total,
    total: Math.min(MAX_VERIFICATION_RUNS, failed.total + pending.total),
    commands: [...failed.items, ...pending.items].slice(0, MAX_VERIFICATION_RUNS),
  };
}

function verificationConfirmationDetail(inspected, selection) {
  const lines = [
    `Session: ${inspected.session}`,
    `Failed checks: ${selection.failed}`,
    `Pending checks: ${selection.pending}`,
    `The CLI will re-read, de-duplicate, and run at most ${selection.total} check(s) in a visible terminal.`,
  ];
  if (selection.commands.length) lines.push('', ...selection.commands.map((command) => `- ${command}`));
  return lines.join('\n');
}

function renderSessionInspector(report) {
  const { overview, plan, verification, files, transcript } = report;
  const lines = [
    '# VibeAgent Session Inspector',
    '',
    `Session: ${inlineCode(report.session)}`,
    `Status: ${escapeMarkdown(report.status)}`,
    `Events: ${overview.events.total} total, ${overview.events.malformed} malformed`,
    `Iterations: ${overview.events.iterations}`,
    `Tool calls: ${overview.toolCalls}`,
    `Approvals: ${overview.approvals.approved} approved, ${overview.approvals.denied} denied, ${overview.approvals.requested} requested`,
    `Tokens: ${overview.tokens.input} input, ${overview.tokens.output} output, ${overview.tokens.total} total`,
    '',
    '## Task',
    '',
    ...indentedText(overview.task || '(no recorded task)'),
    '',
    '## Completion',
    '',
    `Ready: ${booleanLabel(overview.completion.ready)}`,
    `Blockers: ${overview.completion.blockers}`,
    `Warnings: ${overview.completion.warnings}`,
    `Blocked attempts: ${overview.completion.blockedAttempts}`,
    `Final review: ${booleanLabel(overview.finalReview.ready)} (${overview.finalReview.blockingIssues} blocking, ${overview.finalReview.warnings} warnings)`,
  ];
  if (overview.finalMessage) lines.push('', '### Final Message', '', ...indentedText(overview.finalMessage));
  lines.push('', '## Plan', '');
  if (!plan.items.length) {
    lines.push('_No recorded plan items._');
  } else {
    for (const item of plan.items) {
      const checked = item.status === 'completed' ? 'x' : ' ';
      lines.push(`- [${checked}] ${escapeMarkdown(item.status)}: ${escapeMarkdown(item.step)}`);
    }
    if (plan.truncated) lines.push(`- ${plan.total - plan.shown} older plan item(s) omitted`);
  }
  appendVerification(lines, verification);
  appendFiles(lines, files);
  appendTimeline(lines, transcript);
  return `${lines.join('\n')}\n`;
}

function appendVerification(lines, verification) {
  lines.push('', '## Verification', '', `Ready: ${verification.ready ? 'yes' : 'no'}`);
  for (const [label, group] of [
    ['Verified', verification.verified],
    ['Pending', verification.pending],
    ['Failed', verification.failed],
  ]) {
    lines.push('', `### ${label} (${group.total})`, '');
    if (!group.items.length) lines.push('_None._');
    else group.items.forEach((item) => lines.push(...indentedText(item)));
    if (group.truncated) lines.push(`${group.total - group.shown} check(s) omitted.`);
  }
}

function appendFiles(lines, files) {
  lines.push('', `## Files (${files.total})`, '');
  if (!files.items.length) {
    lines.push('_No recorded file references._');
    return;
  }
  for (const item of files.items) {
    const uses = item.uses.length ? item.uses.join(', ') : 'unknown use';
    lines.push(`- ${inlineCode(item.path)}: ${escapeMarkdown(uses)} (${item.count} reference(s))`);
  }
  if (files.truncated) lines.push(`- ${files.omitted} file(s) omitted`);
}

function appendTimeline(lines, transcript) {
  lines.push('', `## Timeline (${transcript.shown}/${transcript.total})`, '');
  if (transcript.omitted) lines.push(`${transcript.omitted} older event(s) omitted.`, '');
  if (!transcript.items.length) {
    lines.push('_No recorded events._');
    return;
  }
  transcript.items.forEach((item) => lines.push(...indentedText(item.summary)));
}

function indentedText(value) {
  return String(value).replace(/\r\n?/g, '\n').split('\n').map((line) => `    ${line || ' '}`);
}

function inlineCode(value) {
  return `\`${String(value).replace(/`/g, "'")}\``;
}

function escapeMarkdown(value) {
  return String(value).replace(/([\\`*_{}\[\]()<>#+.!|])/g, '\\$1');
}

function booleanLabel(value) {
  return value === true ? 'yes' : value === false ? 'no' : 'unknown';
}

module.exports = {
  MAX_INSPECTOR_DOCUMENT_CHARS,
  MAX_VERIFICATION_RUNS,
  SessionInspectorManager,
  renderSessionInspector,
  verificationConfirmationDetail,
  verificationRunSelection,
};
