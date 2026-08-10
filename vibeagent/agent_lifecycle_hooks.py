from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json

from .agent_hook_execution import run_project_hook_command
from .agent_hook_results import HookRunResult
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation
from .workspace_core import RunWorkspace
from .workspace_hooks import HookEvent, ProjectHooks, matching_lifecycle_hooks
from .workspace_instruction_rules import path_is_in_scope, rule_pattern_matches
from .workspace_permissions import ProjectPermissions


CONTEXT_EVENTS = frozenset({"SessionStart", "UserPromptSubmit"})
BLOCKING_EVENTS = frozenset({"Stop", "UserPromptSubmit"})
ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


@dataclass(frozen=True)
class LifecycleHookResult:
    results: tuple[HookRunResult, ...] = ()
    contexts: tuple[str, ...] = ()
    blocking_message: str | None = None


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
) -> LifecycleHookResult:
    hooks = matching_lifecycle_hooks(config, event, matcher_value)
    if not hooks:
        return LifecycleHookResult()
    hook_input = {
        "session_id": workspace.run_id,
        "transcript_path": str(workspace.session_dir / "events.jsonl"),
        "cwd": str(workspace.root),
        "permission_mode": _claude_permission_mode(approval_policy),
        "hook_event_name": event,
        **event_fields,
    }
    results: list[HookRunResult] = []
    contexts: list[str] = []
    for index, hook in enumerate(hooks, start=1):
        result = run_project_hook_command(
            workspace,
            hook,
            target=matcher_value or event,
            hook_input=hook_input,
            iteration=iteration,
            hook_index=index,
            command_timeout_ms=command_timeout_ms,
            logger=logger,
            approval_handler=approval_handler,
            approval_policy=approval_policy,
            execute_action_safely_func=execute_action_safely_func,
            permissions=permissions,
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
    return _ParsedHookOutput(
        context=context if isinstance(context, str) and context.strip() else None,
        decision=payload.get("decision")
        if isinstance(payload.get("decision"), str)
        else None,
        reason=reason if isinstance(reason, str) and reason.strip() else None,
    )


def _blocking_message(result: HookRunResult, output: _ParsedHookOutput) -> str | None:
    if result.exit_code == 2:
        return result.stderr.strip() or result.message
    if output.decision == "block":
        return output.reason or "Project hook blocked this lifecycle event."
    if output.context and result.event == "Stop" and not output.plain_text:
        return output.context
    return None


def _claude_permission_mode(policy: ApprovalPolicy) -> str:
    return {
        "allow": "bypassPermissions",
        "ask": "default",
        "deny": "dontAsk",
        "plan": "plan",
    }[policy]


__all__ = ["LifecycleHookResult", "run_instruction_loaded_hooks", "run_lifecycle_hooks"]
