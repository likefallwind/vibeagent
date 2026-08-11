'use strict';

const MAX_INSPECTOR_DOCUMENT_CHARS = 250_000;

function renderSessionInspector(report) {
  const { overview, plan, tasks, verification, files, transcript } = report;
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
  appendTasks(lines, tasks);
  appendVerification(lines, verification);
  appendFiles(lines, files);
  appendTimeline(lines, transcript);
  const content = `${lines.join('\n')}\n`;
  if (content.length > MAX_INSPECTOR_DOCUMENT_CHARS) {
    throw new Error(`VibeAgent session inspector exceeds ${MAX_INSPECTOR_DOCUMENT_CHARS} rendered characters.`);
  }
  return content;
}

function appendTasks(lines, tasks) {
  const counts = tasks.counts;
  lines.push(
    '',
    `## Persistent Tasks (${tasks.shown}/${tasks.total})`,
    '',
    `Pending: ${counts.pending}; in progress: ${counts.inProgress}; completed: ${counts.completed}; blocked: ${counts.blocked}`,
    '',
  );
  if (!tasks.items.length) {
    lines.push('_No persistent tasks._');
    return;
  }
  for (const item of tasks.items) {
    const checked = item.status === 'completed' ? 'x' : ' ';
    const blocked = item.blocked ? ' (blocked)' : '';
    lines.push(`- [${checked}] ${inlineCode(`#${item.id}`)} ${escapeMarkdown(item.status)}${blocked}: ${escapeMarkdown(item.subject)}`);
    if (item.owner) lines.push(`  Owner: ${inlineCode(item.owner)}`);
    if (item.blockedBy.length) lines.push(`  Blocked by: ${item.blockedBy.map((id) => inlineCode(`#${id}`)).join(', ')}`);
    if (item.blocks.length) lines.push(`  Blocks: ${item.blocks.map((id) => inlineCode(`#${id}`)).join(', ')}`);
    lines.push(...indentedText(item.description));
  }
  if (tasks.truncated) lines.push(`${tasks.omitted} task(s) omitted.`);
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

module.exports = { MAX_INSPECTOR_DOCUMENT_CHARS, renderSessionInspector };
