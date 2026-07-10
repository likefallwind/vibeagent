from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import dataclass

from .agent_action_targets import build_action_target
from .agent_permissions import authorize_tool_action
from .agent_observation_utils import observation_failed, summarize
from .agent_runtime_utils import append_session_event
from .redaction import redact_jsonable_payload
from .types import (
    AgentLogger,
    ApprovalDecision,
    ApprovalHandler,
    ApprovalPolicy,
    ApprovalRequest,
    Observation,
    RunCommandAction,
    RunCommandObservation,
    ToolErrorObservation,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import HookEvent, ProjectHook, ProjectHooks, matching_project_hooks
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
ExecuteTool = Callable[[], Observation]


@dataclass(frozen=True)
class HookRunResult:
    event: HookEvent
    command: str
    source: str
    status: str
    ok: bool
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    message: str


@dataclass(frozen=True)
class HookBatchResult:
    results: tuple[HookRunResult, ...] = ()
    blocking_message: str | None = None
    failures: tuple[ToolErrorObservation, ...] = ()


@dataclass(frozen=True)
class HookWrappedToolResult:
    observation: Observation
    hook_results: tuple[HookRunResult, ...] = ()
    additional_observations: tuple[Observation, ...] = ()


def run_hooks_around_tool(
    workspace: RunWorkspace,
    config: ProjectHooks,
    tool_name: str,
    action: object,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    execute_tool: ExecuteTool,
    permissions: ProjectPermissions = ProjectPermissions(),
) -> HookWrappedToolResult:
    authorization = authorize_tool_action(
        workspace,
        permissions,
        tool_name,
        action,
        iteration,
        approval_handler,
        approval_policy,
        logger,
    )
    if not authorization.allowed:
        assert authorization.denial is not None
        return HookWrappedToolResult(observation=authorization.denial)

    pre_hooks = run_tool_hooks(
        workspace,
        config,
        "PreToolUse",
        tool_name,
        action,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        approval_policy,
        execute_action_safely_func,
        permissions,
    )
    if pre_hooks.blocking_message is not None:
        return HookWrappedToolResult(
            observation=pre_hooks.failures[-1],
            hook_results=pre_hooks.results,
        )

    observation = execute_tool()
    post_event: HookEvent = "PostToolUseFailure" if observation_failed(observation) else "PostToolUse"
    post_hooks = run_tool_hooks(
        workspace,
        config,
        post_event,
        tool_name,
        action,
        iteration,
        command_timeout_ms,
        logger,
        approval_handler,
        approval_policy,
        execute_action_safely_func,
        permissions,
    )
    return HookWrappedToolResult(
        observation=observation,
        hook_results=pre_hooks.results + post_hooks.results,
        additional_observations=post_hooks.failures,
    )


def run_tool_hooks(
    workspace: RunWorkspace,
    config: ProjectHooks,
    event: HookEvent,
    tool_name: str,
    action: object,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions = ProjectPermissions(),
) -> HookBatchResult:
    if config.error is not None:
        message = f"Project hook configuration is invalid: {config.error}"
        failure = _hook_failure_observation(event, tool_name, message)
        return HookBatchResult(blocking_message=message if event == "PreToolUse" else None, failures=(failure,))

    hooks = matching_project_hooks(config, event, tool_name)
    if not hooks:
        return HookBatchResult()
    results: list[HookRunResult] = []
    failures: list[ToolErrorObservation] = []
    for index, hook in enumerate(hooks, start=1):
        result = _run_one_hook(
            workspace,
            hook,
            tool_name,
            action,
            iteration,
            index,
            command_timeout_ms,
            logger,
            approval_handler,
            approval_policy,
            execute_action_safely_func,
            permissions,
        )
        results.append(result)
        if not result.ok:
            failure = _hook_failure_observation(event, tool_name, result.message)
            failures.append(failure)
            if event == "PreToolUse":
                return HookBatchResult(
                    results=tuple(results),
                    blocking_message=result.message,
                    failures=tuple(failures),
                )
    return HookBatchResult(results=tuple(results), failures=tuple(failures))


def _run_one_hook(
    workspace: RunWorkspace,
    hook: ProjectHook,
    tool_name: str,
    action: object,
    iteration: int,
    hook_index: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
) -> HookRunResult:
    event_payload = {
        "iteration": iteration,
        "index": hook_index,
        "event": hook.event,
        "tool": tool_name,
        "source": hook.source,
        "matcher": hook.matcher,
        "command": hook.command,
    }
    if approval_policy == "plan":
        result = HookRunResult(
            event=hook.event,
            command=hook.command,
            source=hook.source,
            status="skipped",
            ok=True,
            exit_code=None,
            timed_out=False,
            stdout="",
            stderr="",
            message="Hook skipped because Plan mode does not run commands.",
        )
        append_session_event(workspace.session_dir, "hook_skipped", {**event_payload, "result": result})
        return result

    request = ApprovalRequest(
        action_type="run_command",
        target=f"{hook.event} hook for {tool_name}: {hook.command}",
        risk="This project hook will run a shell command in the active project.",
    )
    append_session_event(workspace.session_dir, "hook_approval_requested", {**event_payload, "request": request})
    hook_action = RunCommandAction(
        type="run_command",
        command=hook.command,
        timeout_ms=min(hook.timeout_ms, command_timeout_ms),
        max_output_chars=4_000,
    )
    authorization = authorize_tool_action(
        workspace,
        permissions,
        "run_command",
        hook_action,
        iteration,
        approval_handler,
        approval_policy,
        logger,
        default_request=request,
    )
    decision = authorization.decision or ApprovalDecision(
        approved=authorization.allowed,
        message=(
            "Hook command authorized."
            if authorization.allowed
            else getattr(authorization.denial, "message", "Hook command denied by project permissions.")
        ),
    )
    append_session_event(workspace.session_dir, "hook_approval_decision", {**event_payload, "decision": decision})
    if not authorization.allowed:
        result = HookRunResult(
            event=hook.event,
            command=hook.command,
            source=hook.source,
            status="denied",
            ok=False,
            exit_code=None,
            timed_out=False,
            stdout="",
            stderr="",
            message=decision.message or f"{hook.event} hook command was denied.",
        )
        append_session_event(workspace.session_dir, "hook_completed", {**event_payload, "result": result})
        return result

    wrapped_command = _hook_command_with_context(hook, tool_name, action)
    timeout_ms = hook_action.timeout_ms
    if logger:
        logger("running hook", f"{hook.event} {tool_name} from {hook.source}")
    observation = execute_action_safely_func(
        workspace,
        RunCommandAction(type="run_command", command=wrapped_command, timeout_ms=timeout_ms, max_output_chars=4_000),
        timeout_ms,
        f"hook:{hook.event}",
    )
    result = _hook_result_from_observation(hook, observation)
    append_session_event(
        workspace.session_dir,
        "hook_completed",
        {**event_payload, "result": redact_jsonable_payload(result)},
    )
    if logger:
        logger("hook passed" if result.ok else "hook failed", summarize(result.message, 500))
    return result


def _hook_command_with_context(hook: ProjectHook, tool_name: str, action: object) -> str:
    values = {
        "VIBEAGENT_HOOK_EVENT": hook.event,
        "VIBEAGENT_TOOL_NAME": tool_name,
        "VIBEAGENT_TOOL_TARGET": build_action_target(action),
    }
    prefix = " ".join(f"{name}={shlex.quote(value)}" for name, value in values.items())
    return f"{prefix} {hook.command}"


def _hook_result_from_observation(hook: ProjectHook, observation: Observation) -> HookRunResult:
    if isinstance(observation, RunCommandObservation):
        command_result = observation.result
        ok = command_result.exit_code == 0 and not command_result.timed_out
        status = "passed" if ok else "failed"
        if command_result.timed_out:
            message = f"{hook.event} hook timed out after {command_result.timeout_ms}ms."
        elif command_result.exit_code is None:
            message = f"{hook.event} hook command could not start."
        else:
            message = f"{hook.event} hook exited with code {command_result.exit_code}."
        return HookRunResult(
            event=hook.event,
            command=hook.command,
            source=hook.source,
            status=status,
            ok=ok,
            exit_code=command_result.exit_code,
            timed_out=command_result.timed_out,
            stdout=command_result.stdout,
            stderr=command_result.stderr,
            message=message,
        )
    return HookRunResult(
        event=hook.event,
        command=hook.command,
        source=hook.source,
        status="failed",
        ok=False,
        exit_code=None,
        timed_out=False,
        stdout="",
        stderr="",
        message=f"{hook.event} hook execution failed: {getattr(observation, 'message', observation.kind)}",
    )


def _hook_failure_observation(event: HookEvent, tool_name: str, message: str) -> ToolErrorObservation:
    return ToolErrorObservation(
        kind="tool_error",
        tool=f"hook:{event}:{tool_name}",
        message=message,
    )
