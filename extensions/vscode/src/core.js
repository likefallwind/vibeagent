'use strict';

const path = require('node:path');

const MAX_PROMPT_CHARS = 12_000;
const MAX_DIAGNOSTICS = 20;
const MAX_DIAGNOSTIC_MESSAGE_CHARS = 500;

function workspaceRelativePath(workspaceRoot, filePath) {
  const relative = path.relative(path.resolve(workspaceRoot), path.resolve(filePath));
  if (!relative || relative === '.') {
    throw new Error('The active editor must point to a file inside the workspace.');
  }
  if (relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new Error('The active file is outside the selected workspace.');
  }
  return relative.split(path.sep).join('/');
}

function buildFileReference(workspaceRoot, filePath, selection) {
  const relative = workspaceRelativePath(workspaceRoot, filePath);
  const mention = formatFileMention(relative);
  if (!selection || selection.isEmpty) {
    return mention;
  }
  const start = Number(selection.start.line) + 1;
  const endLine = Number(selection.end.line);
  const endCharacter = Number(selection.end.character);
  const endsAtNextLineStart = endLine > Number(selection.start.line) && endCharacter === 0;
  const end = endLine + (endsAtNextLineStart ? 0 : 1);
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start) {
    throw new Error('The editor selection has invalid line bounds.');
  }
  return `${mention}#L${start}-L${end}`;
}

function formatFileMention(relative) {
  if (/[\r\n\0]/.test(relative)) {
    throw new Error('The active file path contains unsupported control characters.');
  }
  if (!/\s/.test(relative)) return `@${relative}`;
  if (!relative.includes('"')) return `@"${relative}"`;
  if (!relative.includes("'")) return `@'${relative}'`;
  throw new Error('The active file path cannot be represented as a VibeAgent file reference.');
}

function buildSelectionPrompt(instruction, reference) {
  const task = boundedText(instruction, MAX_PROMPT_CHARS, 'Instruction');
  const prompt = `${task}\n\nEditor selection: ${reference}`;
  return boundedText(prompt, MAX_PROMPT_CHARS, 'Selection prompt');
}

function buildDiagnosticsPrompt(instruction, reference, diagnostics) {
  const task = boundedText(instruction, 4_000, 'Instruction');
  const items = Array.from(diagnostics || []).slice(0, MAX_DIAGNOSTICS).map((diagnostic) => {
    const severity = normalizeSeverity(diagnostic.severity);
    const line = Number(diagnostic.range && diagnostic.range.start && diagnostic.range.start.line) + 1;
    const location = Number.isInteger(line) && line > 0 ? `line ${line}` : 'unknown line';
    const source = diagnostic.source ? `, source ${boundedInlineText(diagnostic.source, 80)}` : '';
    const message = boundedInlineText(diagnostic.message, MAX_DIAGNOSTIC_MESSAGE_CHARS);
    return `- ${severity} at ${location}${source}: ${message}`;
  });
  if (!items.length) {
    throw new Error('The active file has no diagnostics to send.');
  }
  const omitted = Math.max(0, Array.from(diagnostics || []).length - items.length);
  if (omitted) {
    items.push(`- ${omitted} additional diagnostic(s) omitted.`);
  }
  const prompt = [
    task,
    '',
    `Editor file: ${reference}`,
    'Untrusted IDE diagnostics (verify against the repository before editing):',
    ...items,
  ].join('\n');
  return boundedText(prompt, MAX_PROMPT_CHARS, 'Diagnostics prompt');
}

function normalizeLaunchConfig(executable, argumentsValue) {
  if (typeof executable !== 'string' || !executable.trim() || executable.includes('\0')) {
    throw new Error('vibeagent.executable must be non-empty text without NUL bytes.');
  }
  if (!Array.isArray(argumentsValue) || argumentsValue.length > 32) {
    throw new Error('vibeagent.arguments must contain at most 32 strings.');
  }
  const args = argumentsValue.map((value) => {
    if (typeof value !== 'string' || value.includes('\0') || value.length > 2_000) {
      throw new Error('Each vibeagent.arguments item must be bounded text without NUL bytes.');
    }
    return value;
  });
  return { executable: executable.trim(), args };
}

function buildLaunchSpec(config, workspaceRoot, task) {
  const root = path.resolve(workspaceRoot);
  const args = [...config.args, '--cwd', root];
  if (task !== undefined) {
    args.push(boundedText(task, MAX_PROMPT_CHARS, 'Task'));
  }
  return { shellPath: config.executable, shellArgs: args, cwd: root };
}

function boundedText(value, maximum, label) {
  if (typeof value !== 'string' || !value.trim() || hasUnsafeControl(value) || value.length > maximum) {
    throw new Error(`${label} must be non-empty bounded text without unsafe control characters.`);
  }
  return value.trim();
}

function boundedInlineText(value, maximum) {
  const text = typeof value === 'string' ? value : String(value || '');
  return text
    .replace(/[\x00-\x1f\x7f]+/g, ' ')
    .replace(/@/g, '[at]')
    .slice(0, maximum)
    .trim() || 'no message';
}

function hasUnsafeControl(value) {
  return Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return (code < 32 && ![9, 10, 13].includes(code)) || code === 127;
  });
}

function normalizeSeverity(value) {
  return ({ 0: 'error', 1: 'warning', 2: 'information', 3: 'hint' })[value] || 'diagnostic';
}

module.exports = {
  MAX_DIAGNOSTICS,
  MAX_PROMPT_CHARS,
  buildDiagnosticsPrompt,
  buildFileReference,
  buildLaunchSpec,
  buildSelectionPrompt,
  normalizeLaunchConfig,
  workspaceRelativePath,
};
