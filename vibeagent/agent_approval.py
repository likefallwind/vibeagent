from __future__ import annotations

import json

from .agent_approval_targets import (
    command_batch_target,
    command_target,
    focused_test_commands_target,
    session_verification_target,
    suggested_checks_target,
)
from .agent_file_approval import build_file_approval_request
from .agent_observation_utils import summarize
from .redaction import redact_jsonable_payload
from . import types as t


def _with_command_description(risk: str, description: str | None) -> str:
    if not description:
        return risk
    return f"{risk} Purpose: {description}"


def build_approval_request(action: object) -> t.ApprovalRequest | None:
    file_request = build_file_approval_request(action)
    if file_request is not None:
        return file_request
    if isinstance(action, t.MemoryWriteAction):
        return t.ApprovalRequest(
            action_type="memory_write",
            target=f"{action.path} ({action.mode}, {len(action.content.encode('utf-8'))} bytes)",
            risk="This will persist durable memory in the store configured for the current agent context.",
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
    if isinstance(action, t.EnterWorktreeAction):
        return t.ApprovalRequest(
            action_type="enter_worktree",
            target=action.path or action.name or "generated isolated worktree",
            risk="This will create git metadata and switch subsequent agent tools into an isolated worktree.",
        )
    if isinstance(action, t.DelegateTaskAction) and action.teammate_name is not None:
        return t.ApprovalRequest(
            action_type="spawn_teammate",
            target=action.teammate_name,
            risk="This starts an independent background agent with the current session's permissions and shared task list.",
        )
    if isinstance(action, t.DelegateTaskAction) and action.isolation == "worktree":
        return t.ApprovalRequest(
            action_type="delegate_task_worktree",
            target=summarize(action.task, 120),
            risk="This will create and lock an isolated git worktree for the delegated task.",
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
            risk=_with_command_description(
                "This will run a shell command from the active project directory.",
                action.description,
            ),
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
            risk=_with_command_description(
                "This will start a background shell command from the active project directory.",
                action.description,
            ),
        )
    if isinstance(action, t.WriteProcessAction):
        target = (
            f"{action.process_id} (stdin_file: {action.stdin_file})"
            if action.stdin_file is not None
            else f"{action.process_id} ({len(action.content or '')} chars)"
        )
        return t.ApprovalRequest(
            action_type="write_process",
            target=target,
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
    if isinstance(action, t.WebSearchAction):
        filters = []
        if action.allowed_domains:
            filters.append(f"allowed={','.join(action.allowed_domains)}")
        if action.blocked_domains:
            filters.append(f"blocked={','.join(action.blocked_domains)}")
        suffix = f" ({'; '.join(filters)})" if filters else ""
        return t.ApprovalRequest(
            action_type="web_search",
            target=f"{action.query}{suffix}",
            risk="This will send the search query to an external public search service and return bounded results.",
        )
    if isinstance(action, t.McpToolsAction):
        return t.ApprovalRequest(
            action_type="mcp_tools",
            target=action.server,
            risk="This will start the configured MCP server process and request its tool catalog.",
        )
    if isinstance(action, t.McpCallAction):
        arguments = summarize(json.dumps(redact_jsonable_payload(action.arguments), ensure_ascii=False), 500)
        return t.ApprovalRequest(
            action_type="mcp_call",
            target=f"{action.server}/{action.name} arguments={arguments}",
            risk="This will start configured code and send the provided arguments to an MCP tool, which may have external side effects.",
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
