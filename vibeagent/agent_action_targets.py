from __future__ import annotations

from .agent_approval_targets import (
    command_batch_target,
    command_target,
    focused_test_commands_target,
    session_verification_target,
    suggested_checks_target,
)
from .agent_observation_utils import summarize
from . import types as t


def _described_command_target(action: object) -> str:
    target = command_target(getattr(action, "command"), getattr(action, "cwd", None))
    description = getattr(action, "description", None)
    return f"{description}: {target}" if description else target


def _monitor_target(action: t.MonitorAction) -> str:
    target = action.ws.url if action.ws is not None else action.command or "monitor"
    return f"{action.description}: {target}"


def build_action_target(action: object) -> str:
    if isinstance(action, t.ListAgentsAction):
        return "session subagents"
    if isinstance(action, t.SendMessageAction):
        return action.to
    if isinstance(action, (t.CheckMemoryWriteAction, t.MemoryReadAction, t.MemoryWriteAction)):
        return action.path
    if isinstance(action, t.MemoryListAction):
        return "project memory"
    if isinstance(action, t.EnterWorktreeAction):
        return action.path or action.name or "generated isolated worktree"
    if isinstance(action, t.ExitWorktreeAction):
        return "main worktree"
    if isinstance(
        action,
        (
            t.WriteFileAction,
            t.CheckWriteFileAction,
            t.CheckEditFileAction,
            t.EditFileAction,
            t.CheckMultiEditAction,
            t.MultiEditAction,
            t.CheckNotebookEditAction,
            t.NotebookEditAction,
            t.CheckReplaceLinesAction,
            t.CheckPatchAction,
            t.PatchFileAction,
            t.CheckDeleteFileAction,
            t.DeleteFileAction,
            t.ReadFileAction,
            t.NotebookReadAction,
        ),
    ):
        return action.path
    if isinstance(action, (t.CheckDeleteFilesAction, t.DeleteFilesAction)):
        return ", ".join(action.paths)
    if isinstance(action, t.ReplaceLinesAction):
        return f"{action.path}:{action.start_line}-{action.end_line}"
    if isinstance(action, t.CheckInsertLinesAction):
        return f"{action.path}:{action.line}"
    if isinstance(action, t.InsertLinesAction):
        return f"{action.path}:{action.line}"
    if isinstance(action, t.CheckAppendFileAction):
        return action.path
    if isinstance(action, t.AppendFileAction):
        return action.path
    if isinstance(action, t.RegexReplaceAction):
        return action.path
    if isinstance(action, t.CheckRegexReplaceAction):
        return action.path
    if isinstance(action, (t.CheckWriteFilesAction, t.WriteFilesAction)):
        return ", ".join(file.path for file in action.files)
    if isinstance(action, t.ReadFilesAction):
        return ", ".join(action.paths)
    if isinstance(action, t.ReadFileRangesAction):
        return ", ".join(f"{item.path}:{item.start_line}+{item.line_count}" for item in action.ranges)
    if isinstance(action, t.FileInfoAction):
        return ", ".join(action.paths)
    if isinstance(action, t.ImageInfoAction):
        return ", ".join(action.paths)
    if isinstance(action, t.ViewImageAction):
        return action.path
    if isinstance(action, t.PythonSymbolsAction):
        return ", ".join(action.paths)
    if isinstance(action, t.CodeOutlineAction):
        return ", ".join(action.paths)
    if isinstance(action, t.LspQueryAction):
        position = f":{action.line}:{action.character}" if action.line is not None and action.character is not None else ""
        return f"{action.path or action.symbol or '.'}{position}"
    if isinstance(action, t.PythonCheckAction):
        return action.path or "."
    if isinstance(action, t.ConfigCheckAction):
        return action.path or "."
    if isinstance(action, (t.CheckJsonSetAction, t.JsonSetAction, t.CheckJsonRemoveAction, t.JsonRemoveAction)):
        return f"{action.path} {action.pointer}"
    if isinstance(action, (t.CheckJsonPatchAction, t.JsonPatchAction)):
        return f"{action.path} ({len(action.operations)} operations)"
    if isinstance(action, t.PythonDependenciesAction):
        return action.path or "."
    if isinstance(action, t.PythonDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, (t.CheckReplacePythonDefinitionAction, t.ReplacePythonDefinitionAction)):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonCallsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonCallGraphAction):
        return action.path or "."
    if isinstance(action, t.PythonReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonReferenceContextsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.PythonRenamePreviewAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.PythonRenameAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.CheckMultiEditAction):
        return action.path
    if isinstance(action, t.CheckReplaceLinesAction):
        return f"{action.path}:{action.start_line}-{action.end_line}"
    if isinstance(action, (t.CheckPatchesAction, t.PatchFilesAction)):
        return "multiple files"
    if isinstance(action, (t.CheckMoveFileAction, t.MoveFileAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckMoveFilesAction, t.MoveFilesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckCopyFileAction, t.CopyFileAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckCopyFilesAction, t.CopyFilesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckMoveDirectoryAction, t.MoveDirectoryAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckMoveDirectoriesAction, t.MoveDirectoriesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckCopyDirectoryAction, t.CopyDirectoryAction)):
        return f"{action.source} -> {action.destination}"
    if isinstance(action, (t.CheckCopyDirectoriesAction, t.CopyDirectoriesAction)):
        return ", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers)
    if isinstance(action, (t.CheckCreateDirectoryAction, t.CreateDirectoryAction, t.CheckDeleteEmptyDirectoryAction, t.DeleteEmptyDirectoryAction)):
        return action.path
    if isinstance(action, (t.CheckCreateDirectoriesAction, t.CreateDirectoriesAction)):
        return ", ".join(action.paths)
    if isinstance(action, (t.CheckDeleteEmptyDirectoriesAction, t.DeleteEmptyDirectoriesAction)):
        return ", ".join(action.paths)
    if isinstance(action, (t.CheckSetExecutableAction, t.SetExecutableAction)):
        return action.path
    if isinstance(action, t.RunCommandAction):
        return _described_command_target(action)
    if isinstance(action, t.RunCommandsAction):
        return command_batch_target(action.commands)
    if isinstance(action, t.RunSessionVerificationAction):
        return session_verification_target(action.run_id, action.include_failed, action.include_pending)
    if isinstance(action, t.MonitorAction):
        return _monitor_target(action)
    if isinstance(action, t.StartCommandAction):
        return _described_command_target(action)
    if isinstance(action, (t.ReadProcessAction, t.StopProcessAction)):
        return action.process_id
    if isinstance(action, (t.ListProcessesAction, t.CheckStopAllProcessesAction, t.StopAllProcessesAction)):
        return "background processes"
    if isinstance(action, t.RepoMapAction):
        return action.path or "."
    if isinstance(action, t.SearchAction):
        return action.query
    if isinstance(action, t.SearchContextsAction):
        return f"{action.query} in {action.path or '.'}"
    if isinstance(action, t.FindFilesAction):
        return f"{action.query} in {action.path or '.'}"
    if isinstance(action, t.GlobAction):
        return action.pattern
    if isinstance(action, t.ListTreeAction):
        return action.path or "."
    if isinstance(action, t.GitStatusAction):
        return "git status"
    if isinstance(action, t.GitConflictsAction):
        return action.path or "."
    if isinstance(action, t.GitDiffContextsAction):
        return action.path or "."
    if isinstance(action, t.GitInfoAction):
        return "git info"
    if isinstance(action, t.GitChangesAction):
        return "git changes"
    if isinstance(action, t.GitBranchesAction):
        return "git branches"
    if isinstance(action, (t.CheckGitFetchAction, t.GitFetchAction)):
        return action.remote or "default remote"
    if isinstance(action, (t.CheckGitPullAction, t.GitPullAction)):
        return "current branch upstream"
    if isinstance(action, (t.CheckGitPushAction, t.GitPushAction)):
        return "current branch upstream"
    if isinstance(action, (t.CheckGitRestoreAction, t.GitRestoreAction)):
        return ", ".join(action.paths)
    if isinstance(action, t.GitStashesAction):
        return "git stashes"
    if isinstance(action, (t.CheckGitStashAction, t.GitStashAction)):
        return action.message or "vibeagent stash"
    if isinstance(action, (t.CheckGitStashApplyAction, t.GitStashApplyAction, t.CheckGitStashDropAction, t.GitStashDropAction)):
        return action.stash_ref
    if isinstance(action, (t.CheckGitSwitchAction, t.GitSwitchAction)):
        return f"{action.branch}{' (create)' if action.create else ''}"
    if isinstance(action, t.ReviewChangesAction):
        return "changed files"
    if isinstance(action, t.FinalReviewAction):
        return "final review"
    if isinstance(action, t.SuggestChecksAction):
        return "check commands"
    if isinstance(action, t.ProjectCommandsAction):
        return "project commands"
    if isinstance(action, t.ToolSearchAction):
        return action.query
    if isinstance(action, t.RelatedTestsAction):
        return "related tests"
    if isinstance(action, t.FocusedTestCommandsAction):
        return "focused test commands"
    if isinstance(action, (t.CheckFocusedTestCommandsAction, t.RunFocusedTestCommandsAction)):
        return focused_test_commands_target(action.max_commands)
    if isinstance(action, t.ProjectManifestsAction):
        return "project manifests"
    if isinstance(action, t.ProjectInstructionsAction):
        return "project instructions"
    if isinstance(action, t.ProjectSkillsAction):
        return "project skills"
    if isinstance(action, t.SkillAction):
        return action.name
    if isinstance(action, t.McpServersAction):
        return "MCP servers"
    if isinstance(action, t.McpToolsAction):
        return action.server
    if isinstance(action, t.McpResourcesAction):
        return action.server
    if isinstance(action, t.McpReadResourceAction):
        return f"{action.server}/{action.uri}"
    if isinstance(action, t.McpCallAction):
        return f"{action.server}/{action.name}"
    if isinstance(action, t.ProjectOverviewAction):
        return "project overview"
    if isinstance(action, t.CodeDependenciesAction):
        return action.path or "."
    if isinstance(action, t.CodeReferencesAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.CodeReferenceContextsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.CodeDefinitionsAction):
        return f"{action.symbol} in {action.path or '.'}"
    if isinstance(action, t.CodeRenamePreviewAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.CodeRenameAction):
        return f"{action.symbol} -> {action.new_name} in {action.path or '.'}"
    if isinstance(action, t.CommandCheckAction):
        return command_target(action.command, action.cwd)
    if isinstance(action, t.PortCheckAction):
        return f"{action.host}:{action.port}"
    if isinstance(action, t.HttpCheckAction):
        return action.url
    if isinstance(action, t.HttpFetchAction):
        return action.url
    if isinstance(action, t.WebFetchAction):
        return action.url
    if isinstance(action, t.WebSearchAction):
        return action.query
    if isinstance(action, t.EnvironmentInfoAction):
        return "runtime environment"
    if isinstance(action, t.GitDiffAction):
        return action.path or ("staged changes" if action.staged else "working tree")
    if isinstance(action, t.GitDiffHunksAction):
        return action.path or ("staged changes" if action.staged else "working tree")
    if isinstance(action, t.GitLogAction):
        return action.path or f"last {action.max_count} commits"
    if isinstance(action, t.GitShowAction):
        return f"{action.rev}{f' -- {action.path}' if action.path else ''}"
    if isinstance(action, t.GitBlameAction):
        if action.start_line is not None:
            return f"{action.path}:{action.start_line}+{action.line_count or 120}"
        return action.path
    if isinstance(action, (t.CheckGitStageAction, t.GitStageAction, t.CheckGitUnstageAction, t.GitUnstageAction)):
        return ", ".join(action.paths)
    if isinstance(action, (t.CheckGitCommitAction, t.GitCommitAction)):
        return summarize(action.message, 80)
    if isinstance(action, t.MonitorAction):
        return _monitor_target(action)
    if isinstance(action, (t.RunCommandAction, t.CheckStartCommandAction, t.StartCommandAction)):
        return _described_command_target(action)
    if isinstance(action, (t.CheckRunCommandsAction, t.RunCommandsAction)):
        return command_batch_target(action.commands)
    if isinstance(action, (t.CheckSuggestedChecksAction, t.RunSuggestedChecksAction)):
        return suggested_checks_target(action.max_commands)
    if isinstance(action, (t.WaitProcessAction, t.CheckStopProcessAction)):
        return action.process_id
    if isinstance(action, (t.CheckWriteProcessAction, t.WriteProcessAction)):
        if action.stdin_file is not None:
            return f"{action.process_id} (stdin_file: {action.stdin_file})"
        return f"{action.process_id} ({len(action.content or '')} chars)"
    if isinstance(action, t.SessionSummaryAction):
        return action.run_id or "current session"
    if isinstance(action, t.SessionPlanAction):
        return action.run_id or "current session"
    if isinstance(action, t.SessionTranscriptAction):
        return action.run_id or "current session"
    if isinstance(action, (t.SessionVerificationAction, t.SessionAuditAction, t.SessionHandoffAction)):
        return action.run_id or "current session"
    if isinstance(action, t.CheckpointCreateAction):
        return action.label or "checkpoint"
    if isinstance(action, t.CheckpointListAction):
        return "checkpoints"
    if isinstance(action, (t.CheckCheckpointPruneAction, t.CheckpointPruneAction)):
        return f"keep_last={action.keep_last}"
    if isinstance(action, (t.CheckpointShowAction, t.CheckpointDiffAction, t.CheckpointStatusAction, t.CheckCheckpointRestoreAction, t.CheckpointRestoreAction, t.CheckCheckpointDeleteAction, t.CheckpointDeleteAction)):
        return action.checkpoint_id
    if isinstance(action, t.UpdatePlanAction):
        current = next((item.step for item in action.plan if item.status == "in_progress"), None)
        return current or "plan"
    if isinstance(action, t.TaskCreateAction):
        return action.subject
    if isinstance(action, (t.TaskGetAction, t.TaskUpdateAction)):
        return action.task_id
    if isinstance(action, t.TaskListAction):
        return "tasks"
    if isinstance(action, t.AskUserAction):
        return action.question
    if isinstance(action, t.DelegateTaskAction):
        return action.task
    if isinstance(action, (t.TaskOutputAction, t.TaskStopAction)):
        return action.task_id
    if getattr(action, "type", None) == "list_files":
        return str(getattr(action, "path", None) or ".")
    if isinstance(action, t.FinishAction):
        return "finish"
    return ""
