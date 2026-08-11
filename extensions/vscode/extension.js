'use strict';

const path = require('node:path');
const crypto = require('node:crypto');
const vscode = require('vscode');
const {
  buildDiagnosticsPrompt,
  buildFileReference,
  buildSelectionPrompt,
  normalizeLaunchConfig,
  workspaceRelativePath,
} = require('./src/core');
const { IdeContextBridge } = require('./src/context');
const { AgentPanelManager } = require('./src/agentPanel');
const { AgentChangeContentProvider } = require('./src/agentChanges');
const { SessionCatalog, sessionQuickPickItems } = require('./src/sessionCatalog');
const { InteractiveTerminalManager } = require('./src/terminals');
const { PlanReviewManager } = require('./src/sessionPlan');
const { RewindReviewManager } = require('./src/sessionRewind');

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
  const contextBridges = new Map();
  const diffProvider = new GitHeadContentProvider();
  const agentChangeProvider = new AgentChangeContentProvider(vscode);
  const agentPanels = new AgentPanelManager(vscode, { changeProvider: agentChangeProvider });
  const sessionCatalog = new SessionCatalog();
  const planReviews = new PlanReviewManager(vscode);
  const terminals = new InteractiveTerminalManager(vscode, {
    prepareEnvironment(root) {
      const bridge = contextBridge(root);
      refreshEditorContext(vscode.window.activeTextEditor);
      return bridge.environment();
    },
  });
  const rewindReviews = new RewindReviewManager(vscode, {
    catalog: sessionCatalog,
    terminals,
  });
  context.subscriptions.push(
    diffProvider,
    agentChangeProvider,
    agentPanels,
    planReviews,
    rewindReviews,
    terminals,
    vscode.workspace.registerTextDocumentContentProvider('vibeagent-git', diffProvider),
    vscode.workspace.registerTextDocumentContentProvider('vibeagent-change', agentChangeProvider),
    vscode.window.onDidCloseTerminal((terminal) => terminals.closed(terminal)),
    vscode.workspace.onDidCloseTextDocument((document) => planReviews.closed(document)),
    vscode.workspace.onDidCloseTextDocument((document) => rewindReviews.closed(document)),
    vscode.window.onDidChangeActiveTextEditor((editor) => refreshEditorContext(editor)),
    vscode.window.onDidChangeTextEditorSelection((event) => refreshEditorContext(event.textEditor)),
    vscode.languages.onDidChangeDiagnostics(() => refreshEditorContext(vscode.window.activeTextEditor)),
  );

  const register = (name, handler) => context.subscriptions.push(
    vscode.commands.registerCommand(name, () => runCommand(handler)),
  );

  register('vibeagent.open', async () => {
    const root = activeWorkspaceRoot();
    terminals.openPrimary(launchConfig(), root);
  });

  register('vibeagent.newSession', async () => {
    const root = activeWorkspaceRoot();
    terminals.openNew(launchConfig(), root);
  });

  register('vibeagent.resumeSession', async () => {
    const root = activeWorkspaceRoot();
    const launch = launchConfig();
    const sessions = await sessionCatalog.list(launch, root);
    if (!sessions.length) {
      vscode.window.showInformationMessage('No VibeAgent sessions are available in this workspace.');
      return;
    }
    const selected = await vscode.window.showQuickPick(sessionQuickPickItems(sessions), {
      title: 'Resume VibeAgent Session',
      placeHolder: 'Choose a recent workspace session',
      matchOnDescription: true,
      matchOnDetail: true,
      ignoreFocusOut: true,
    });
    if (!selected) return;
    terminals.resume(launch, root, selected.session, selected.label);
  });

  register('vibeagent.reviewSessionPlan', async () => {
    const root = activeWorkspaceRoot();
    const launch = launchConfig();
    const sessions = await sessionCatalog.list(launch, root);
    if (!sessions.length) {
      vscode.window.showInformationMessage('No VibeAgent sessions are available in this workspace.');
      return;
    }
    const selected = await vscode.window.showQuickPick(sessionQuickPickItems(sessions), {
      title: 'Review VibeAgent Session Plan',
      placeHolder: 'Choose a recent workspace session',
      matchOnDescription: true,
      matchOnDetail: true,
      ignoreFocusOut: true,
    });
    if (!selected) return;
    const session = sessions.find((item) => item.session === selected.session);
    if (!session) throw new Error('The selected VibeAgent session is no longer available.');
    await planReviews.open(launch, root, session);
  });

  register('vibeagent.executeReviewedPlan', async () => {
    const review = planReviews.activeExecution();
    terminals.resumeTask(
      launchConfig(),
      review.root,
      review.session,
      review.name,
      review.prompt,
    );
  });

  register('vibeagent.reviewSessionRewind', async () => {
    const root = activeWorkspaceRoot();
    await rewindReviews.open(launchConfig(), root);
  });

  register('vibeagent.executeReviewedRewind', async () => {
    await rewindReviews.executeActive(launchConfig());
  });

  register('vibeagent.openAgentPanel', async () => {
    const root = activeWorkspaceRoot();
    const bridge = contextBridge(root);
    refreshEditorContext(vscode.window.activeTextEditor);
    await agentPanels.open(root, launchConfig(), bridge.environment());
  });

  register('vibeagent.insertReference', async () => {
    const { editor, root } = activeEditorContext();
    const reference = buildFileReference(root, editor.document.uri.fsPath, editor.selection);
    const terminal = terminals.referenceTarget(root);
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
    terminals.openTask('VibeAgent Task', launchConfig(), root, task);
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
    terminals.openTask('VibeAgent Diagnostics', launchConfig(), root, task);
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

  function launchConfig() {
    const configuration = vscode.workspace.getConfiguration('vibeagent');
    return normalizeLaunchConfig(
      configuration.get('executable', 'python'),
      configuration.get('arguments', ['-m', 'vibeagent']),
    );
  }

  function contextBridge(root) {
    let bridge = contextBridges.get(root);
    if (!bridge) {
      bridge = new IdeContextBridge(root);
      contextBridges.set(root, bridge);
      context.subscriptions.push(bridge);
    }
    return bridge;
  }

  function refreshEditorContext(editor) {
    if (!editor || editor.document.uri.scheme !== 'file') return;
    const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
    if (!folder) return;
    const bridge = contextBridges.get(folder.uri.fsPath);
    if (!bridge) return;
    try {
      bridge.update(editor, vscode.languages.getDiagnostics(editor.document.uri));
    } catch (_error) {
      bridge.update(null, []);
    }
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
