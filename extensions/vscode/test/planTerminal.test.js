'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { InteractiveTerminalManager } = require('../src/terminals');

test('executes a reviewed plan as a bounded task in the exact resumed session', () => {
  const created = [];
  const vscode = {
    window: {
      activeTerminal: null,
      createTerminal(options) {
        const terminal = { options, show() {} };
        created.push(terminal);
        return terminal;
      },
    },
  };
  const manager = new InteractiveTerminalManager(vscode);
  const prompt = 'Implement the reviewed plan\n\n- [ ] Run tests';
  const terminal = manager.resumeTask(
    { executable: 'python', args: ['-m', 'vibeagent'] },
    '/workspace/project',
    'run-123',
    'Parser repair',
    prompt,
  );
  assert.equal(terminal.options.name, 'VibeAgent Plan: Parser repair');
  assert.deepEqual(terminal.options.shellArgs, [
    '-m', 'vibeagent', '--cwd', '/workspace/project', '--resume', 'run-123', prompt,
  ]);
  vscode.window.activeTerminal = terminal;
  assert.equal(manager.referenceTarget('/workspace/project'), null);
  assert.throws(
    () => manager.resumeTask(
      { executable: 'python', args: [] }, '/workspace', '../escape', null, prompt,
    ),
    /session ID/,
  );
});

test('continues an inspected task in a visible one-shot resumed terminal', () => {
  const created = [];
  const vscode = {
    window: {
      activeTerminal: null,
      createTerminal(options) {
        const terminal = { options, shown: 0, show() { this.shown += 1; } };
        created.push(terminal);
        return terminal;
      },
    },
  };
  const manager = new InteractiveTerminalManager(vscode);
  const prompt = 'Continue persistent session task #7.';
  const terminal = manager.continueTask(
    { executable: 'python', args: ['-m', 'vibeagent'] },
    '/workspace/project',
    'run-123',
    'Repair parser',
    prompt,
  );

  assert.equal(terminal.options.name, 'VibeAgent Task: Repair parser');
  assert.deepEqual(terminal.options.shellArgs, [
    '-m', 'vibeagent', '--cwd', '/workspace/project', '--resume', 'run-123', prompt,
  ]);
  assert.equal(terminal.shown, 1);
  vscode.window.activeTerminal = terminal;
  assert.equal(manager.referenceTarget('/workspace/project'), null);
  assert.throws(
    () => manager.continueTask(
      { executable: 'python', args: [] }, '/workspace', '../escape', 'Task', prompt,
    ),
    /session ID/,
  );
});
