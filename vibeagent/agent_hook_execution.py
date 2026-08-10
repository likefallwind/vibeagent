from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import re
from collections.abc import Callable
from uuid import uuid4

from .agent_hook_results import HookRunResult, hook_result_from_observation
from .agent_observation_utils import summarize
from .agent_permissions import authorize_tool_action
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
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHook
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def run_project_hook_command(
    workspace: RunWorkspace,
    hook: ProjectHook,
    *,
    target: str,
    hook_input: dict[str, object],
    cwd: str | None = None,
    environment: dict[str, str] | None = None,
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
        "tool": target,
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
        append_session_event(
            workspace.session_dir, "hook_skipped", {**event_payload, "result": result}
        )
        return result

    request = ApprovalRequest(
        action_type="run_command",
        target=f"{hook.event} hook for {target}: {hook.command}",
        risk="This configured hook will run a shell command in the active project.",
    )
    append_session_event(
        workspace.session_dir,
        "hook_approval_requested",
        {**event_payload, "request": request},
    )
    hook_action = RunCommandAction(
        type="run_command",
        command=hook.command,
        timeout_ms=min(hook.timeout_ms, command_timeout_ms),
        max_output_chars=4_000,
        cwd=cwd,
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
            else getattr(
                authorization.denial,
                "message",
                "Hook command denied by permission rules.",
            )
        ),
    )
    append_session_event(
        workspace.session_dir,
        "hook_approval_decision",
        {**event_payload, "decision": decision},
    )
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
        append_session_event(
            workspace.session_dir, "hook_completed", {**event_payload, "result": result}
        )
        return result

    input_path = _write_hook_input(workspace, hook_input)
    environment_path: Path | None = None
    try:
        environment_path = _write_hook_environment(
            workspace,
            hook.command,
            {
                "CLAUDE_PROJECT_DIR": str(workspace.root),
                "VIBEAGENT_HOOK_EVENT": hook.event,
                "VIBEAGENT_HOOK_INPUT": json.dumps(
                    hook_input,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                **(environment or {}),
            },
        )
        wrapped_command = _hook_command_with_input(input_path, environment_path)
        if logger:
            logger("running hook", f"{hook.event} {target} from {hook.source}")
        observation: Observation = execute_action_safely_func(
            workspace,
            RunCommandAction(
                type="run_command",
                command=wrapped_command,
                timeout_ms=hook_action.timeout_ms,
                max_output_chars=4_000,
                cwd=cwd,
            ),
            hook_action.timeout_ms,
            f"hook:{hook.event}",
        )
    finally:
        input_path.unlink(missing_ok=True)
        if environment_path is not None:
            environment_path.unlink(missing_ok=True)
    result = hook_result_from_observation(hook, observation)
    append_session_event(
        workspace.session_dir,
        "hook_completed",
        {**event_payload, "result": redact_jsonable_payload(result)},
    )
    if logger:
        logger(
            "hook passed" if result.ok else "hook failed",
            summarize(result.message, 500),
        )
    return result


def _hook_command_with_input(
    input_path: Path,
    environment_path: Path,
) -> str:
    return f"{shlex.quote(str(environment_path))} < {shlex.quote(str(input_path))}"


def _write_hook_input(workspace: RunWorkspace, hook_input: dict[str, object]) -> Path:
    path = workspace.session_dir / f".hook-input-{uuid4().hex}.json"
    encoded = json.dumps(hook_input, ensure_ascii=False, separators=(",", ":"))
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _write_hook_environment(
    workspace: RunWorkspace,
    command: str,
    environment: dict[str, str],
) -> Path:
    if any(not ENVIRONMENT_NAME_PATTERN.fullmatch(name) for name in environment):
        raise ValueError("Hook environment contains an invalid variable name.")
    path = workspace.session_dir / f".hook-launch-{uuid4().hex}.sh"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("#!/bin/sh\n")
            for name, value in environment.items():
                stream.write(f"export {name}={shlex.quote(value)}\n")
            stream.write(f"exec /bin/sh -c {shlex.quote(command)}\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


__all__ = ["run_project_hook_command"]
