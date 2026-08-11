from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import json
import os
import time

from .agent_hook_execution import run_project_hook
from .session_environment import lifecycle_hook_environment
from .agent_hook_results import HookRunResult
from .agent_hook_prompt import HookModelRuntime
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation
from .workspace_core import RunWorkspace
from .workspace_hooks import HookEvent, ProjectHooks, matching_lifecycle_hooks
from .workspace_hook_types import ProjectHook
from .workspace_instruction_rules import path_is_in_scope, rule_pattern_matches
from .workspace_permissions import ProjectPermissions


CONTEXT_EVENTS = frozenset(
    {"PostToolBatch", "SessionStart", "SubagentStart", "UserPromptSubmit"}
)
BLOCKING_EVENTS = frozenset(
    {
        "PostToolBatch", "Stop", "SubagentStop", "TaskCompleted",
        "TaskCreated", "TeammateIdle", "UserPromptSubmit",
    }
)
ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
SESSION_END_DEFAULT_BUDGET_MS = 1_500
SESSION_END_MAX_BUDGET_MS = 60_000


@dataclass(frozen=True)
class LifecycleHookResult:
    results: tuple[HookRunResult, ...] = ()
    contexts: tuple[str, ...] = ()
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
        output = _parse_hook_output(result)
        if event in CONTEXT_EVENTS and output.context:
            contexts.append(output.context)
        if event in BLOCKING_EVENTS:
            blocking_message = _blocking_message(result, output)
            if blocking_message is not None:
                return LifecycleHookResult(
                    results=tuple(results),
                    contexts=tuple(contexts),
                    blocking_message=blocking_message,
                    halt_turn_message=output.stop_reason,
                )
    return LifecycleHookResult(results=tuple(results), contexts=tuple(contexts))


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


@dataclass(frozen=True)
class _ParsedHookOutput:
    context: str | None = None
    decision: str | None = None
    reason: str | None = None
    plain_text: bool = False
    stop_reason: str | None = None
    continue_: bool | None = None


def _parse_hook_output(result: HookRunResult) -> _ParsedHookOutput:
    if not result.ok or not result.stdout.strip():
        return _ParsedHookOutput()
    stripped = result.stdout.strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return _ParsedHookOutput(context=stripped, plain_text=True)
    if not isinstance(payload, dict):
        return _ParsedHookOutput()
    specific = payload.get("hookSpecificOutput")
    specific_payload = specific if isinstance(specific, dict) else {}
    context = specific_payload.get(
        "additionalContext", payload.get("additionalContext")
    )
    reason = payload.get("reason")
    stop_reason = payload.get("stopReason")
    continue_value = payload.get("continue")
    return _ParsedHookOutput(
        context=context if isinstance(context, str) and context.strip() else None,
        decision=payload.get("decision")
        if isinstance(payload.get("decision"), str)
        else None,
        reason=reason if isinstance(reason, str) and reason.strip() else None,
        stop_reason=(
            stop_reason if isinstance(stop_reason, str) and stop_reason.strip() else None
        ),
        continue_=continue_value if isinstance(continue_value, bool) else None,
    )


def _blocking_message(result: HookRunResult, output: _ParsedHookOutput) -> str | None:
    if result.handler_type in {"prompt", "agent"} and result.status == "blocked":
        return result.message
    if result.exit_code == 2:
        return result.stderr.strip() or result.message
    if output.decision == "block":
        return output.reason or "Configured hook blocked this lifecycle event."
    if output.continue_ is False:
        return output.stop_reason or "Configured hook stopped this lifecycle event."
    if output.context and result.event == "Stop" and not output.plain_text:
        return output.context
    return None


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
