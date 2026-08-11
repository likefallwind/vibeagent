from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import os
import time

from .agent_hook_execution import run_project_hook
from .session_environment import lifecycle_hook_environment
from .agent_hook_results import HookRunResult
from .agent_hook_prompt import HookModelRuntime
from .agent_lifecycle_output import (
    lifecycle_blocking_message,
    parse_lifecycle_hook_output,
)
from .agent_runtime_utils import append_session_event
from .redaction import redact_sensitive_text
from .session_file_watch_state import write_dynamic_watch_paths
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation
from .workspace_core import RunWorkspace
from .workspace_hooks import HookEvent, ProjectHooks, matching_lifecycle_hooks
from .workspace_hook_types import ProjectHook
from .workspace_instruction_rules import path_is_in_scope, rule_pattern_matches
from .workspace_permissions import ProjectPermissions


CONTEXT_EVENTS = frozenset(
    {
        "PostToolBatch",
        "SessionStart",
        "SubagentStart",
        "UserPromptExpansion",
        "UserPromptSubmit",
    }
)
BLOCKING_EVENTS = frozenset(
    {
        "ConfigChange", "PostToolBatch", "Stop", "SubagentStop", "TaskCompleted",
        "TaskCreated", "TeammateIdle", "UserPromptExpansion", "UserPromptSubmit",
    }
)
ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
SESSION_END_DEFAULT_BUDGET_MS = 1_500
SESSION_END_MAX_BUDGET_MS = 60_000


@dataclass(frozen=True)
class LifecycleHookResult:
    results: tuple[HookRunResult, ...] = ()
    contexts: tuple[str, ...] = ()
    system_messages: tuple[str, ...] = ()
    watch_paths: tuple[str, ...] | None = None
    display_content: str | None = None
    blocking_message: str | None = None
    halt_turn_message: str | None = None


def run_lifecycle_hooks(
    workspace: RunWorkspace,
    config: ProjectHooks,
    event: HookEvent,
    matcher_value: str,
    event_fields: dict[str, object],
    *,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
    hook_model_runtime: HookModelRuntime | None = None,
) -> LifecycleHookResult:
    hooks = matching_lifecycle_hooks(config, event, matcher_value)
    if not hooks:
        return LifecycleHookResult()
    hook_input = {
        "session_id": workspace.run_id,
        "transcript_path": str(workspace.session_dir / "events.jsonl"),
        "cwd": str(event_fields.get("new_cwd", workspace.root)),
        "permission_mode": _claude_permission_mode(approval_policy),
        "hook_event_name": event,
        **event_fields,
    }
    results: list[HookRunResult] = []
    contexts: list[str] = []
    system_messages: list[str] = []
    watch_paths: tuple[str, ...] | None = None
    display_content: str | None = None
    session_end_deadline = (
        time.monotonic() + _session_end_budget_ms(hooks) / 1000
        if event == "SessionEnd"
        else None
    )
    for index, hook in enumerate(hooks, start=1):
        if session_end_deadline is not None:
            remaining_ms = round((session_end_deadline - time.monotonic()) * 1000)
            if remaining_ms < 100:
                break
            hook = replace(hook, timeout_ms=min(hook.timeout_ms, remaining_ms))
        result = run_project_hook(
            workspace,
            hook,
            target=matcher_value or event,
            hook_input=hook_input,
            environment=lifecycle_hook_environment(workspace, event),
            cwd=(
                str(event_fields["new_cwd"])
                if event == "CwdChanged" and isinstance(event_fields.get("new_cwd"), str)
                else None
            ),
            iteration=iteration,
            hook_index=index,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            execute_action_safely_func=execute_action_safely_func,
            permissions=permissions,
            hook_model_runtime=hook_model_runtime,
        )
        results.append(result)
        output = parse_lifecycle_hook_output(result)
        if event in CONTEXT_EVENTS and output.context:
            contexts.append(output.context)
        if output.system_message:
            system_messages.append(output.system_message)
        if event == "MessageDisplay" and output.display_content is not None:
            display_content = output.display_content
        if event in {"SessionStart", "CwdChanged", "FileChanged"} and output.watch_paths is not None:
            try:
                stored_paths = write_dynamic_watch_paths(workspace, output.watch_paths)
            except (OSError, ValueError) as error:
                append_session_event(
                    workspace.session_dir,
                    "file_watch_update_rejected",
                    {
                        "event": event,
                        "message": redact_sensitive_text(str(error))[:2_000],
                    },
                )
            else:
                watch_paths = tuple(str(path) for path in stored_paths)
        if event in BLOCKING_EVENTS:
            blocking_message = lifecycle_blocking_message(result, output)
            if blocking_message is not None:
                return LifecycleHookResult(
                    results=tuple(results),
                    contexts=tuple(contexts),
                    system_messages=tuple(system_messages),
                    watch_paths=watch_paths,
                    display_content=display_content,
                    blocking_message=blocking_message,
                    halt_turn_message=output.stop_reason,
                )
    return LifecycleHookResult(
        results=tuple(results),
        contexts=tuple(contexts),
        system_messages=tuple(system_messages),
        watch_paths=watch_paths,
        display_content=display_content,
    )


def run_instruction_loaded_hooks(
    workspace: RunWorkspace,
    config: ProjectHooks,
    instruction_context: dict[str, object],
    *,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
    hook_model_runtime: HookModelRuntime | None = None,
) -> tuple[HookRunResult, ...]:
    results: list[HookRunResult] = []
    raw_trigger_paths = instruction_context.get("paths")
    trigger_paths = (
        [path for path in raw_trigger_paths if isinstance(path, str)]
        if isinstance(raw_trigger_paths, list)
        else []
    )
    files = instruction_context.get("files")
    if not isinstance(files, list):
        return ()
    for source in files:
        if not isinstance(source, dict):
            continue
        relative_path = source.get("path")
        load_reason = source.get("reason")
        if not isinstance(relative_path, str) or not isinstance(load_reason, str):
            continue
        fields: dict[str, object] = {
            "file_path": str((workspace.root / relative_path).resolve()),
            "memory_type": "Local"
            if relative_path.endswith("CLAUDE.local.md")
            else "Project",
            "load_reason": load_reason,
        }
        patterns = source.get("patterns")
        if isinstance(patterns, list) and patterns:
            fields["globs"] = patterns
        parent_path = source.get("parent_path")
        if isinstance(parent_path, str):
            fields["parent_file_path"] = str((workspace.root / parent_path).resolve())
        trigger_path = _matching_trigger_path(source, trigger_paths)
        if isinstance(trigger_path, str):
            fields["trigger_file_path"] = str((workspace.root / trigger_path).resolve())
        batch = run_lifecycle_hooks(
            workspace,
            config,
            "InstructionsLoaded",
            load_reason,
            fields,
            iteration=iteration,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            execute_action_safely_func=execute_action_safely_func,
            permissions=permissions,
            hook_model_runtime=hook_model_runtime,
        )
        results.extend(batch.results)
    return tuple(results)


def _matching_trigger_path(source: dict[str, object], paths: list[str]) -> str | None:
    patterns = source.get("patterns")
    if isinstance(patterns, list) and patterns:
        return next(
            (
                path
                for path in paths
                if any(isinstance(pattern, str) and rule_pattern_matches(pattern, path) for pattern in patterns)
            ),
            None,
        )
    scope = source.get("scope")
    if isinstance(scope, str) and scope != ".":
        return next((path for path in paths if path_is_in_scope(path, scope)), None)
    return paths[0] if paths else None


def _claude_permission_mode(policy: ApprovalPolicy) -> str:
    return {
        "allow": "bypassPermissions",
        "ask": "default",
        "deny": "dontAsk",
        "dontAsk": "dontAsk",
        "plan": "plan",
    }[policy]


def _session_end_budget_ms(hooks: list[ProjectHook]) -> int:
    override = os.environ.get("CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS")
    if override is not None:
        try:
            value = int(override)
        except ValueError:
            value = SESSION_END_DEFAULT_BUDGET_MS
        return max(100, min(value, SESSION_END_MAX_BUDGET_MS))
    configured = max(
        (
            hook.timeout_ms
            for hook in hooks
            if not hook.source.startswith("plugin:")
        ),
        default=SESSION_END_DEFAULT_BUDGET_MS,
    )
    return max(
        SESSION_END_DEFAULT_BUDGET_MS,
        min(configured, SESSION_END_MAX_BUDGET_MS),
    )


__all__ = ["LifecycleHookResult", "run_instruction_loaded_hooks", "run_lifecycle_hooks"]
