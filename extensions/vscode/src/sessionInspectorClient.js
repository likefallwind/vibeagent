'use strict';

const { LocalJsonClient } = require('./localCli');
const { requireSessionId } = require('./sessionCatalog');

const MAX_INSPECT_PLAN_ITEMS = 20;
const MAX_INSPECT_TASKS = 50;
const MAX_SESSION_TASKS = 100;
const MAX_INSPECT_FILES = 100;
const MAX_INSPECT_EVENTS = 80;
const MAX_INSPECT_CHECKS = 50;
const SESSION_STATUSES = new Set(['completed', 'failed', 'blocked', 'incomplete']);
const REPORT_STATUSES = new Set([...SESSION_STATUSES, 'missing', 'invalid']);
const PLAN_ITEM_STATUSES = new Set(['pending', 'in_progress', 'completed']);

class SessionInspectorClient {
  constructor(options = {}) {
    this.client = options.client || new LocalJsonClient(options);
  }

  async get(config, root, sessionId) {
    const session = requireSessionId(sessionId);
    const result = await this.client.run(config, root, ['--session-inspect', session]);
    const report = parseSessionInspector(result.payload, session);
    if (result.code !== 0 || !report.ok || !report.exists) {
      throw new Error(report.message || `VibeAgent could not inspect session ${session}.`);
    }
    return report;
  }
}

function parseSessionInspector(payload, expectedSession) {
  const report = requireObject(payload, 'sessionInspect', 'session inspector report');
  const session = requireSessionId(report.session);
  if (session !== expectedSession) throw new Error('VibeAgent returned an inspector report for the wrong session.');
  const ok = requireBoolean(report.ok, 'session inspector status');
  const exists = requireBoolean(report.exists, 'session inspector existence');
  const status = requireAllowedStatus(report.status, REPORT_STATUSES, 'session status');
  const message = optionalText(report.message, 2_000, 'session inspector message');
  if (!ok || !exists) {
    return {
      session,
      ok,
      exists,
      status,
      overview: null,
      plan: null,
      tasks: null,
      transcript: null,
      files: null,
      verification: null,
      message,
    };
  }
  requireAllowedStatus(status, SESSION_STATUSES, 'session status');
  return {
    session,
    ok,
    exists,
    status,
    overview: parseOverview(report.overview, status),
    plan: parsePlan(report.plan),
    tasks: parseTasks(report.tasks, session),
    transcript: parseTranscript(report.transcript, session),
    files: parseFiles(report.files, session),
    verification: parseVerification(report.verification, session),
    message,
  };
}

function parseOverview(value, expectedStatus) {
  const overview = requireValueObject(value, 'session overview');
  const status = requireStatus(overview.status, 'overview status');
  if (status !== expectedStatus) throw new Error('VibeAgent returned inconsistent session status.');
  const events = requireValueObject(overview.events, 'session event summary');
  const approvals = requireValueObject(overview.approvals, 'session approval summary');
  const tokens = requireValueObject(overview.tokens, 'session token summary');
  const completion = requireValueObject(overview.completion, 'session completion summary');
  const finalReview = requireValueObject(overview.finalReview, 'session final review summary');
  const checkpoints = requireValueObject(overview.checkpoints, 'session checkpoint summary');
  return {
    status,
    task: optionalText(overview.task, 4_000, 'session task'),
    finalMessage: optionalText(overview.finalMessage, 4_000, 'session final message'),
    events: {
      total: requireCount(events.total, 'session event count'),
      malformed: requireCount(events.malformed, 'malformed event count'),
      iterations: requireCount(events.iterations, 'session iteration count'),
    },
    toolCalls: requireCount(overview.toolCalls, 'session tool call count'),
    approvals: parseCounts(approvals, ['requested', 'approved', 'denied'], 'approval'),
    tokens: parseCounts(tokens, ['input', 'output', 'total'], 'token'),
    completion: {
      ready: optionalBoolean(completion.ready, 'completion readiness'),
      blockers: requireCount(completion.blockers, 'completion blocker count'),
      warnings: requireCount(completion.warnings, 'completion warning count'),
      blockedAttempts: requireCount(completion.blockedAttempts, 'blocked completion count'),
    },
    finalReview: {
      seen: requireBoolean(finalReview.seen, 'final review seen flag'),
      ready: optionalBoolean(finalReview.ready, 'final review readiness'),
      blockingIssues: requireCount(finalReview.blockingIssues, 'final review blocker count'),
      warnings: requireCount(finalReview.warnings, 'final review warning count'),
      files: requireCount(finalReview.files, 'final review file count'),
    },
    checkpoints: {
      created: requireCount(checkpoints.created, 'checkpoint count'),
      latestId: optionalInline(checkpoints.latestId, 255, 'latest checkpoint ID'),
    },
  };
}

function parsePlan(value) {
  const plan = requireValueObject(value, 'session plan');
  const items = requireBoundedArray(plan.items, MAX_INSPECT_PLAN_ITEMS, 'session plan items')
    .map((item) => {
      const entry = requireValueObject(item, 'session plan item');
      if (!PLAN_ITEM_STATUSES.has(entry.status)) throw new Error('VibeAgent returned an invalid plan item status.');
      return {
        status: entry.status,
        step: requireText(entry.step, 2_000, 'session plan step'),
        activeForm: optionalText(entry.activeForm, 2_000, 'session plan active form'),
      };
    });
  const counts = parseCollectionCounts(plan, items.length, 'session plan', false);
  return { status: requireStatus(plan.status, 'plan status'), ...counts, items };
}

function parseTasks(value, expectedSession) {
  const report = requireValueObject(value, 'session task graph');
  requireReportIdentity(report, expectedSession, 'session task graph');
  const status = requireAllowedStatus(report.status, new Set(['ready', 'empty']), 'session task graph status');
  const counts = requireValueObject(report.counts, 'session task counts');
  const parsedCounts = parseCounts(counts, ['pending', 'inProgress', 'completed', 'blocked'], 'session task');
  const collection = requireValueObject(report.tasks, 'session task collection');
  const items = requireBoundedArray(collection.items, MAX_INSPECT_TASKS, 'session task items')
    .map((item) => {
      const entry = requireValueObject(item, 'session task item');
      const id = requireInline(entry.id, 64, 'session task ID');
      if (!/^\d+$/.test(id)) throw new Error('VibeAgent returned an invalid session task ID.');
      if (!PLAN_ITEM_STATUSES.has(entry.status)) throw new Error('VibeAgent returned an invalid session task status.');
      return {
        id,
        subject: requireInline(entry.subject, 500, 'session task subject'),
        description: requireInline(entry.description, 500, 'session task description'),
        status: entry.status,
        activeForm: optionalInline(entry.activeForm, 500, 'session task active form'),
        owner: optionalInline(entry.owner, 200, 'session task owner'),
        blocks: parseTaskIds(entry.blocks, 'session task blocks'),
        blockedBy: parseTaskIds(entry.blockedBy, 'session task blockers'),
        blocked: requireBoolean(entry.blocked, 'session task blocked flag'),
      };
    });
  if (new Set(items.map((item) => item.id)).size !== items.length) {
    throw new Error('VibeAgent returned duplicate session task IDs.');
  }
  const taskCounts = parseCollectionCounts(collection, items.length, 'session tasks');
  if (taskCounts.total > MAX_SESSION_TASKS) throw new Error('VibeAgent returned too many session tasks.');
  if (parsedCounts.pending + parsedCounts.inProgress + parsedCounts.completed !== taskCounts.total) {
    throw new Error('VibeAgent returned inconsistent session task status counts.');
  }
  if (parsedCounts.blocked > taskCounts.total || (status === 'empty') !== (taskCounts.total === 0)) {
    throw new Error('VibeAgent returned inconsistent session task summary.');
  }
  return { status, counts: parsedCounts, ...taskCounts, items };
}

function parseTaskIds(value, label) {
  const items = parseInlineArray(value, MAX_SESSION_TASKS, 64, label);
  if (items.some((item) => !/^\d+$/.test(item))) throw new Error(`VibeAgent returned invalid ${label}.`);
  return items;
}
function parseTranscript(value, expectedSession) {
  const report = requireValueObject(value, 'session transcript');
  requireReportIdentity(report, expectedSession, 'session transcript');
  const events = requireValueObject(report.events, 'session timeline');
  const items = requireBoundedArray(events.items, MAX_INSPECT_EVENTS, 'session timeline items')
    .map((item) => {
      const entry = requireValueObject(item, 'session timeline item');
      return {
        lineNumber: requirePositiveInteger(entry.lineNumber, 'session event line'),
        type: requireInline(entry.type, 120, 'session event type'),
        malformed: requireBoolean(entry.malformed, 'malformed session event flag'),
        summary: requireText(entry.summary, 1_200, 'session event summary'),
      };
    });
  const counts = parseCollectionCounts(events, items.length, 'session timeline');
  return {
    ...counts,
    malformed: requireCount(events.malformed, 'malformed timeline count'),
    items,
  };
}

function parseFiles(value, expectedSession) {
  const report = requireValueObject(value, 'session files');
  requireReportIdentity(report, expectedSession, 'session files');
  const files = requireValueObject(report.files, 'session file collection');
  const items = requireBoundedArray(files.items, MAX_INSPECT_FILES, 'session file items')
    .map((item) => {
      const entry = requireValueObject(item, 'session file item');
      const tools = parseInlineArray(entry.tools, 20, 120, 'session file tools');
      const uses = parseInlineArray(entry.uses, 20, 120, 'session file uses');
      const lines = requireBoundedArray(entry.lines, 20, 'session file lines')
        .map((line) => requirePositiveInteger(line, 'session file event line'));
      const toolCount = requirePositiveInteger(entry.toolCount, 'session file tool count');
      const useCount = requirePositiveInteger(entry.useCount, 'session file use count');
      const count = requirePositiveInteger(entry.count, 'session file reference count');
      const toolsTruncated = requireBoolean(entry.toolsTruncated, 'session file tool truncation flag');
      const usesTruncated = requireBoolean(entry.usesTruncated, 'session file use truncation flag');
      const linesTruncated = requireBoolean(entry.linesTruncated, 'session file line truncation flag');
      if (
        toolCount < tools.length || toolsTruncated !== (toolCount > tools.length)
        || useCount < uses.length || usesTruncated !== (useCount > uses.length)
        || count < lines.length || linesTruncated !== (count > lines.length)
      ) throw new Error('VibeAgent returned inconsistent session file detail counts.');
      return {
        path: requireInline(entry.path, 4_000, 'session file path'),
        tools, toolCount, toolsTruncated,
        uses, useCount, usesTruncated,
        lines, count, linesTruncated,
      };
    });
  if (new Set(items.map((item) => item.path)).size !== items.length) {
    throw new Error('VibeAgent returned duplicate session file paths.');
  }
  return { ...parseCollectionCounts(files, items.length, 'session files'), items };
}

function parseVerification(value, expectedSession) {
  const report = requireValueObject(value, 'session verification');
  requireReportIdentity(report, expectedSession, 'session verification', false);
  const ready = requireBoolean(report.ready, 'session verification readiness');
  const ok = requireBoolean(report.ok, 'session verification status');
  if (ready !== ok) throw new Error('VibeAgent returned inconsistent verification readiness.');
  const verified = parseStringGroup(report.verified, 'verified checks');
  const pending = parseStringGroup(report.pending, 'pending checks');
  const failed = parseStringGroup(report.failed, 'failed checks');
  const truncated = requireBoolean(report.truncated, 'verification truncation flag');
  if (truncated !== (verified.truncated || pending.truncated || failed.truncated)) {
    throw new Error('VibeAgent returned inconsistent verification truncation state.');
  }
  return { ready, ok, truncated, verified, pending, failed };
}

function parseStringGroup(value, label) {
  const group = requireValueObject(value, label);
  const items = requireBoundedArray(group.items, MAX_INSPECT_CHECKS, label)
    .map((item) => requireText(item, 600, label));
  return { ...parseCollectionCounts(group, items.length, label, false), items };
}

function parseCollectionCounts(value, itemCount, label, hasOmitted = true) {
  const total = requireCount(value.total, `${label} total`);
  const shown = requireCount(value.shown, `${label} shown count`);
  const truncated = requireBoolean(value.truncated, `${label} truncation flag`);
  if (shown !== itemCount || total < shown || truncated !== (total > shown)) {
    throw new Error(`VibeAgent returned inconsistent ${label} counts.`);
  }
  const omitted = hasOmitted ? requireCount(value.omitted, `${label} omitted count`) : total - shown;
  if (omitted !== total - shown) throw new Error(`VibeAgent returned inconsistent ${label} omission count.`);
  return { total, shown, omitted, truncated };
}

function requireReportIdentity(report, expectedSession, label, requireOk = true) {
  const session = requireSessionId(report.session);
  if (session !== expectedSession) throw new Error(`VibeAgent returned ${label} for the wrong session.`);
  if (!requireBoolean(report.exists, `${label} existence`)) throw new Error(`VibeAgent returned missing ${label}.`);
  const ok = requireBoolean(report.ok, `${label} status`);
  if (requireOk && !ok) throw new Error(`VibeAgent returned unavailable ${label}.`);
}

function requireObject(payload, key, label) {
  const value = payload && typeof payload === 'object' ? payload[key] : null;
  return requireValueObject(value, label);
}

function requireValueObject(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`VibeAgent returned an invalid ${label}.`);
  }
  return value;
}

function requireBoundedArray(value, maximum, label) {
  if (!Array.isArray(value) || value.length > maximum) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function parseInlineArray(value, maximumItems, maximumText, label) {
  const items = requireBoundedArray(value, maximumItems, label)
    .map((item) => requireInline(item, maximumText, label));
  if (new Set(items).size !== items.length) throw new Error(`VibeAgent returned duplicate ${label}.`);
  return items;
}

function parseCounts(value, keys, label) {
  return Object.fromEntries(keys.map((key) => [key, requireCount(value[key], `${label} ${key} count`)]));
}

function requireStatus(value, label) {
  return requireAllowedStatus(value, SESSION_STATUSES, label);
}

function requireAllowedStatus(value, statuses, label) {
  if (typeof value !== 'string' || !statuses.has(value)) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function requireBoolean(value, label) {
  if (typeof value !== 'boolean') throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function optionalBoolean(value, label) {
  if (value === null || value === undefined) return null;
  return requireBoolean(value, label);
}

function requireCount(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function requirePositiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value < 1) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function optionalText(value, maximum, label) {
  if (value === null || value === undefined || value === '') return null;
  return requireText(value, maximum, label);
}

function requireText(value, maximum, label) {
  if (typeof value !== 'string' || !value.trim() || value.length > maximum || hasUnsafeControl(value)) {
    throw new Error(`VibeAgent returned an invalid ${label}.`);
  }
  return value.replace(/\r\n?/g, '\n').trim();
}

function optionalInline(value, maximum, label) {
  if (value === null || value === undefined || value === '') return null;
  return requireInline(value, maximum, label);
}

function requireInline(value, maximum, label) {
  const text = requireText(value, maximum, label);
  if (text.includes('\n') || text.includes('\r')) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return text;
}

function hasUnsafeControl(value) {
  return Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return (code < 32 && ![9, 10, 13].includes(code)) || code === 127;
  });
}

module.exports = {
  MAX_INSPECT_CHECKS,
  MAX_INSPECT_EVENTS,
  MAX_INSPECT_FILES,
  MAX_INSPECT_PLAN_ITEMS,
  MAX_INSPECT_TASKS,
  SessionInspectorClient,
  parseSessionInspector,
};
