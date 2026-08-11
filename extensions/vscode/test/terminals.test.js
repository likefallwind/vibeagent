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

  vscode.window.activeTerminal = parallel;
  assert.equal(manager.referenceTarget(root), parallel);
  vscode.window.activeTerminal = { unrelated: true };
  assert.equal(manager.referenceTarget(root), primary);
  manager.closed(primary);
  assert.equal(manager.referenceTarget(root), resumed);
  manager.closed(resumed);
  assert.equal(manager.resume(config, root, 'run-123'), terminals.at(-1));
  assert.equal(terminals.length, 4);
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
