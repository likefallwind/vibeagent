from __future__ import annotations

import shlex
from dataclasses import dataclass

from .agent_action_targets import build_action_target
from .types import Observation, RunCommandObservation, ToolErrorObservation
from .workspace_hooks import HookEvent, ProjectHook


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


def hook_command_with_context(hook: ProjectHook, tool_name: str, action: object) -> str:
    values = {
        "VIBEAGENT_HOOK_EVENT": hook.event,
        "VIBEAGENT_TOOL_NAME": tool_name,
        "VIBEAGENT_TOOL_TARGET": build_action_target(action),
    }
    prefix = " ".join(f"{name}={shlex.quote(value)}" for name, value in values.items())
    return f"{prefix} {hook.command}"


def hook_result_from_observation(hook: ProjectHook, observation: Observation) -> HookRunResult:
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


def hook_failure_observation(event: HookEvent, tool_name: str, message: str) -> ToolErrorObservation:
    return ToolErrorObservation(
        kind="tool_error",
        tool=f"hook:{event}:{tool_name}",
        message=message,
    )
