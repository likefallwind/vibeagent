from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread

from .agent_execution_support import execute_action_safely
from .agent_hook_execution import run_project_hook
from .agent_runtime_utils import append_session_event
from .redaction import redact_sensitive_text
from .session_additional_directories import record_session_additional_directories
from .session_environment import lifecycle_hook_environment
from .types import ApprovalDecision, ApprovalHandler, ApprovalPolicy, ApprovalRequest
from .workspace_core import RunWorkspace, normalize_additional_roots
from .workspace_hooks import ProjectHooks, matching_lifecycle_hooks
from .workspace_permissions import ProjectPermissions


@dataclass(frozen=True)
class DirectoryAddedNotification:
    context: str | None = None
    error: str | None = None


_NOTIFICATIONS: dict[str, Queue[DirectoryAddedNotification]] = {}
_NOTIFICATIONS_LOCK = Lock()
MAX_DIRECTORY_HOOK_CONTEXT_CHARS = 50_000


def schedule_directory_added_hooks(
    workspace: RunWorkspace,
    directory: Path,
    source: str,
    *,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    approval_policy: ApprovalPolicy,
    approval_handler: ApprovalHandler | None,
    command_timeout_ms: int = 600_000,
) -> int:
    matched = matching_lifecycle_hooks(hooks, "DirectoryAdded", source)
    approved = []
    for hook in matched:
        if _approve_schedule(hook.handler_target, approval_policy, approval_handler):
            approved.append(hook)
            continue
        append_session_event(
            workspace.session_dir,
            "directory_added_hook_denied",
            {"directory": str(directory.resolve()), "source": source, "target": hook.handler_target},
        )
    if not approved:
        return 0
    append_session_event(
        workspace.session_dir,
        "directory_added_hooks_scheduled",
        {"directory": str(directory.resolve()), "source": source, "count": len(approved)},
    )
    Thread(
        target=_run_hooks,
        args=(
            workspace,
            directory.resolve(),
            source,
            tuple(approved),
            permissions,
            approval_policy,
            command_timeout_ms,
        ),
        daemon=True,
        name=f"vibeagent-directory-added-{workspace.run_id}",
    ).start()
    return len(approved)


def collect_directory_added_notifications(workspace: RunWorkspace) -> list[DirectoryAddedNotification]:
    with _NOTIFICATIONS_LOCK:
        queue = _NOTIFICATIONS.get(_key(workspace))
    if queue is None:
        return []
    selected: list[DirectoryAddedNotification] = []
    while True:
        try:
            selected.append(queue.get_nowait())
        except Empty:
            break
    return selected


def collect_directory_added_turn_context(
    workspace: RunWorkspace,
    append_system_prompt: str | None,
) -> tuple[str | None, tuple[str, ...]]:
    notifications = collect_directory_added_notifications(workspace)
    contexts = [item.context for item in notifications if item.context]
    errors = tuple(item.error for item in notifications if item.error)
    directory_context = (
        "DirectoryAdded hook context:\n" + "\n\n".join(contexts)
        if contexts
        else None
    )
    prompt = "\n\n".join(
        value for value in (append_system_prompt, directory_context) if value
    ) or None
    return prompt, errors


def register_repo_root(
    workspace: RunWorkspace,
    directory: str | Path,
    **hook_options,
) -> RunWorkspace:
    candidate = Path(directory).expanduser().resolve()
    updated = normalize_additional_roots(workspace.root, (*workspace.additional_roots, candidate))
    if updated == workspace.additional_roots:
        raise ValueError(f"Working directory is already available: {candidate}")
    registered = replace(workspace, additional_roots=updated)
    record_session_additional_directories(
        registered.root,
        registered.run_id,
        registered.additional_roots,
    )
    schedule_directory_added_hooks(
        registered, candidate, "register_repo_root", **hook_options
    )
    return registered


def _approve_schedule(
    target: str,
    policy: ApprovalPolicy,
    handler: ApprovalHandler | None,
) -> bool:
    if policy == "allow":
        return True
    if policy in {"deny", "dontAsk", "plan"} or handler is None:
        return False
    decision = handler(
        ApprovalRequest(
            action_type="directory_added_hook",
            target=target,
            risk="This configured hook will run in the background for a newly added directory.",
        )
    )
    return decision.approved


def _run_hooks(workspace, directory, source, hooks, permissions, approval_policy, timeout):
    with _NOTIFICATIONS_LOCK:
        queue = _NOTIFICATIONS.setdefault(_key(workspace), Queue())
    fields = {
        "session_id": workspace.run_id,
        "transcript_path": str(workspace.session_dir / "events.jsonl"),
        "cwd": str(workspace.root),
        "permission_mode": _permission_mode(approval_policy, permissions),
        "hook_event_name": "DirectoryAdded",
        "directory": str(directory),
        "source": source,
    }
    for index, hook in enumerate(hooks, start=1):
        result = run_project_hook(
            workspace,
            replace(hook, async_=False, async_rewake=False),
            target=source,
            hook_input=fields,
            environment=lifecycle_hook_environment(workspace, "DirectoryAdded"),
            iteration=0,
            hook_index=index,
            command_timeout_ms=timeout,
            logger=None,
            approval_handler=lambda _request: ApprovalDecision(
                approved=True,
                message="Pre-approved DirectoryAdded hook.",
            ),
            approval_policy="allow",
            execute_action_safely_func=execute_action_safely,
            permissions=permissions,
        )
        context = _system_message(result.stdout) if result.ok and source == "slash_command" else None
        if context:
            queue.put(DirectoryAddedNotification(context=context))
        elif not result.ok and source == "slash_command":
            queue.put(DirectoryAddedNotification(error=result.message))


def _key(workspace: RunWorkspace) -> str:
    return str(workspace.root.resolve())


def _system_message(stdout: str) -> str | None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("systemMessage")
    if not isinstance(value, str) or not value.strip():
        return None
    return redact_sensitive_text(value.strip())[:MAX_DIRECTORY_HOOK_CONTEXT_CHARS]


def _permission_mode(policy: ApprovalPolicy, permissions: ProjectPermissions) -> str:
    if permissions.default_mode is not None:
        return permissions.default_mode
    return {
        "allow": "bypassPermissions",
        "ask": "default",
        "auto": "auto",
        "deny": "dontAsk",
        "dontAsk": "dontAsk",
        "plan": "plan",
    }[policy]


__all__ = [
    "DirectoryAddedNotification",
    "collect_directory_added_notifications",
    "collect_directory_added_turn_context",
    "register_repo_root",
    "schedule_directory_added_hooks",
]
