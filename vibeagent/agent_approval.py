from __future__ import annotations

import json

from .agent_approval_targets import (
    command_batch_target,
    command_target,
    focused_test_commands_target,
    session_verification_target,
    suggested_checks_target,
)
from .agent_observation_utils import summarize
from .redaction import redact_jsonable_payload
from . import types as t


def build_approval_request(action: object) -> t.ApprovalRequest | None:
    if isinstance(action, t.WriteFileAction):
        return t.ApprovalRequest(
            action_type="write_file",
            target=action.path,
            risk="This will create or replace a file in the active project.",
        )
    if isinstance(action, t.WriteFilesAction):
        return t.ApprovalRequest(
            action_type="write_files",
            target=", ".join(file.path for file in action.files),
            risk="This will create or replace multiple files in the active project.",
        )
    if isinstance(action, t.EditFileAction):
        return t.ApprovalRequest(
            action_type="edit_file",
            target=action.path,
            risk="This will modify an existing file in the active project.",
        )
    if isinstance(action, t.MultiEditAction):
        return t.ApprovalRequest(
            action_type="multi_edit_file",
            target=action.path,
            risk="This will apply multiple exact replacements to an existing file in the active project.",
        )
    if isinstance(action, t.ReplacePythonDefinitionAction):
        return t.ApprovalRequest(
            action_type="replace_python_definition",
            target=f"{action.symbol} in {action.path or '.'}",
            risk="This will replace a full Python class/function definition in the active project.",
        )
    if isinstance(action, t.PythonRenameAction):
        return t.ApprovalRequest(
            action_type="python_rename",
            target=f"{action.symbol} -> {action.new_name} in {action.path or '.'}",
            risk="This will rename Python identifiers across matching project files.",
        )
    if isinstance(action, t.CodeRenameAction):
        return t.ApprovalRequest(
            action_type="code_rename",
            target=f"{action.symbol} -> {action.new_name} in {action.path or '.'}",
            risk="This will rename non-Python source symbols or literals across matching project files.",
        )
    if isinstance(action, t.ReplaceLinesAction):
        return t.ApprovalRequest(
            action_type="replace_lines",
            target=f"{action.path}:{action.start_line}-{action.end_line}",
            risk="This will replace a line range in an existing file in the active project.",
        )
    if isinstance(action, t.InsertLinesAction):
        return t.ApprovalRequest(
            action_type="insert_lines",
            target=f"{action.path}:{action.line}",
            risk="This will insert text into an existing file in the active project.",
        )
    if isinstance(action, t.AppendFileAction):
        return t.ApprovalRequest(
            action_type="append_file",
            target=action.path,
            risk="This will append text to an existing file in the active project.",
        )
    if isinstance(action, t.RegexReplaceAction):
        return t.ApprovalRequest(
            action_type="regex_replace",
            target=action.path,
            risk="This will apply a regular expression replacement to an existing file in the active project.",
        )
    if isinstance(action, t.JsonSetAction):
        return t.ApprovalRequest(
            action_type="json_set",
            target=f"{action.path} {action.pointer}",
            risk="This will update one value in an existing JSON file in the active project.",
        )
    if isinstance(action, t.JsonRemoveAction):
        return t.ApprovalRequest(
            action_type="json_remove",
            target=f"{action.path} {action.pointer}",
            risk="This will remove one value from an existing JSON file in the active project.",
        )
    if isinstance(action, t.JsonPatchAction):
        return t.ApprovalRequest(
            action_type="json_patch",
            target=f"{action.path} ({len(action.operations)} operations)",
            risk="This will apply multiple JSON changes to an existing JSON file in the active project.",
        )
    if isinstance(action, t.PatchFileAction):
        return t.ApprovalRequest(
            action_type="patch_file",
            target=action.path,
            risk="This will apply a unified diff patch to an existing file in the active project.",
        )
    if isinstance(action, t.PatchFilesAction):
        return t.ApprovalRequest(
            action_type="patch_files",
            target="multiple files",
            risk="This will apply a multi-file unified diff patch to files in the active project.",
        )
    if isinstance(action, t.DeleteFileAction):
        return t.ApprovalRequest(
            action_type="delete_file",
            target=action.path,
            risk="This will delete an existing file in the active project.",
        )
    if isinstance(action, t.DeleteFilesAction):
        return t.ApprovalRequest(
            action_type="delete_files",
            target=", ".join(action.paths),
            risk="This will delete explicit existing files in the active project.",
        )
    if isinstance(action, t.MoveFileAction):
        return t.ApprovalRequest(
            action_type="move_file",
            target=f"{action.source} -> {action.destination}",
            risk="This will move or rename an existing file in the active project.",
        )
    if isinstance(action, t.MoveFilesAction):
        return t.ApprovalRequest(
            action_type="move_files",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will move or rename explicit existing files in the active project.",
        )
    if isinstance(action, t.CopyFileAction):
        return t.ApprovalRequest(
            action_type="copy_file",
            target=f"{action.source} -> {action.destination}",
            risk="This will copy an existing file to a new path in the active project.",
        )
    if isinstance(action, t.CopyFilesAction):
        return t.ApprovalRequest(
            action_type="copy_files",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will copy explicit existing files to new paths in the active project.",
        )
    if isinstance(action, t.MoveDirectoryAction):
        return t.ApprovalRequest(
            action_type="move_dir",
            target=f"{action.source} -> {action.destination}",
            risk="This will move or rename an existing directory in the active project.",
        )
    if isinstance(action, t.MoveDirectoriesAction):
        return t.ApprovalRequest(
            action_type="move_dirs",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will move or rename one or more existing directories in the active project.",
        )
    if isinstance(action, t.CopyDirectoryAction):
        return t.ApprovalRequest(
            action_type="copy_dir",
            target=f"{action.source} -> {action.destination}",
            risk="This will copy an existing directory tree in the active project.",
        )
    if isinstance(action, t.CopyDirectoriesAction):
        return t.ApprovalRequest(
            action_type="copy_dirs",
            target=", ".join(f"{transfer.source} -> {transfer.destination}" for transfer in action.transfers),
            risk="This will copy one or more existing directory trees in the active project.",
        )
    if isinstance(action, t.CreateDirectoryAction):
        return t.ApprovalRequest(
            action_type="create_dir",
            target=action.path,
            risk="This will create a directory in the active project.",
        )
    if isinstance(action, t.CreateDirectoriesAction):
        return t.ApprovalRequest(
            action_type="create_dirs",
            target=", ".join(action.paths),
            risk="This will create one or more directories in the active project.",
        )
    if isinstance(action, t.DeleteEmptyDirectoryAction):
        return t.ApprovalRequest(
            action_type="delete_empty_dir",
            target=action.path,
            risk="This will delete one empty directory in the active project.",
        )
    if isinstance(action, t.DeleteEmptyDirectoriesAction):
        return t.ApprovalRequest(
            action_type="delete_empty_dirs",
            target=", ".join(action.paths),
            risk="This will delete one or more empty directories in the active project.",
        )
    if isinstance(action, t.SetExecutableAction):
        state = "add executable bits to" if action.executable else "remove executable bits from"
        return t.ApprovalRequest(
            action_type="set_executable",
            target=action.path,
            risk=f"This will {state} one file in the active project.",
        )
    if isinstance(action, t.GitStageAction):
        return t.ApprovalRequest(
            action_type="git_stage",
            target=", ".join(action.paths),
            risk="This will modify the git index by staging project paths.",
        )
    if isinstance(action, t.GitUnstageAction):
        return t.ApprovalRequest(
            action_type="git_unstage",
            target=", ".join(action.paths),
            risk="This will modify the git index by unstaging project paths.",
        )
    if isinstance(action, t.GitCommitAction):
        return t.ApprovalRequest(
            action_type="git_commit",
            target=summarize(action.message, 120),
            risk="This will create a local git commit from currently staged changes without running git hooks.",
        )
    if isinstance(action, t.GitSwitchAction):
        return t.ApprovalRequest(
            action_type="git_switch",
            target=f"{action.branch}{' (create)' if action.create else ''}",
            risk="This will change the current git branch in the active project.",
        )
    if isinstance(action, t.GitFetchAction):
        return t.ApprovalRequest(
            action_type="git_fetch",
            target=action.remote or "default remote",
            risk="This will contact a git remote and update local remote-tracking refs.",
        )
    if isinstance(action, t.GitPullAction):
        return t.ApprovalRequest(
            action_type="git_pull",
            target="current branch upstream",
            risk="This will contact the git remote and fast-forward the current branch.",
        )
    if isinstance(action, t.GitPushAction):
        return t.ApprovalRequest(
            action_type="git_push",
            target="current branch upstream",
            risk="This will contact the git remote and push local commits to the configured upstream.",
        )
    if isinstance(action, t.GitRestoreAction):
        return t.ApprovalRequest(
            action_type="git_restore",
            target=", ".join(action.paths),
            risk="This will discard unstaged changes in tracked project files.",
        )
    if isinstance(action, t.GitStashAction):
        return t.ApprovalRequest(
            action_type="git_stash",
            target=action.message or "vibeagent stash",
            risk="This will move current project changes into the git stash.",
        )
    if isinstance(action, t.GitStashApplyAction):
        return t.ApprovalRequest(
            action_type="git_stash_apply",
            target=action.stash_ref,
            risk="This will apply a git stash entry to the current worktree.",
        )
    if isinstance(action, t.GitStashDropAction):
        return t.ApprovalRequest(
            action_type="git_stash_drop",
            target=action.stash_ref,
            risk="This will permanently remove a git stash entry.",
        )
    if isinstance(action, t.CheckpointRestoreAction):
        return t.ApprovalRequest(
            action_type="checkpoint_restore",
            target=action.checkpoint_id,
            risk="This will discard current tracked staged and unstaged changes, then restore tracked changes and saved untracked file contents from a checkpoint.",
        )
    if isinstance(action, t.CheckpointDeleteAction):
        return t.ApprovalRequest(
            action_type="checkpoint_delete",
            target=action.checkpoint_id,
            risk="This will permanently delete one saved checkpoint snapshot from the local runtime directory.",
        )
    if isinstance(action, t.CheckpointPruneAction):
        return t.ApprovalRequest(
            action_type="checkpoint_prune",
            target=f"keep_last={action.keep_last}",
            risk="This will permanently delete older saved checkpoint snapshots from the local runtime directory.",
        )
    if isinstance(action, t.RunCommandAction):
        return t.ApprovalRequest(
            action_type="run_command",
            target=command_target(action.command, action.cwd),
            risk="This will run a shell command from the active project directory.",
        )
    if isinstance(action, t.RunCommandsAction):
        return t.ApprovalRequest(
            action_type="run_commands",
            target=command_batch_target(action.commands),
            risk="This will run several shell commands sequentially from the active project directory.",
        )
    if isinstance(action, t.RunSuggestedChecksAction):
        return t.ApprovalRequest(
            action_type="run_suggested_checks",
            target=suggested_checks_target(action.max_commands),
            risk="This will discover and run project test/build/lint check commands from the active project directory.",
        )
    if isinstance(action, t.RunFocusedTestCommandsAction):
        return t.ApprovalRequest(
            action_type="run_focused_test_commands",
            target=focused_test_commands_target(action.max_commands),
            risk="This will discover and run focused project test commands from the active project directory.",
        )
    if isinstance(action, t.RunSessionVerificationAction):
        return t.ApprovalRequest(
            action_type="run_session_verification",
            target=session_verification_target(action.run_id, action.include_failed, action.include_pending),
            risk="This will rerun verification shell commands recorded in a local session from the active project directory.",
        )
    if isinstance(action, t.StartCommandAction):
        return t.ApprovalRequest(
            action_type="start_command",
            target=command_target(action.command, action.cwd),
            risk="This will start a background shell command from the active project directory.",
        )
    if isinstance(action, t.WriteProcessAction):
        return t.ApprovalRequest(
            action_type="write_process",
            target=f"{action.process_id} ({len(action.content)} chars)",
            risk="This will write input to a running background process.",
        )
    if isinstance(action, t.StopProcessAction):
        return t.ApprovalRequest(
            action_type="stop_process",
            target=action.process_id,
            risk="This will stop a background process started from the active project.",
        )
    if isinstance(action, t.StopAllProcessesAction):
        return t.ApprovalRequest(
            action_type="stop_all_processes",
            target="background processes",
            risk="This will stop all background processes started from the active project.",
        )
    if isinstance(action, t.WebFetchAction):
        return t.ApprovalRequest(
            action_type="web_fetch",
            target=action.url,
            risk="This will send a request to an external public server and return bounded document text.",
        )
    if isinstance(action, t.McpToolsAction):
        return t.ApprovalRequest(
            action_type="mcp_tools",
            target=action.server,
            risk="This will start the project-configured MCP server process and request its tool catalog.",
        )
    if isinstance(action, t.McpCallAction):
        arguments = summarize(json.dumps(redact_jsonable_payload(action.arguments), ensure_ascii=False), 500)
        return t.ApprovalRequest(
            action_type="mcp_call",
            target=f"{action.server}/{action.name} arguments={arguments}",
            risk="This will start project-configured code and send the provided arguments to an MCP tool, which may have external side effects.",
        )
    return None


def request_approval(handler: t.ApprovalHandler | None, request: t.ApprovalRequest) -> t.ApprovalDecision:
    if handler is None:
        return t.ApprovalDecision(approved=False, message="No approval handler configured.")
    return handler(request)


def summarize_approval_request(request: t.ApprovalRequest) -> str:
    suffix = " (previewed)" if request.preview else ""
    return f"{request.action_type} {summarize(request.target, 120)}{suffix}"


def summarize_approval_decision(request: t.ApprovalRequest, decision: t.ApprovalDecision) -> str:
    message = decision.message or ("approved" if decision.approved else "denied")
    return f"{request.action_type} {summarize(request.target, 80)}: {summarize(message, 120)}"
