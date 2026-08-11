'use strict';

const assert = require('node:assert/strict');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

test('registers IDE commands and routes editor context through native VS Code surfaces', async () => {
  const callbacks = new Map();
  const terminals = [];
  const executed = [];
  const errors = [];
  let contentProvider;
  const root = path.resolve('/workspace/project');
  const file = path.join(root, 'src', 'app.py');
  const documentUri = { scheme: 'file', fsPath: file };
  const repository = {
    rootUri: { fsPath: root },
    async show(revision, relativePath) {
      assert.equal(revision, 'HEAD');
      assert.equal(relativePath, 'src/app.py');
      return 'old content\n';
    },
  };

  class EventEmitter {
    constructor() {
      this.event = () => ({ dispose() {} });
    }
    dispose() {}
  }

  const vscode = {
    EventEmitter,
    Uri: {
      parse(value) {
        return { value, toString: () => value };
      },
    },
    commands: {
      registerCommand(name, callback) {
        callbacks.set(name, callback);
        return { dispose() {} };
      },
      async executeCommand(...args) {
        executed.push(args);
      },
    },
    env: { clipboard: { async writeText() {} } },
    extensions: {
      getExtension(name) {
        assert.equal(name, 'vscode.git');
        return {
          isActive: true,
          exports: { getAPI: () => ({ getRepository: () => repository }) },
        };
      },
    },
    languages: {
      getDiagnostics() {
        return [{ severity: 0, message: 'undefined name', source: 'lint', range: { start: { line: 1 } } }];
      },
    },
    window: {
      activeTextEditor: {
        document: { uri: documentUri },
        selection: {
          isEmpty: false,
          start: { line: 1, character: 1 },
          end: { line: 2, character: 4 },
        },
      },
      createTerminal(options) {
        const terminal = {
          options,
          shown: 0,
          sent: [],
          show() { this.shown += 1; },
          sendText(value, newline) { this.sent.push([value, newline]); },
        };
        terminals.push(terminal);
        return terminal;
      },
      onDidCloseTerminal() { return { dispose() {} }; },
      async showInputBox(options) {
        return options.title.includes('Diagnostics') ? 'Fix diagnostics' : 'Explain selection';
      },
      showErrorMessage(message) { errors.push(message); },
      showInformationMessage() {},
    },
    workspace: {
      workspaceFolders: [{ uri: { fsPath: root } }],
      getWorkspaceFolder() { return { uri: { fsPath: root } }; },
      getConfiguration() { return { get: (_name, fallback) => fallback }; },
      registerTextDocumentContentProvider(_scheme, provider) {
        contentProvider = provider;
        return { dispose() {} };
      },
    },
  };

  const originalLoad = Module._load;
  Module._load = function load(request, parent, isMain) {
    if (request === 'vscode') return vscode;
    return originalLoad.call(this, request, parent, isMain);
  };
  let extension;
  try {
    const extensionPath = require.resolve('../extension');
    delete require.cache[extensionPath];
    extension = require('../extension');
  } finally {
    Module._load = originalLoad;
  }

  const context = { subscriptions: [] };
  extension.activate(context);
  assert.deepEqual(new Set(callbacks.keys()), new Set([
    'vibeagent.open',
    'vibeagent.askSelection',
    'vibeagent.insertReference',
    'vibeagent.sendDiagnostics',
    'vibeagent.reviewCurrentFile',
  ]));

  await callbacks.get('vibeagent.open')();
  assert.equal(terminals[0].options.shellPath, 'python');
  assert.deepEqual(terminals[0].options.shellArgs, ['-m', 'vibeagent', '--cwd', root]);

  await callbacks.get('vibeagent.insertReference')();
  assert.deepEqual(terminals[0].sent, [['@src/app.py#L2-L3', false]]);

  await callbacks.get('vibeagent.askSelection')();
  assert.match(terminals[1].options.shellArgs.at(-1), /Editor selection: @src\/app.py#L2-L3/);

  await callbacks.get('vibeagent.sendDiagnostics')();
  assert.match(terminals[2].options.shellArgs.at(-1), /Untrusted IDE diagnostics/);
  assert.match(terminals[2].options.shellArgs.at(-1), /error at line 2, source lint: undefined name/);

  await callbacks.get('vibeagent.reviewCurrentFile')();
  assert.equal(executed.at(-1)[0], 'vscode.diff');
  assert.equal(await contentProvider.provideTextDocumentContent(executed.at(-1)[1]), 'old content\n');
  assert.deepEqual(errors, []);
});
