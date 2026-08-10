from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from .agent_approval import build_approval_request
from .agent_hook_results import HookRunResult
from .agent_observation_utils import summarize
from .agent_permissions import authorize_tool_action
from .agent_runtime_utils import append_session_event
from .redaction import redact_sensitive_text
from .types import (
    AgentLogger,
    ApprovalDecision,
    ApprovalHandler,
    ApprovalPolicy,
    McpCallAction,
    McpCallObservation,
    Observation,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHook
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]
MAX_MCP_HOOK_ARGUMENT_CHARS = 50_000
MAX_MCP_HOOK_OUTPUT_CHARS = 10_000
MAX_MCP_HOOK_INPUT_DEPTH = 20
MAX_MCP_HOOK_INPUT_NODES = 1_000
PLACEHOLDER_PATTERN = re.compile(r"\$\{([A-Za-z0-9_.-]+)\}")


def run_project_mcp_hook(
    workspace: RunWorkspace,
    hook: ProjectHook,
    *,
    target: str,
    hook_input: dict[str, object],
    iteration: int,
    hook_index: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    permissions: ProjectPermissions,
) -> HookRunResult:
    handler_target = f"{hook.mcp_server}/{hook.mcp_tool}"
    event_payload = {
        "iteration": iteration,
        "index": hook_index,
        "event": hook.event,
        "tool": target,
        "source": hook.source,
        "matcher": hook.matcher,
        "handler_type": "mcp_tool",
        "server": hook.mcp_server,
        "mcp_tool": hook.mcp_tool,
    }
    if approval_policy == "plan":
        result = _result(
            hook,
            status="skipped",
            ok=True,
            message="Hook skipped because Plan mode does not call MCP tools.",
        )
        append_session_event(
            workspace.session_dir, "hook_skipped", {**event_payload, "result": result}
        )
        return result

    try:
        arguments = expand_mcp_hook_input(hook.mcp_input, hook_input)
    except (TypeError, ValueError) as error:
        result = _result(
            hook,
            status="failed",
            ok=False,
            non_blocking_error=True,
            message=(
                f"{hook.event} MCP hook input was rejected: "
                f"{redact_sensitive_text(str(error))}. The hook error is non-blocking."
            ),
        )
        append_session_event(
            workspace.session_dir, "hook_completed", {**event_payload, "result": result}
        )
        return result

    action = McpCallAction(
        type="mcp_call",
        server=hook.mcp_server,
        name=hook.mcp_tool,
        arguments=arguments,
        timeout_ms=hook.timeout_ms,
        max_output_chars=MAX_MCP_HOOK_OUTPUT_CHARS,
    )
    request = build_approval_request(action)
    assert request is not None
    request = replace(
        request,
        target=f"{hook.event} hook for {target}: {request.target}",
    )
    append_session_event(
        workspace.session_dir,
        "hook_approval_requested",
        {**event_payload, "request": request},
    )
    tool_name = f"mcp__{hook.mcp_server}__{hook.mcp_tool}"
    authorization = authorize_tool_action(
        workspace,
        permissions,
        tool_name,
        action,
        iteration,
        approval_handler,
        approval_policy,
        logger,
        default_request=request,
    )
    decision = authorization.decision or ApprovalDecision(
        approved=authorization.allowed,
        message=(
            "MCP hook authorized."
            if authorization.allowed
            else getattr(
                authorization.denial,
                "message",
                "MCP hook denied by permission rules.",
            )
        ),
    )
    append_session_event(
        workspace.session_dir,
        "hook_approval_decision",
        {**event_payload, "decision": decision},
    )
    if not authorization.allowed:
        result = _result(
            hook,
            status="denied",
            ok=False,
            message=decision.message or f"{hook.event} MCP hook was denied.",
        )
        append_session_event(
            workspace.session_dir, "hook_completed", {**event_payload, "result": result}
        )
        return result

    if logger:
        logger("running hook", f"{hook.event} {target} MCP hook {handler_target}")
    observation = execute_action_safely_func(
        workspace,
        action,
        hook.timeout_ms,
        f"hook:{hook.event}",
    )
    if isinstance(observation, McpCallObservation) and observation.ok:
        result = _result(
            hook,
            status="passed",
            ok=True,
            stdout=observation.text_output,
            message=f"{hook.event} MCP hook {handler_target} completed.",
        )
    else:
        error = getattr(observation, "error", None) or getattr(
            observation, "message", observation.kind
        )
        result = _result(
            hook,
            status="failed",
            ok=False,
            non_blocking_error=True,
            message=(
                f"{hook.event} MCP hook {handler_target} failed: "
                f"{redact_sensitive_text(str(error))}. The hook error is non-blocking."
            ),
        )
    append_session_event(
        workspace.session_dir, "hook_completed", {**event_payload, "result": result}
    )
    if logger:
        logger(
            "hook passed" if result.ok else "hook failed",
            summarize(result.message, 500),
        )
    return result


def expand_mcp_hook_input(
    template: dict[str, Any], hook_input: dict[str, object]
) -> dict[str, Any]:
    node_count = [0]

    def copy_value(value: object, depth: int) -> object:
        node_count[0] += 1
        if depth > MAX_MCP_HOOK_INPUT_DEPTH:
            raise ValueError(
                f"MCP hook input exceeds depth {MAX_MCP_HOOK_INPUT_DEPTH}."
            )
        if node_count[0] > MAX_MCP_HOOK_INPUT_NODES:
            raise ValueError(
                f"MCP hook input exceeds {MAX_MCP_HOOK_INPUT_NODES} values."
            )
        if isinstance(value, dict):
            return {
                str(key): copy_value(item, depth + 1)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [copy_value(item, depth + 1) for item in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        raise ValueError("MCP hook placeholder value is not JSON serializable.")

    def expand(value: Any, depth: int) -> Any:
        node_count[0] += 1
        if depth > MAX_MCP_HOOK_INPUT_DEPTH:
            raise ValueError(
                f"MCP hook input exceeds depth {MAX_MCP_HOOK_INPUT_DEPTH}."
            )
        if node_count[0] > MAX_MCP_HOOK_INPUT_NODES:
            raise ValueError(
                f"MCP hook input exceeds {MAX_MCP_HOOK_INPUT_NODES} values."
            )
        if isinstance(value, dict):
            return {str(key): expand(item, depth + 1) for key, item in value.items()}
        if isinstance(value, list):
            return [expand(item, depth + 1) for item in value]
        if not isinstance(value, str):
            return value
        exact = PLACEHOLDER_PATTERN.fullmatch(value)
        if exact is not None:
            return copy_value(_resolve_path(hook_input, exact.group(1)), depth + 1)

        def replace(match: re.Match[str]) -> str:
            resolved = copy_value(
                _resolve_path(hook_input, match.group(1)), depth + 1
            )
            return _render_json_value(resolved)

        return PLACEHOLDER_PATTERN.sub(replace, value)

    expanded = expand(template, 0)
    if not isinstance(expanded, dict):
        raise ValueError("MCP hook input expansion must produce an object.")
    encoded = json.dumps(expanded, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > MAX_MCP_HOOK_ARGUMENT_CHARS:
        raise ValueError(
            f"MCP hook expanded input exceeds {MAX_MCP_HOOK_ARGUMENT_CHARS} characters."
        )
    return expanded


def _resolve_path(payload: object, path: str) -> object:
    current = payload
    for segment in path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
            continue
        if isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if index < len(current):
                current = current[index]
                continue
        raise ValueError(f"MCP hook input placeholder ${{{path}}} is unavailable.")
    return current


def _render_json_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _result(
    hook: ProjectHook,
    *,
    status: str,
    ok: bool,
    message: str,
    stdout: str = "",
    non_blocking_error: bool = False,
) -> HookRunResult:
    return HookRunResult(
        event=hook.event,
        command=f"{hook.mcp_server}/{hook.mcp_tool}",
        source=hook.source,
        status=status,
        ok=ok,
        exit_code=None,
        timed_out=False,
        stdout=stdout,
        stderr="",
        message=message,
        handler_type="mcp_tool",
        non_blocking_error=non_blocking_error,
    )


__all__ = ["expand_mcp_hook_input", "run_project_mcp_hook"]
