from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from .agent_execution_support import execute_action_safely
from .agent_hook_execution import run_project_hook
from .agent_hook_results import HookRunResult
from .session_environment import lifecycle_hook_environment
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks, matching_lifecycle_hooks
from .workspace_permissions import ProjectPermissions


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@dataclass(frozen=True)
class WorktreeHookContext:
    hooks: ProjectHooks
    permissions: ProjectPermissions
    approval_policy: ApprovalPolicy
    approval_handler: ApprovalHandler | None
    command_timeout_ms: int
    logger: AgentLogger | None = None


@dataclass(frozen=True)
class WorktreeCreateHookResult:
    configured: bool
    path: Path | None = None
    results: tuple[HookRunResult, ...] = ()
    error: str | None = None


def run_worktree_create_hook(
    workspace: RunWorkspace, name: str, context: WorktreeHookContext | None
) -> WorktreeCreateHookResult:
    hooks = _matching(context, "WorktreeCreate")
    if not hooks:
        return WorktreeCreateHookResult(configured=False)
    if len(hooks) != 1:
        return WorktreeCreateHookResult(
            configured=True, error="WorktreeCreate requires exactly one configured handler."
        )
    result = _run(workspace, hooks[0], {"name": name}, context)
    if not result.ok:
        return WorktreeCreateHookResult(True, results=(result,), error=result.message)
    raw_path = _returned_path(result)
    if raw_path is None:
        return WorktreeCreateHookResult(
            True, results=(result,), error="WorktreeCreate hook did not return a worktree path."
        )
    try:
        path = _validate_returned_path(workspace.root, raw_path)
    except ValueError as error:
        return WorktreeCreateHookResult(True, results=(result,), error=str(error))
    return WorktreeCreateHookResult(True, path, (result,))


def run_worktree_remove_hooks(
    workspace: RunWorkspace, worktree_path: str, context: WorktreeHookContext | None
) -> tuple[HookRunResult, ...]:
    return tuple(
        _run(workspace, hook, {"worktree_path": worktree_path}, context)
        for hook in _matching(context, "WorktreeRemove")
    )


def _matching(context: WorktreeHookContext | None, event: str):
    if context is None:
        return []
    return matching_lifecycle_hooks(context.hooks, event, "")


def _run(workspace, hook, fields, context):
    assert context is not None
    hook_input = {
        "session_id": workspace.run_id,
        "transcript_path": str(workspace.session_dir / "events.jsonl"),
        "cwd": str(workspace.root),
        "permission_mode": {
            "allow": "bypassPermissions", "ask": "default", "auto": "auto", "deny": "dontAsk",
            "dontAsk": "dontAsk", "plan": "plan",
        }[context.approval_policy],
        "hook_event_name": hook.event,
        **fields,
    }
    return run_project_hook(
        workspace, hook, target=hook.event, hook_input=hook_input,
        environment=lifecycle_hook_environment(workspace, hook.event),
        iteration=0, hook_index=1, command_timeout_ms=context.command_timeout_ms,
        logger=context.logger, approval_handler=context.approval_handler,
        approval_policy=context.approval_policy,
        execute_action_safely_func=execute_action_safely,
        permissions=context.permissions,
    )


def _returned_path(result: HookRunResult) -> str | None:
    if result.handler_type == "http":
        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError):
            return None
        specific = payload.get("hookSpecificOutput") if isinstance(payload, dict) else None
        value = specific.get("worktreePath") if isinstance(specific, dict) else None
        return value.strip() if isinstance(value, str) and value.strip() else None
    lines = [ANSI_ESCAPE.sub("", line).strip() for line in result.stdout.splitlines()]
    return next((line for line in reversed(lines) if line), None)


def _validate_returned_path(cwd: Path, value: str) -> Path:
    raw = Path(value).expanduser()
    if raw.is_absolute() and ".." in raw.parts:
        raise ValueError("WorktreeCreate hook returned an absolute path containing '..'.")
    candidate = raw if raw.is_absolute() else cwd / raw
    current = Path(candidate.anchor) if candidate.is_absolute() else cwd
    for part in candidate.parts[1:] if candidate.is_absolute() else candidate.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"WorktreeCreate hook path contains a symbolic link: {current}")
    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise ValueError(f"WorktreeCreate hook path is not a directory: {resolved}")
    return resolved


__all__ = ["WorktreeHookContext", "run_worktree_create_hook", "run_worktree_remove_hooks"]
