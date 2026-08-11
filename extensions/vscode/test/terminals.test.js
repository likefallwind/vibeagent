'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const { InteractiveTerminalManager } = require('../src/terminals');

test('manages primary, parallel, and exact resumed terminals', () => {
  const terminals = [];
  const vscode = {
    window: {
      activeTerminal: null,
      createTerminal(options) {
        const terminal = { options, shown: 0, show() { this.shown += 1; } };
        terminals.push(terminal);
        return terminal;
      },
    },
  };
  const manager = new InteractiveTerminalManager(vscode, {
    prepareEnvironment: (root) => ({ ROOT: root }),
  });
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };
  const root = path.resolve('/workspace/project');
  let changes = 0;
  const changeSubscription = manager.onDidChange(() => { changes += 1; });

  const primary = manager.openPrimary(config, root);
  assert.equal(manager.openPrimary(config, root), primary);
  assert.equal(primary.shown, 2);
  const parallel = manager.openNew(config, root);
  const resumed = manager.resume(config, root, 'run-123', 'Parser repair');
  assert.equal(manager.resume(config, root, 'run-123', 'Ignored new title'), resumed);
  assert.deepEqual(resumed.options.shellArgs, [
    '-m', 'vibeagent', '--cwd', root, '--resume', 'run-123',
  ]);
  assert.equal(resumed.options.name, 'VibeAgent: Parser repair');
  assert.equal(resumed.options.env.ROOT, root);
  assert.equal(terminals.length, 3);
  assert.equal(manager.sessionCount(root), 3);
  assert.equal(manager.sessionCount('/workspace/other'), 0);
  assert.equal(changes, 3);

  vscode.window.activeTerminal = parallel;
  assert.equal(manager.referenceTarget(root), parallel);
  vscode.window.activeTerminal = { unrelated: true };
  assert.equal(manager.referenceTarget(root), primary);
  manager.closed(primary);
  assert.equal(manager.sessionCount(root), 2);
  assert.equal(changes, 4);
  assert.equal(manager.referenceTarget(root), resumed);
  manager.closed(resumed);
  assert.equal(manager.resume(config, root, 'run-123'), terminals.at(-1));
  assert.equal(terminals.length, 4);
  assert.equal(manager.sessionCount(root), 2);
  changeSubscription.dispose();
  manager.openNew(config, root);
  assert.equal(changes, 6);
  assert.throws(() => manager.onDidChange(null), /listener must be a function/);
  assert.throws(() => manager.resume(config, root, '../escape'), /session ID/);
});

test('keeps one-shot task terminals outside interactive reference routing', () => {
  const terminals = [];
  const vscode = {
    window: {
      activeTerminal: null,
      createTerminal(options) {
        const terminal = { options, show() {} };
        terminals.push(terminal);
        return terminal;
      },
    },
  };
  const manager = new InteractiveTerminalManager(vscode);
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };
  manager.openTask('Task', config, '/workspace/project', 'fix tests');
  vscode.window.activeTerminal = terminals[0];
  assert.equal(manager.referenceTarget('/workspace/project'), null);
});

test('runs bounded session verification in a visible untracked terminal', () => {
  const terminals = [];
  const vscode = {
    window: {
      activeTerminal: null,
      createTerminal(options) {
        const terminal = { options, shown: 0, show() { this.shown += 1; } };
        terminals.push(terminal);
        return terminal;
      },
    },
  };
  const manager = new InteractiveTerminalManager(vscode);
  const config = { executable: 'python', args: ['-m', 'vibeagent'] };
  const terminal = manager.runVerification(config, '/workspace/project', 'run-123', 'Parser repair');

  assert.equal(terminal.options.name, 'VibeAgent Verify: Parser repair');
  assert.deepEqual(terminal.options.shellArgs, [
    '-m', 'vibeagent', '--cwd', path.resolve('/workspace/project'),
    '--run-session-verification', 'run-123', '--session-max-checks', '10',
    '--run-output-contexts', '--run-output-diagnostics',
  ]);
  assert.equal(terminal.shown, 1);
  vscode.window.activeTerminal = terminal;
  assert.equal(manager.referenceTarget('/workspace/project'), null);
  assert.throws(
    () => manager.runVerification(config, '/workspace/project', '../escape'),
    /session ID/,
  );
});
