'use strict';

const path = require('node:path');
const crypto = require('node:crypto');
const vscode = require('vscode');
const {
  buildDiagnosticsPrompt,
  buildFileReference,
  buildLaunchSpec,
  buildSelectionPrompt,
  normalizeLaunchConfig,
  workspaceRelativePath,
} = require('./src/core');

class GitHeadContentProvider {
  constructor() {
    this.entries = new Map();
    this.changeEmitter = new vscode.EventEmitter();
    this.onDidChange = this.changeEmitter.event;
  }

  track(repository, relativePath) {
    const id = crypto.randomUUID();
    const uri = vscode.Uri.parse(`vibeagent-git:/head/${encodeURIComponent(path.basename(relativePath))}?${id}`);
    this.entries.set(uri.toString(), { repository, relativePath });
    return uri;
  }

  async provideTextDocumentContent(uri) {
    const entry = this.entries.get(uri.toString());
    if (!entry) {
      throw new Error('The VibeAgent diff source is no longer available.');
    }
    const content = await entry.repository.show('HEAD', entry.relativePath);
    return Buffer.from(content).toString('utf8');
  }

  dispose() {
    this.entries.clear();
    this.changeEmitter.dispose();
  }
}

function activate(context) {
  const interactiveTerminals = new Map();
  const diffProvider = new GitHeadContentProvider();
  context.subscriptions.push(
    diffProvider,
    vscode.workspace.registerTextDocumentContentProvider('vibeagent-git', diffProvider),
    vscode.window.onDidCloseTerminal((terminal) => {
      for (const [root, candidate] of interactiveTerminals) {
        if (candidate === terminal) interactiveTerminals.delete(root);
      }
    }),
  );

  const register = (name, handler) => context.subscriptions.push(
    vscode.commands.registerCommand(name, () => runCommand(handler)),
  );

  register('vibeagent.open', async () => {
    const root = activeWorkspaceRoot();
    let terminal = interactiveTerminals.get(root);
    if (!terminal) {
      terminal = createTerminal('VibeAgent', root);
      interactiveTerminals.set(root, terminal);
    }
    terminal.show(false);
  });

  register('vibeagent.insertReference', async () => {
    const { editor, root } = activeEditorContext();
    const reference = buildFileReference(root, editor.document.uri.fsPath, editor.selection);
    const terminal = interactiveTerminals.get(root);
    if (!terminal) {
      await vscode.env.clipboard.writeText(reference);
      vscode.window.showInformationMessage('File reference copied. Open a VibeAgent session and paste it into the prompt.');
      return;
    }
    terminal.show(false);
    terminal.sendText(reference, false);
  });

  register('vibeagent.askSelection', async () => {
    const { editor, root } = activeEditorContext();
    const instruction = await vscode.window.showInputBox({
      title: 'Ask VibeAgent About Selection',
      prompt: 'What should VibeAgent do?',
      ignoreFocusOut: true,
      validateInput: validatePrompt,
    });
    if (instruction === undefined) return;
    const reference = buildFileReference(root, editor.document.uri.fsPath, editor.selection);
    const task = buildSelectionPrompt(instruction, reference);
    createTerminal('VibeAgent Task', root, task).show(false);
  });

  register('vibeagent.sendDiagnostics', async () => {
    const { editor, root } = activeEditorContext();
    const diagnostics = vscode.languages.getDiagnostics(editor.document.uri);
    const instruction = await vscode.window.showInputBox({
      title: 'Send Diagnostics to VibeAgent',
      value: 'Investigate and fix these diagnostics',
      ignoreFocusOut: true,
      validateInput: validatePrompt,
    });
    if (instruction === undefined) return;
    const reference = buildFileReference(root, editor.document.uri.fsPath, undefined);
    const task = buildDiagnosticsPrompt(instruction, reference, diagnostics);
    createTerminal('VibeAgent Diagnostics', root, task).show(false);
  });

  register('vibeagent.reviewCurrentFile', async () => {
    const { editor, root } = activeEditorContext();
    const gitExtension = vscode.extensions.getExtension('vscode.git');
    if (!gitExtension) throw new Error('The built-in VS Code Git extension is unavailable.');
    const git = gitExtension.isActive ? gitExtension.exports : await gitExtension.activate();
    const repository = git.getAPI(1).getRepository(editor.document.uri);
    if (!repository) throw new Error('The active file is not in an open Git repository.');
    const relativePath = workspaceRelativePath(repository.rootUri.fsPath, editor.document.uri.fsPath);
    const original = diffProvider.track(repository, relativePath);
    await vscode.commands.executeCommand(
      'vscode.diff',
      original,
      editor.document.uri,
      `${path.basename(relativePath)} (HEAD to Working Tree)`,
    );
  });

  function createTerminal(name, root, task) {
    const configuration = vscode.workspace.getConfiguration('vibeagent');
    const launch = normalizeLaunchConfig(
      configuration.get('executable', 'python'),
      configuration.get('arguments', ['-m', 'vibeagent']),
    );
    return vscode.window.createTerminal({ name, ...buildLaunchSpec(launch, root, task) });
  }
}

function activeWorkspaceRoot() {
  const editor = vscode.window.activeTextEditor;
  if (editor) {
    const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
    if (folder) return folder.uri.fsPath;
  }
  const folders = vscode.workspace.workspaceFolders || [];
  if (folders.length === 1) return folders[0].uri.fsPath;
  throw new Error('Open a file inside a workspace before starting VibeAgent.');
}

function activeEditorContext() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.uri.scheme !== 'file') {
    throw new Error('Open a workspace file before using this VibeAgent command.');
  }
  const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
  if (!folder) throw new Error('The active file is not inside an open workspace.');
  return { editor, root: folder.uri.fsPath };
}

function validatePrompt(value) {
  if (!value || !value.trim()) return 'Enter a task for VibeAgent.';
  if (value.includes('\0')) return 'The task cannot contain NUL bytes.';
  if (value.length > 4_000) return 'The task must be at most 4,000 characters.';
  return undefined;
}

async function runCommand(handler) {
  try {
    await handler();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    vscode.window.showErrorMessage(`VibeAgent: ${message}`);
  }
}

function deactivate() {}

module.exports = { activate, deactivate, GitHeadContentProvider };
