from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Literal

from .agent_execution_support import execute_action_safely
from .agent_hook_results import HookRunResult
from .agent_lifecycle_hooks import LifecycleHookResult
from .agent_lifecycle_runtime import AgentLifecycleRuntime
from .file_changed_hooks import FileChangedHookRuntime
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy
from .workspace_core import RunWorkspace, create_local_workspace
from .workspace_hooks import read_project_hooks
from .workspace_permissions import read_project_permissions


SESSION_END_REASONS = frozenset(
    {
        "clear",
        "resume",
        "logout",
        "prompt_input_exit",
        "bypass_permissions_disabled",
        "other",
    }
)


def run_session_end_hooks(
    workspace: RunWorkspace,
    reason: str,
    *,
    command_timeout_ms: int,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    logger: AgentLogger | None = None,
) -> tuple[HookRunResult, ...]:
    if reason not in SESSION_END_REASONS:
        raise ValueError(f"Unsupported SessionEnd reason: {reason}.")
    runtime = _runtime(
        workspace,
        command_timeout_ms=command_timeout_ms,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        logger=logger,
    )
    return tuple(runtime.end(workspace, reason).results)


def run_compact_hooks(
    workspace: RunWorkspace,
    phase: str,
    *,
    trigger: str,
    summary: str | None,
    command_timeout_ms: int,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    logger: AgentLogger | None = None,
) -> None:
    if phase not in {"pre", "post"}:
        raise ValueError(f"Unsupported compact hook phase: {phase}.")
    runtime = _runtime(
        workspace,
        command_timeout_ms=command_timeout_ms,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        logger=logger,
    )
    runtime.compact(workspace, phase, trigger, summary, iteration=0)


def run_interactive_session_hook(
    project_root: Path,
    run_id: str | None,
    pending_workspace: RunWorkspace | None,
    additional_roots: tuple[Path, ...],
    event: Literal["session_end", "pre_compact", "post_compact"],
    value: str,
    *,
    summary: str | None,
    command_timeout_ms: int,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
) -> None:
    workspace = _interactive_workspace(
        project_root,
        run_id,
        pending_workspace,
        additional_roots,
    )
    if workspace is None:
        return
    if event == "session_end":
        run_session_end_hooks(
            workspace,
            value,
            command_timeout_ms=command_timeout_ms,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
        )
        return
    run_compact_hooks(
        workspace,
        "pre" if event == "pre_compact" else "post",
        trigger=value,
        summary=summary,
        command_timeout_ms=command_timeout_ms,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
    )


def run_interactive_notification_hooks(
    project_root: Path,
    run_id: str | None,
    pending_workspace: RunWorkspace | None,
    additional_roots: tuple[Path, ...],
    notification_type: str,
    message: str,
    *,
    title: str | None,
    command_timeout_ms: int,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
) -> LifecycleHookResult:
    workspace = _interactive_workspace(
        project_root,
        run_id,
        pending_workspace,
        additional_roots,
    )
    if workspace is None:
        return LifecycleHookResult()
    runtime = _runtime(
        workspace,
        command_timeout_ms=command_timeout_ms,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        logger=None,
    )
    return runtime.notify(
        workspace,
        notification_type,
        message,
        title=title,
    )


def create_interactive_file_changed_runtime(
    project_root: Path,
    run_id: str | None,
    pending_workspace: RunWorkspace | None,
    additional_roots: tuple[Path, ...],
    *,
    command_timeout_ms: int,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
) -> FileChangedHookRuntime | None:
    workspace = _interactive_workspace(
        project_root,
        run_id,
        pending_workspace,
        additional_roots,
    )
    if workspace is None:
        return None
    runtime = _runtime(
        workspace,
        command_timeout_ms=command_timeout_ms,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        logger=None,
    )
    return FileChangedHookRuntime(workspace, runtime.hooks, runtime)


def _interactive_workspace(
    project_root: Path,
    run_id: str | None,
    pending_workspace: RunWorkspace | None,
    additional_roots: tuple[Path, ...],
) -> RunWorkspace | None:
    if run_id is None:
        return None
    if pending_workspace is not None and pending_workspace.run_id == run_id:
        return replace(pending_workspace, additional_roots=additional_roots)
    return create_local_workspace(
        project_root,
        run_id,
        additional_roots=additional_roots,
    )


def _runtime(
    workspace: RunWorkspace,
    *,
    command_timeout_ms: int,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    logger: AgentLogger | None,
) -> AgentLifecycleRuntime:
    hooks = read_project_hooks(workspace)
    permissions = read_project_permissions(workspace)
    if workspace.project_config_trusted and permissions.enabled:
        permissions = replace(permissions, allow_rules_trusted=True)
    return AgentLifecycleRuntime(
        hooks=hooks,
        permissions=permissions,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        execute_action_safely=execute_action_safely,
    )


__all__ = [
    "SESSION_END_REASONS",
    "create_interactive_file_changed_runtime",
    "run_compact_hooks",
    "run_interactive_notification_hooks",
    "run_interactive_session_hook",
    "run_session_end_hooks",
]
