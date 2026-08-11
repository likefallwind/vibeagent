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
  const range = selectionLineRange(selection);
  return range ? `${mention}#L${range.startLine}-L${range.endLine}` : mention;
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
  const normalized = normalizeDiagnostics(diagnostics);
  const items = normalized.items.map((diagnostic) => (
    `- ${diagnostic.severity} at line ${diagnostic.line}, source ${diagnostic.source}: ${diagnostic.message}`
  ));
  if (!items.length) {
    throw new Error('The active file has no diagnostics to send.');
  }
  if (normalized.omitted) {
    items.push(`- ${normalized.omitted} additional diagnostic(s) omitted.`);
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

function selectionLineRange(selection) {
  if (!selection || selection.isEmpty) return null;
  const startLine = Number(selection.start.line) + 1;
  const endLineIndex = Number(selection.end.line);
  const endCharacter = Number(selection.end.character);
  const endsAtNextLineStart = endLineIndex > Number(selection.start.line) && endCharacter === 0;
  const endLine = endLineIndex + (endsAtNextLineStart ? 0 : 1);
  if (!Number.isInteger(startLine) || !Number.isInteger(endLine) || startLine < 1 || endLine < startLine) {
    throw new Error('The editor selection has invalid line bounds.');
  }
  if (endLine - startLine + 1 > 1_000) {
    throw new Error('The editor selection must contain at most 1,000 lines.');
  }
  return { startLine, endLine };
}

function normalizeDiagnostics(diagnostics) {
  const sourceItems = Array.from(diagnostics || []);
  const items = sourceItems.slice(0, MAX_DIAGNOSTICS).map((diagnostic) => {
    const line = Number(diagnostic.range && diagnostic.range.start && diagnostic.range.start.line) + 1;
    return {
      severity: normalizeSeverity(diagnostic.severity),
      line: Number.isInteger(line) && line > 0 ? line : 1,
      source: boundedInlineText(diagnostic.source, 80) || 'unknown',
      message: boundedInlineText(diagnostic.message, MAX_DIAGNOSTIC_MESSAGE_CHARS),
    };
  });
  return { items, omitted: Math.max(0, sourceItems.length - items.length) };
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
  normalizeDiagnostics,
  normalizeLaunchConfig,
  selectionLineRange,
  workspaceRelativePath,
};
