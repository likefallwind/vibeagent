from __future__ import annotations

import json

from .agent_hook_prompt import HookModelRuntime, parse_prompt_hook_decision
from .agent_hook_results import HookRunResult
from .agent_runtime_utils import append_session_event
from .redaction import redact_sensitive_text
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHook


MAX_AGENT_HOOK_ERROR_CHARS = 1_000


def agent_hook_decision_result(
    workspace: RunWorkspace,
    hook: ProjectHook,
    event_payload: dict[str, object],
    text: str,
    runtime: HookModelRuntime,
) -> HookRunResult:
    try:
        allowed, reason = parse_prompt_hook_decision(text.strip())
    except ValueError as error:
        return failed_agent_hook_result(
            workspace,
            hook,
            event_payload,
            f"Agent hook response was rejected: {error}",
        )
    safe_reason = redact_sensitive_text(reason)
    safe_output = json.dumps(
        {"ok": allowed, **({"reason": safe_reason} if safe_reason else {})},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    result = HookRunResult(
        event=hook.event,
        command="agent",
        source=hook.source,
        status="passed" if allowed else "blocked",
        ok=allowed,
        exit_code=None,
        timed_out=False,
        stdout=safe_output,
        stderr="",
        message=(
            f"{hook.event} agent hook allowed execution."
            if allowed
            else safe_reason
        ),
        handler_type="agent",
    )
    append_session_event(
        workspace.session_dir,
        "hook_completed",
        {**event_payload, "result": result},
    )
    if runtime.logger:
        runtime.logger("hook passed" if allowed else "hook blocked", result.message)
    return result


def failed_agent_hook_result(
    workspace: RunWorkspace,
    hook: ProjectHook,
    event_payload: dict[str, object],
    message: str,
    *,
    timed_out: bool = False,
) -> HookRunResult:
    bounded = redact_sensitive_text(message)
    if len(bounded) > MAX_AGENT_HOOK_ERROR_CHARS:
        bounded = bounded[: MAX_AGENT_HOOK_ERROR_CHARS - 3] + "..."
    result = HookRunResult(
        event=hook.event,
        command="agent",
        source=hook.source,
        status="failed",
        ok=False,
        exit_code=None,
        timed_out=timed_out,
        stdout="",
        stderr="",
        message=f"{bounded} The hook error is non-blocking.",
        handler_type="agent",
        non_blocking_error=True,
    )
    append_session_event(
        workspace.session_dir,
        "hook_completed",
        {**event_payload, "result": result},
    )
    return result


__all__ = ["agent_hook_decision_result", "failed_agent_hook_result"]
