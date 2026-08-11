'use strict';

const {
  LOCAL_CLI_TIMEOUT_MS,
  MAX_JSON_BYTES,
  LocalJsonClient,
  parseLocalEnvelope,
} = require('./localCli');

const MAX_CATALOG_BYTES = MAX_JSON_BYTES;
const MAX_CATALOG_ITEMS = 100;
const CATALOG_TIMEOUT_MS = LOCAL_CLI_TIMEOUT_MS;

class SessionCatalog {
  constructor(options = {}) {
    this.client = options.client || new LocalJsonClient(options);
  }

  async list(config, workspaceRoot) {
    const { code, payload } = await this.client.run(config, workspaceRoot, ['--sessions']);
    const sessions = parseSessionCatalog(payload);
    const emptyResult = code === 1 && sessions.length === 0;
    if (code !== 0 && !emptyResult) {
      throw new Error(`VibeAgent session catalog exited with status ${code}.`);
    }
    return sessions;
  }
}

function parseSessionCatalog(raw) {
  let payload;
  try {
    payload = Buffer.isBuffer(raw) || typeof raw === 'string' ? parseLocalEnvelope(raw) : raw;
  } catch (_error) {
    throw new Error('VibeAgent returned an invalid session catalog.');
  }
  const report = payload && typeof payload === 'object' ? payload.sessions : null;
  const collection = report && typeof report === 'object' ? report.sessions : null;
  const items = collection && typeof collection === 'object' ? collection.items : null;
  if (
    !payload
    || typeof payload !== 'object'
    || payload.schemaVersion !== 1
    || payload.kind !== 'local'
    || !report
    || typeof report !== 'object'
    || !Array.isArray(items)
    || items.length > MAX_CATALOG_ITEMS
  ) {
    throw new Error('VibeAgent returned an invalid session catalog.');
  }
  const sessions = items.map(validateSession);
  if (new Set(sessions.map((item) => item.session)).size !== sessions.length) {
    throw new Error('VibeAgent returned duplicate session IDs.');
  }
  return sessions;
}

function validateSession(value) {
  if (!value || typeof value !== 'object') throw new Error('VibeAgent returned an invalid session.');
  const session = requireSessionId(value.session);
  const status = boundedInline(value.status, 40, 'session status');
  const events = requireCount(value.events, 'session event count');
  const malformed = requireCount(value.malformed, 'malformed session count');
  const lastEventTime = optionalInline(value.lastEventTime, 80, 'session timestamp');
  const name = optionalInline(value.name, 200, 'session name');
  const task = optionalInline(value.task, 500, 'session task');
  for (const field of ['completed', 'failed', 'blocked']) {
    if (typeof value[field] !== 'boolean') throw new Error(`VibeAgent returned an invalid ${field} flag.`);
  }
  return {
    session,
    status,
    events,
    malformed,
    lastEventTime,
    name,
    task,
    completed: value.completed,
    failed: value.failed,
    blocked: value.blocked,
  };
}

function requireSessionId(value) {
  if (
    typeof value !== 'string'
    || !value
    || value.length > 255
    || value === '.'
    || value === '..'
    || /[\\/\x00-\x1f\x7f]/.test(value)
  ) {
    throw new Error('VibeAgent returned an invalid session ID.');
  }
  return value;
}

function requireCount(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function optionalInline(value, maximum, label) {
  if (value === null || value === undefined) return null;
  return boundedInline(value, maximum, label);
}

function boundedInline(value, maximum, label) {
  if (typeof value !== 'string' || !value || value.length > maximum || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) {
    throw new Error(`VibeAgent returned an invalid ${label}.`);
  }
  const normalized = value.replace(/\s+/g, ' ').replace(/\$\(/g, '[').trim();
  if (!normalized) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return normalized;
}

function sessionQuickPickItems(sessions) {
  return sessions.map((item) => {
    const sourceLabel = item.name || item.task || item.session;
    const label = sourceLabel.slice(0, 120);
    const taskDetail = item.task && item.task !== sourceLabel ? ` | ${item.task}` : '';
    return {
      label,
      description: `${item.status} | ${item.lastEventTime || 'unknown time'}`,
      detail: `${item.session}${taskDetail}`,
      session: item.session,
    };
  });
}

module.exports = {
  CATALOG_TIMEOUT_MS,
  MAX_CATALOG_BYTES,
  SessionCatalog,
  parseSessionCatalog,
  requireSessionId,
  sessionQuickPickItems,
};
