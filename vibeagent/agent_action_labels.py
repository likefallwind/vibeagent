from __future__ import annotations

from .agent_observation_utils import summarize
from .agent_action_label_file_ops import build_file_operation_step_label
from .agent_action_label_process_ops import build_process_step_label
from . import types as t


def build_step_label(action: object) -> str:
    if isinstance(action, t.EnterWorktreeAction):
        return f"Enter worktree {action.path or action.name or 'generated'}"
    if isinstance(action, t.ExitWorktreeAction):
        return "Exit worktree"
    label = build_file_operation_step_label(action)
    if label is not None:
        return label
    label = build_process_step_label(action)
    if label is not None:
        return label
    if isinstance(action, t.UpdatePlanAction):
        return "Update plan"
    if isinstance(action, t.AskUserAction):
        return "Ask user"
    if isinstance(action, t.DelegateTaskAction):
        return "Delegate task"
    if isinstance(action, t.RepoMapAction):
        return f"Map repo {action.path or '.'}"
    if isinstance(action, t.ReadFileAction):
        return f"Read {action.path}"
    if isinstance(action, t.ReadFileContextAction):
        return f"Read {action.path}:{action.line}"
    if isinstance(action, t.ReadFileContextsAction):
        return f"Read {len(action.contexts)} file contexts"
    if isinstance(action, t.OutputContextsAction):
        return f"Read output contexts from {action.max_contexts} reference(s)"
    if isinstance(action, t.SessionOutputContextsAction):
        return f"Read session output contexts for {action.run_id or 'current session'}"
    if isinstance(action, t.SessionOutputDiagnosticsAction):
        return f"Read session output diagnostics for {action.run_id or 'current session'}"
    if isinstance(action, t.TailFileAction):
        return f"Tail {action.path}"
    if isinstance(action, t.ReadFilesAction):
        return f"Read {len(action.paths)} files"
    if isinstance(action, t.ReadFileRangesAction):
        return f"Read {len(action.ranges)} file ranges"
    if isinstance(action, t.FileInfoAction):
        return f"Inspect {len(action.paths)} paths"
    if isinstance(action, t.ImageInfoAction):
        return f"Inspect {len(action.paths)} images"
    if isinstance(action, t.ViewImageAction):
        return f"View image {action.path}"
    if isinstance(action, t.PythonSymbolsAction):
        return f"Read Python symbols for {len(action.paths)} files"
    if isinstance(action, t.CodeOutlineAction):
        return f"Read code outlines for {len(action.paths)} files"
    if isinstance(action, t.LspQueryAction):
        return f"LSP {action.operation} {action.path or action.symbol or '.'}"
    if isinstance(action, t.PythonCheckAction):
        return f"Check Python {action.path or '.'}"
    if isinstance(action, t.ConfigCheckAction):
        return f"Check config {action.path or '.'}"
    if isinstance(action, t.CheckJsonSetAction):
        return f"Check JSON set {action.path} {action.pointer}"
    if isinstance(action, t.JsonSetAction):
        return f"Set JSON {action.path} {action.pointer}"
    if isinstance(action, t.CheckJsonRemoveAction):
        return f"Check JSON remove {action.path} {action.pointer}"
    if isinstance(action, t.JsonRemoveAction):
        return f"Remove JSON {action.path} {action.pointer}"
    if isinstance(action, t.CheckJsonPatchAction):
        return f"Check JSON patch {action.path}"
    if isinstance(action, t.JsonPatchAction):
        return f"Patch JSON {action.path}"
    if isinstance(action, t.PythonDependenciesAction):
        return f"Read Python dependencies {action.path or '.'}"
    if isinstance(action, t.CodeDependenciesAction):
        return f"Read code dependencies {action.path or '.'}"
    if isinstance(action, t.CodeReferencesAction):
        return f"Find code references {action.symbol}"
    if isinstance(action, t.CodeReferenceContextsAction):
        return f"Read code reference contexts {action.symbol}"
    if isinstance(action, t.CodeDefinitionsAction):
        return f"Find code definitions {action.symbol}"
    if isinstance(action, t.CodeRenamePreviewAction):
        return f"Preview code rename {action.symbol} to {action.new_name}"
    if isinstance(action, t.CodeRenameAction):
        return f"Rename code symbol {action.symbol} to {action.new_name}"
    if isinstance(action, t.PythonDefinitionsAction):
        return f"Read Python definitions {action.symbol}"
    if isinstance(action, t.CheckReplacePythonDefinitionAction):
        return f"Check replace Python definition {action.symbol}"
    if isinstance(action, t.ReplacePythonDefinitionAction):
        return f"Replace Python definition {action.symbol}"
    if isinstance(action, t.PythonCallsAction):
        return f"Read Python calls {action.symbol}"
    if isinstance(action, t.PythonCallGraphAction):
        return f"Read Python call graph {action.path or '.'}"
    if isinstance(action, t.PythonReferencesAction):
        return f"Find Python references {action.symbol}"
    if isinstance(action, t.PythonReferenceContextsAction):
        return f"Read Python reference contexts {action.symbol}"
    if isinstance(action, t.PythonRenamePreviewAction):
        return f"Preview Python rename {action.symbol} to {action.new_name}"
    if isinstance(action, t.PythonRenameAction):
        return f"Rename Python symbol {action.symbol} to {action.new_name}"
    if isinstance(action, t.SearchAction):
        return f"Search {summarize(action.query, 80)}"
    if isinstance(action, t.SearchContextsAction):
        return f"Search contexts {summarize(action.query, 80)} in {action.path or '.'}"
    if isinstance(action, t.GlobAction):
        return f"Find files {summarize(action.pattern, 80)}"
    if isinstance(action, t.ListTreeAction):
        return f"List tree {action.path or '.'}"
    if isinstance(action, t.GitStatusAction):
        return "Read git status"
    if isinstance(action, t.GitConflictsAction):
        return f"Scan git conflicts {action.path or '.'}"
    if isinstance(action, t.GitDiffContextsAction):
        return f"Read git diff contexts {action.path or '.'}"
    if isinstance(action, t.GitInfoAction):
        return "Read git info"
    if isinstance(action, t.GitChangesAction):
        return "Read git changes"
    if isinstance(action, t.GitBranchesAction):
        return "Read git branches"
    if isinstance(action, t.CheckGitFetchAction):
        return f"Check git fetch {action.remote or 'default remote'}"
    if isinstance(action, t.GitFetchAction):
        return f"Fetch git remote {action.remote or 'default remote'}"
    if isinstance(action, t.CheckGitPullAction):
        return "Check git pull"
    if isinstance(action, t.GitPullAction):
        return "Pull git upstream"
    if isinstance(action, t.CheckGitPushAction):
        return "Check git push"
    if isinstance(action, t.GitPushAction):
        return "Push git upstream"
    if isinstance(action, t.CheckGitRestoreAction):
        return f"Check restore {len(action.paths)} git path(s)"
    if isinstance(action, t.GitRestoreAction):
        return f"Restore {len(action.paths)} git path(s)"
    if isinstance(action, t.GitStashesAction):
        return "Read git stashes"
    if isinstance(action, t.CheckGitStashAction):
        return "Check git stash"
    if isinstance(action, t.GitStashAction):
        return "Stash git changes"
    if isinstance(action, t.CheckGitStashApplyAction):
        return f"Check apply {action.stash_ref}"
    if isinstance(action, t.GitStashApplyAction):
        return f"Apply {action.stash_ref}"
    if isinstance(action, t.CheckGitStashDropAction):
        return f"Check drop {action.stash_ref}"
    if isinstance(action, t.GitStashDropAction):
        return f"Drop {action.stash_ref}"
    if isinstance(action, t.CheckGitSwitchAction):
        return f"Check git switch {action.branch}"
    if isinstance(action, t.GitSwitchAction):
        return f"Switch git branch {action.branch}"
    if isinstance(action, t.CheckGitStageAction):
        return f"Check stage {len(action.paths)} git path(s)"
    if isinstance(action, t.GitStageAction):
        return f"Stage {len(action.paths)} git path(s)"
    if isinstance(action, t.CheckGitUnstageAction):
        return f"Check unstage {len(action.paths)} git path(s)"
    if isinstance(action, t.GitUnstageAction):
        return f"Unstage {len(action.paths)} git path(s)"
    if isinstance(action, t.CheckGitCommitAction):
        return "Check commit staged changes"
    if isinstance(action, t.GitCommitAction):
        return "Commit staged changes"
    if isinstance(action, t.ReviewChangesAction):
        return "Review changes"
    if isinstance(action, t.FinalReviewAction):
        return "Final review"
    if isinstance(action, t.SuggestChecksAction):
        return "Suggest checks"
    if isinstance(action, t.ProjectOverviewAction):
        return "Read project overview"
    if isinstance(action, t.CommandCheckAction):
        return f"Check command {summarize(action.command, 80)}"
    if isinstance(action, t.CheckRunCommandsAction):
        return f"Check {len(action.commands)} commands"
    if isinstance(action, t.CheckStartCommandAction):
        return f"Check start command {summarize(action.command, 80)}"
    if isinstance(action, t.PortCheckAction):
        return f"Check port {action.host}:{action.port}"
    if isinstance(action, t.HttpCheckAction):
        return f"Check HTTP {summarize(action.url, 80)}"
    if isinstance(action, t.HttpFetchAction):
        return f"Fetch HTTP {summarize(action.url, 80)}"
    if isinstance(action, t.CheckStopProcessAction):
        return f"Check stop process {action.process_id}"
    if isinstance(action, t.CheckStopAllProcessesAction):
        return "Check stop all background processes"
    if isinstance(action, t.WaitProcessAction):
        return f"Wait for process {action.process_id}"
    if isinstance(action, t.CheckWriteProcessAction):
        return f"Check process input {action.process_id}"
    if isinstance(action, t.WriteProcessAction):
        return f"Write process input {action.process_id}"
    if isinstance(action, t.EnvironmentInfoAction):
        return "Read environment info"
    if isinstance(action, t.GitDiffAction):
        return f"Read git diff {action.path or '.'}"
    if isinstance(action, t.GitLogAction):
        return f"Read git log {action.path or '.'}"
    if isinstance(action, t.GitShowAction):
        return f"Read git show {action.rev}"
    if isinstance(action, t.GitBlameAction):
        return f"Read git blame {action.path}"
    if isinstance(action, t.SessionSummaryAction):
        return f"Read session summary {action.run_id or 'current'}"
    if isinstance(action, t.SessionPlanAction):
        return f"Read session plan {action.run_id or 'current'}"
    if isinstance(action, t.SessionTranscriptAction):
        return f"Read session transcript {action.run_id or 'current'}"
    if isinstance(action, t.SessionSearchAction):
        return f"Search session {action.run_id or 'current'}"
    if isinstance(action, t.SessionCommandsAction):
        return f"Read session commands {action.run_id or 'current'}"
    if isinstance(action, t.SessionFilesAction):
        return f"Read session files {action.run_id or 'current'}"
    if isinstance(action, t.SessionFailuresAction):
        return f"Read session failures {action.run_id or 'current'}"
    if isinstance(action, t.SessionVerificationAction):
        return f"Read session verification {action.run_id or 'current'}"
    if isinstance(action, t.SessionAuditAction):
        return f"Read session audit {action.run_id or 'current'}"
    if isinstance(action, t.SessionHandoffAction):
        return f"Read session handoff {action.run_id or 'current'}"
    if isinstance(action, t.CheckpointCreateAction):
        return f"Create checkpoint {action.label or ''}".strip()
    if isinstance(action, t.CheckpointListAction):
        return "List checkpoints"
    if isinstance(action, t.CheckpointShowAction):
        return f"Show checkpoint {action.checkpoint_id}"
    if isinstance(action, t.CheckpointDiffAction):
        return f"Read checkpoint diff {action.checkpoint_id}"
    if isinstance(action, t.CheckpointStatusAction):
        return f"Check checkpoint status {action.checkpoint_id}"
    if isinstance(action, t.CheckCheckpointRestoreAction):
        return f"Check checkpoint restore {action.checkpoint_id}"
    if isinstance(action, t.CheckpointRestoreAction):
        return f"Restore checkpoint {action.checkpoint_id}"
    if isinstance(action, t.CheckpointDeleteAction):
        return f"Delete checkpoint {action.checkpoint_id}"
    if isinstance(action, t.CheckCheckpointPruneAction):
        return f"Check checkpoint prune keep {action.keep_last}"
    if isinstance(action, t.CheckpointPruneAction):
        return f"Prune checkpoints keep {action.keep_last}"
    if isinstance(action, t.ListFilesAction):
        return f"List files {action.path or '.'}"
    if getattr(action, "type", None) == "list_files":
        return f"List files {getattr(action, 'path', None) or '.'}"
    if isinstance(action, t.FinishAction):
        return "Finish task"
    return str(getattr(action, "type", "Unknown action"))
