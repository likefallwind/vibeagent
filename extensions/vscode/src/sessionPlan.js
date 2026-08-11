'use strict';

const MAX_PROMPT_CHARS = 12_000;
const { LocalJsonClient } = require('./localCli');
const { requireSessionId } = require('./sessionCatalog');

const MAX_PLAN_ITEMS = 100;
const MAX_PLAN_STEP_CHARS = 4_000;
const MAX_REVIEW_CHARS = 10_000;
const PLAN_STATUSES = new Set(['pending', 'in_progress', 'completed']);

class SessionPlanClient {
  constructor(options = {}) {
    this.client = options.client || new LocalJsonClient(options);
  }

  async get(config, workspaceRoot, sessionId) {
    const selected = requireSessionId(sessionId);
    const { code, payload } = await this.client.run(
      config,
      workspaceRoot,
      ['--plan', selected],
    );
    const plan = parseSessionPlan(payload, selected);
    if (code !== 0 || !plan.exists || !plan.ok) {
      throw new Error(plan.message || `VibeAgent could not read plan for session ${selected}.`);
    }
    return plan;
  }
}

class PlanReviewManager {
  constructor(vscode, options = {}) {
    this.vscode = vscode;
    this.client = options.client || new SessionPlanClient(options);
    this.reviews = new Map();
  }

  async open(config, root, session) {
    const plan = await this.client.get(config, root, session.session);
    const document = await this.vscode.workspace.openTextDocument({
      language: 'markdown',
      content: renderPlanDocument(plan),
    });
    this.reviews.set(document.uri.toString(), {
      root,
      session: plan.session,
      name: session.name || session.task || plan.task || plan.session,
    });
    await this.vscode.window.showTextDocument(document, { preview: false });
    return document;
  }

  activeExecution() {
    const editor = this.vscode.window.activeTextEditor;
    if (!editor) throw new Error('Open a VibeAgent plan review before executing it.');
    const review = this.reviews.get(editor.document.uri.toString());
    if (!review) throw new Error('The active editor is not a VibeAgent plan review.');
    return {
      ...review,
      prompt: buildReviewedPlanPrompt(editor.document.getText()),
    };
  }

  closed(document) {
    if (document && document.uri) this.reviews.delete(document.uri.toString());
  }

  dispose() {
    this.reviews.clear();
  }
}

function parseSessionPlan(payload, expectedSession) {
  const report = payload && typeof payload === 'object' ? payload.sessionPlan : null;
  if (!report || typeof report !== 'object') {
    throw new Error('VibeAgent returned an invalid session plan.');
  }
  const session = requireSessionId(report.session);
  if (expectedSession && session !== expectedSession) {
    throw new Error('VibeAgent returned a plan for the wrong session.');
  }
  if (typeof report.exists !== 'boolean' || typeof report.ok !== 'boolean') {
    throw new Error('VibeAgent returned an invalid session plan status.');
  }
  const status = boundedInline(report.status, 40, 'plan status');
  const message = optionalText(report.message, 1_000, 'plan message');
  const task = optionalText(report.task, MAX_REVIEW_CHARS, 'plan task');
  const sourceItems = report.items === undefined ? [] : report.items;
  if (!Array.isArray(sourceItems) || sourceItems.length > MAX_PLAN_ITEMS) {
    throw new Error('VibeAgent returned an invalid session plan item list.');
  }
  const items = sourceItems.map((item) => validatePlanItem(item));
  const plan = { session, exists: report.exists, ok: report.ok, status, message, task, items };
  if (renderPlanDocument(plan).length > MAX_REVIEW_CHARS) {
    throw new Error(`VibeAgent session plan exceeds ${MAX_REVIEW_CHARS} rendered characters.`);
  }
  return plan;
}

function validatePlanItem(item) {
  if (!item || typeof item !== 'object' || !PLAN_STATUSES.has(item.status)) {
    throw new Error('VibeAgent returned an invalid session plan item.');
  }
  return {
    status: item.status,
    step: boundedText(item.step, MAX_PLAN_STEP_CHARS, 'plan step'),
    activeForm: optionalText(item.activeForm, 1_000, 'plan active form'),
  };
}

function renderPlanDocument(plan) {
  const lines = ['# VibeAgent Plan', '', `Session: \`${plan.session}\``];
  if (plan.task) lines.push('', '## Task', '', plan.task);
  lines.push('', '## Steps', '');
  if (!plan.items.length) {
    lines.push('_No recorded plan items._');
  } else {
    for (const item of plan.items) {
      const checked = item.status === 'completed' ? 'x' : ' ';
      lines.push(`- [${checked}] ${item.status}: ${item.step}`);
    }
  }
  return `${lines.join('\n')}\n`;
}

function buildReviewedPlanPrompt(value) {
  const review = boundedText(value, MAX_REVIEW_CHARS, 'Reviewed plan');
  const prompt = [
    'Implement the reviewed plan below in this resumed session.',
    'Re-inspect the current repository state before editing, keep plan status current, run appropriate verification, and commit the completed stage.',
    '',
    review,
  ].join('\n');
  if (prompt.length > MAX_PROMPT_CHARS) {
    throw new Error(`Reviewed plan must leave room within the ${MAX_PROMPT_CHARS}-character task limit.`);
  }
  return prompt;
}

function optionalText(value, maximum, label) {
  if (value === null || value === undefined || value === '') return null;
  return boundedText(value, maximum, label);
}

function boundedText(value, maximum, label) {
  if (typeof value !== 'string' || !value.trim() || value.length > maximum || hasUnsafeControl(value)) {
    throw new Error(`VibeAgent returned invalid ${label}.`);
  }
  return value.replace(/\r\n?/g, '\n').trim();
}

function boundedInline(value, maximum, label) {
  const text = boundedText(value, maximum, label);
  if (text.includes('\n')) throw new Error(`VibeAgent returned invalid ${label}.`);
  return text;
}

function hasUnsafeControl(value) {
  return Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return (code < 32 && ![9, 10, 13].includes(code)) || code === 127;
  });
}

module.exports = {
  MAX_PLAN_ITEMS,
  MAX_REVIEW_CHARS,
  PlanReviewManager,
  SessionPlanClient,
  buildReviewedPlanPrompt,
  parseSessionPlan,
  renderPlanDocument,
};
