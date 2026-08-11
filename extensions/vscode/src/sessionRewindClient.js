'use strict';

const { LocalJsonClient } = require('./localCli');
const { requireSessionId } = require('./sessionCatalog');

const MAX_REWIND_POINTS = 100;
const MAX_PATCH_CHARS = 200_000;
const REWIND_MODES = new Set(['both', 'code', 'conversation']);

class SessionRewindClient {
  constructor(options = {}) {
    this.client = options.client || new LocalJsonClient(options);
  }

  async points(config, root, sessionId) {
    const session = requireSessionId(sessionId);
    const result = await this.client.run(config, root, ['--session-rewind-points', session]);
    const report = parseRewindPoints(result.payload, session);
    requireSuccessful(result.code, report.ok, report.message);
    return report;
  }

  async diff(config, root, checkpointId) {
    const checkpoint = requireCheckpointId(checkpointId);
    const result = await this.client.run(config, root, ['--checkpoint-diff', checkpoint]);
    const report = parseCheckpointDiff(result.payload, checkpoint);
    requireSuccessful(result.code, report.ok, report.message);
    return report;
  }

  async preview(config, root, sessionId, checkpointId, mode) {
    const target = normalizeTarget(sessionId, checkpointId, mode);
    const result = await this.client.run(config, root, [
      '--check-session-rewind', target.session, target.checkpoint, target.mode,
    ]);
    const report = parseRewindPreview(
      result.payload,
      target.session,
      target.checkpoint,
      target.mode,
    );
    requireSuccessful(result.code, report.ok && report.canRewind, report.message);
    return report;
  }

  async execute(config, root, sessionId, checkpointId, mode) {
    const target = normalizeTarget(sessionId, checkpointId, mode);
    const result = await this.client.run(config, root, [
      '--session-rewind', target.session, target.checkpoint, target.mode,
    ]);
    const report = parseRewindResult(
      result.payload,
      target.session,
      target.checkpoint,
      target.mode,
    );
    requireSuccessful(result.code, report.ok && report.rewound, report.message);
    return report;
  }
}

function parseRewindPoints(payload, expectedSession) {
  const report = requireReport(payload, 'sessionRewindPoints');
  const session = requireSessionId(report.session);
  if (session !== expectedSession) throw new Error('VibeAgent returned rewind points for the wrong session.');
  if (typeof report.ok !== 'boolean' || typeof report.exists !== 'boolean') {
    throw new Error('VibeAgent returned an invalid rewind point status.');
  }
  if (!Array.isArray(report.points) || report.points.length > MAX_REWIND_POINTS) {
    throw new Error('VibeAgent returned an invalid rewind point list.');
  }
  const points = report.points.map(validateRewindPoint);
  if (new Set(points.map((item) => item.checkpointId)).size !== points.length) {
    throw new Error('VibeAgent returned duplicate rewind checkpoint IDs.');
  }
  if (!Number.isSafeInteger(report.total) || report.total < points.length) {
    throw new Error('VibeAgent returned an invalid rewind point count.');
  }
  const truncated = requireBoolean(report.truncated, 'rewind point truncation flag');
  if (truncated !== (report.total > points.length)) {
    throw new Error('VibeAgent returned inconsistent rewind point truncation state.');
  }
  return {
    session,
    ok: report.ok,
    exists: report.exists,
    total: report.total,
    truncated,
    points,
    message: optionalMessage(report.message),
  };
}

function parseCheckpointDiff(payload, expectedCheckpoint) {
  const report = requireReport(payload, 'checkpointDiff');
  const checkpoint = report.checkpoint;
  const diff = report.diff;
  if (!checkpoint || typeof checkpoint !== 'object' || !diff || typeof diff !== 'object') {
    throw new Error('VibeAgent returned an invalid checkpoint diff.');
  }
  const checkpointId = requireCheckpointId(checkpoint.id);
  if (checkpointId !== expectedCheckpoint) throw new Error('VibeAgent returned a diff for the wrong checkpoint.');
  if (typeof report.ok !== 'boolean' || typeof report.exists !== 'boolean') {
    throw new Error('VibeAgent returned an invalid checkpoint diff status.');
  }
  return {
    ok: report.ok,
    exists: report.exists,
    checkpointId,
    stagedPatch: boundedPatch(diff.stagedPatch, 'staged checkpoint patch'),
    unstagedPatch: boundedPatch(diff.unstagedPatch, 'unstaged checkpoint patch'),
    stagedTruncated: requireBoolean(diff.stagedTruncated, 'staged truncation flag'),
    unstagedTruncated: requireBoolean(diff.unstagedTruncated, 'unstaged truncation flag'),
    message: optionalMessage(report.message),
  };
}

function parseRewindPreview(payload, expectedSession, expectedCheckpoint, expectedMode) {
  const report = requireReport(payload, 'checkSessionRewind');
  validateRewindIdentity(report, expectedSession, expectedCheckpoint, expectedMode);
  const canRewind = requireBoolean(report.canRewind, 'rewind capability');
  return {
    ok: requireBoolean(report.ok, 'rewind preview status'),
    canRewind,
    session: report.session,
    checkpointId: report.checkpointId,
    mode: report.mode,
    eventLine: requireInteger(report.eventLine, canRewind ? 1 : 0, 'rewind event line'),
    codeWillChange: requireBoolean(report.codeWillChange, 'code impact flag'),
    conversationWillBranch: requireBoolean(report.conversationWillBranch, 'conversation impact flag'),
    message: optionalMessage(report.message),
  };
}

function parseRewindResult(payload, expectedSession, expectedCheckpoint, expectedMode) {
  const report = requireReport(payload, 'sessionRewind');
  validateRewindIdentity(
    { session: report.sourceSession, checkpointId: report.checkpointId, mode: report.mode },
    expectedSession,
    expectedCheckpoint,
    expectedMode,
  );
  const newSession = report.newSession === null ? null : requireSessionId(report.newSession);
  return {
    ok: requireBoolean(report.ok, 'rewind result status'),
    rewound: requireBoolean(report.rewound, 'rewound flag'),
    changed: requireBoolean(report.changed, 'rewind changed flag'),
    sourceSession: report.sourceSession,
    checkpointId: report.checkpointId,
    mode: report.mode,
    newSession,
    codeRestored: requireBoolean(report.codeRestored, 'code restored flag'),
    conversationBranched: requireBoolean(report.conversationBranched, 'conversation branched flag'),
    message: optionalMessage(report.message),
  };
}

function normalizeTarget(sessionId, checkpointId, mode) {
  return {
    session: requireSessionId(sessionId),
    checkpoint: requireCheckpointId(checkpointId),
    mode: requireMode(mode),
  };
}

function validateRewindPoint(value) {
  if (!value || typeof value !== 'object') throw new Error('VibeAgent returned an invalid rewind point.');
  return {
    checkpointId: requireCheckpointId(value.checkpointId),
    label: optionalInline(value.label, 200, 'checkpoint label'),
    createdAt: optionalInline(value.createdAt, 80, 'checkpoint timestamp'),
    eventLine: requireInteger(value.eventLine, 1, 'checkpoint event line'),
  };
}

function validateRewindIdentity(report, expectedSession, expectedCheckpoint, expectedMode) {
  const session = requireSessionId(report.session);
  const checkpoint = requireCheckpointId(report.checkpointId);
  const mode = requireMode(report.mode);
  if (session !== expectedSession || checkpoint !== expectedCheckpoint || mode !== expectedMode) {
    throw new Error('VibeAgent returned rewind data for the wrong target.');
  }
}

function requireReport(payload, key) {
  const report = payload && typeof payload === 'object' ? payload[key] : null;
  if (!report || typeof report !== 'object') throw new Error(`VibeAgent returned an invalid ${key} report.`);
  return report;
}

function requireCheckpointId(value) {
  if (typeof value !== 'string' || !value || value.length > 255 || value === '.' || value === '..' || /[\\/\x00-\x1f\x7f]/.test(value)) {
    throw new Error('VibeAgent returned an invalid checkpoint ID.');
  }
  return value;
}

function requireMode(value) {
  if (typeof value !== 'string' || !REWIND_MODES.has(value)) throw new Error('VibeAgent returned an invalid rewind mode.');
  return value;
}

function requireSuccessful(code, condition, message) {
  if (code !== 0 || !condition) throw new Error(message || `VibeAgent local command exited with status ${code}.`);
}

function requireBoolean(value, label) {
  if (typeof value !== 'boolean') throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function requireInteger(value, minimum, label) {
  if (!Number.isSafeInteger(value) || value < minimum) throw new Error(`VibeAgent returned an invalid ${label}.`);
  return value;
}

function boundedPatch(value, label) {
  if (typeof value !== 'string' || value.length > MAX_PATCH_CHARS || /[\x00\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) {
    throw new Error(`VibeAgent returned an invalid ${label}.`);
  }
  return value.replace(/\r\n?/g, '\n');
}

function optionalMessage(value) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value !== 'string' || value.length > 2_000 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) {
    throw new Error('VibeAgent returned an invalid rewind message.');
  }
  return value.replace(/\r\n?/g, '\n').trim() || null;
}

function optionalInline(value, maximum, label) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value !== 'string' || value.length > maximum || /[\x00-\x1f\x7f]/.test(value)) {
    throw new Error(`VibeAgent returned an invalid ${label}.`);
  }
  return value.trim() || null;
}

module.exports = {
  MAX_REWIND_POINTS,
  SessionRewindClient,
  parseCheckpointDiff,
  parseRewindPoints,
  parseRewindPreview,
  parseRewindResult,
  requireCheckpointId,
};
