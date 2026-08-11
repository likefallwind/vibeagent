'use strict';

const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const { EventEmitter: NodeEventEmitter } = require('node:events');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

test('registers IDE commands and routes editor context through native VS Code surfaces', async () => {
  const callbacks = new Map();
  const terminals = [];
  const executed = [];
  const errors = [];
  const contentProviders = new Map();
  const catalogCalls = [];
  const quickPicks = [];
  const textDocuments = [];
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
      onDidChangeDiagnostics() { return { dispose() {} }; },
    },
    window: {
      activeTextEditor: {
        document: { uri: documentUri, isDirty: true },
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
      onDidChangeActiveTextEditor() { return { dispose() {} }; },
      onDidChangeTextEditorSelection() { return { dispose() {} }; },
      async showInputBox(options) {
        return options.title.includes('Diagnostics') ? 'Fix diagnostics' : 'Explain selection';
      },
      async showQuickPick(items, options) {
        quickPicks.push({ items, options });
        return items[0];
      },
      async showTextDocument(document, options) {
        textDocuments.push({ document, options });
        this.activeTextEditor = { document };
        return this.activeTextEditor;
      },
      showErrorMessage(message) { errors.push(message); },
      showInformationMessage() {},
    },
    workspace: {
      workspaceFolders: [{ uri: { fsPath: root } }],
      getWorkspaceFolder() { return { uri: { fsPath: root } }; },
      getConfiguration() { return { get: (_name, fallback) => fallback }; },
      onDidCloseTextDocument() { return { dispose() {} }; },
      async openTextDocument(options) {
        const document = {
          uri: { scheme: 'untitled', toString: () => `untitled:plan-${textDocuments.length + 1}` },
          getText: () => options.content,
        };
        textDocuments.push({ document, options });
        return document;
      },
      registerTextDocumentContentProvider(_scheme, provider) {
        contentProviders.set(_scheme, provider);
        return { dispose() {} };
      },
    },
  };

  const originalSpawn = childProcess.spawn;
  childProcess.spawn = (executable, args, options) => {
    catalogCalls.push({ executable, args, options });
    const child = new NodeEventEmitter();
    child.stdout = new NodeEventEmitter();
    child.stderr = new NodeEventEmitter();
    child.kill = () => {};
    process.nextTick(() => {
      if (args.includes('--plan')) {
        child.stdout.emit('data', Buffer.from(JSON.stringify({
          schemaVersion: 1,
          kind: 'local',
          sessionPlan: {
            session: 'run-123',
            exists: true,
            ok: true,
            status: 'in_progress',
            message: 'Found 2 plan item(s).',
            task: 'Fix parser',
            items: [{ status: 'in_progress', step: 'Implement parser fix' }],
          },
        })));
        child.emit('close', 0);
        return;
      }
      child.stdout.emit('data', Buffer.from(JSON.stringify({
        schemaVersion: 1,
        kind: 'local',
        sessions: {
          exists: true,
          sessions: {
            items: [{
              session: 'run-123', status: 'completed', events: 7, malformed: 0,
              lastEventTime: '2026-08-11T20:00:00+00:00', name: 'Parser repair',
              task: 'Fix parser', completed: true, failed: false, blocked: false,
            }],
          },
        },
      })));
      child.emit('close', 0);
    });
    return child;
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
  try {
    extension.activate(context);
  } finally {
    childProcess.spawn = originalSpawn;
  }
  assert.deepEqual(new Set(callbacks.keys()), new Set([
    'vibeagent.open',
    'vibeagent.newSession',
    'vibeagent.resumeSession',
    'vibeagent.reviewSessionPlan',
    'vibeagent.executeReviewedPlan',
    'vibeagent.openAgentPanel',
    'vibeagent.askSelection',
    'vibeagent.insertReference',
    'vibeagent.sendDiagnostics',
    'vibeagent.reviewCurrentFile',
  ]));

  await callbacks.get('vibeagent.open')();
  assert.equal(terminals[0].options.shellPath, 'python');
  assert.deepEqual(terminals[0].options.shellArgs, ['-m', 'vibeagent', '--cwd', root]);
  const contextPayload = JSON.parse(fs.readFileSync(terminals[0].options.env.VIBEAGENT_IDE_CONTEXT_FILE, 'utf8'));
  assert.equal(contextPayload.token, terminals[0].options.env.VIBEAGENT_IDE_CONTEXT_TOKEN);
  assert.equal(contextPayload.file, 'src/app.py');
  assert.equal(contextPayload.dirty, true);
  assert.deepEqual(contextPayload.selection, { startLine: 2, endLine: 3 });
  assert.equal(contextPayload.diagnostics[0].message, 'undefined name');

  await callbacks.get('vibeagent.insertReference')();
  assert.deepEqual(terminals[0].sent, [['@src/app.py#L2-L3', false]]);

  await callbacks.get('vibeagent.newSession')();
  assert.deepEqual(terminals[1].options.shellArgs, ['-m', 'vibeagent', '--cwd', root]);

  await callbacks.get('vibeagent.resumeSession')();
  assert.deepEqual(catalogCalls[0].args, [
    '-m', 'vibeagent', '--json', '--cwd', root, '--sessions',
  ]);
  assert.equal(catalogCalls[0].options.shell, false);
  assert.equal(quickPicks[0].options.title, 'Resume VibeAgent Session');
  assert.deepEqual(terminals[2].options.shellArgs, [
    '-m', 'vibeagent', '--cwd', root, '--resume', 'run-123',
  ]);

  await callbacks.get('vibeagent.askSelection')();
  assert.match(terminals[3].options.shellArgs.at(-1), /Editor selection: @src\/app.py#L2-L3/);

  await callbacks.get('vibeagent.sendDiagnostics')();
  assert.match(terminals[4].options.shellArgs.at(-1), /Untrusted IDE diagnostics/);
  assert.match(terminals[4].options.shellArgs.at(-1), /error at line 2, source lint: undefined name/);

  await callbacks.get('vibeagent.reviewCurrentFile')();
  assert.equal(executed.at(-1)[0], 'vscode.diff');
  assert.equal(
    await contentProviders.get('vibeagent-git').provideTextDocumentContent(executed.at(-1)[1]),
    'old content\n',
  );
  assert.deepEqual(errors, []);
  for (const disposable of context.subscriptions.reverse()) {
    if (disposable && typeof disposable.dispose === 'function') disposable.dispose();
  }
});
