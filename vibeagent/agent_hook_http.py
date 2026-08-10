from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

from .agent_hook_results import HookRunResult
from .agent_observation_utils import summarize
from .agent_permissions import authorize_tool_action
from .agent_runtime_utils import append_session_event
from .network_url_safety import UrlSafetyError, open_local_or_public_url
from .redaction import redact_sensitive_text
from .types import (
    AgentLogger,
    ApprovalDecision,
    ApprovalHandler,
    ApprovalPolicy,
    ApprovalRequest,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHook
from .workspace_permissions import ProjectPermissions


MAX_HTTP_HOOK_OUTPUT_CHARS = 10_000
MAX_HTTP_HOOK_RESPONSE_BYTES = 40_000
MAX_HTTP_HOOK_REQUEST_BYTES = 1_048_576
MAX_HTTP_HOOK_HEADER_CHARS = 4_000
ENV_REFERENCE_PATTERN = re.compile(
    r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))"
)


@dataclass(frozen=True)
class HttpHookAction:
    type: Literal["http_hook"]
    url: str


def run_project_http_hook(
    workspace: RunWorkspace,
    hook: ProjectHook,
    *,
    target: str,
    hook_input: dict[str, object],
    environment: dict[str, str] | None,
    iteration: int,
    hook_index: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    permissions: ProjectPermissions,
) -> HookRunResult:
    visible_url = redact_sensitive_text(hook.url)
    event_payload = {
        "iteration": iteration,
        "index": hook_index,
        "event": hook.event,
        "tool": target,
        "source": hook.source,
        "matcher": hook.matcher,
        "handler_type": "http",
        "url": visible_url,
    }
    if approval_policy == "plan":
        result = _result(
            hook,
            status="skipped",
            ok=True,
            message="Hook skipped because Plan mode does not send HTTP requests.",
        )
        append_session_event(
            workspace.session_dir, "hook_skipped", {**event_payload, "result": result}
        )
        return result

    request = ApprovalRequest(
        action_type="http_hook",
        target=f"{hook.event} hook for {target}: {visible_url}",
        risk="This configured hook will send lifecycle data in an HTTP POST request.",
    )
    append_session_event(
        workspace.session_dir,
        "hook_approval_requested",
        {**event_payload, "request": request},
    )
    authorization = authorize_tool_action(
        workspace,
        permissions,
        "http_hook",
        HttpHookAction(type="http_hook", url=hook.url),
        iteration,
        approval_handler,
        approval_policy,
        logger,
        default_request=request,
    )
    decision = authorization.decision or ApprovalDecision(
        approved=authorization.allowed,
        message=(
            "HTTP hook authorized."
            if authorization.allowed
            else getattr(
                authorization.denial,
                "message",
                "HTTP hook denied by permission rules.",
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
            message=decision.message or f"{hook.event} HTTP hook was denied.",
        )
        append_session_event(
            workspace.session_dir, "hook_completed", {**event_payload, "result": result}
        )
        return result

    if logger:
        logger("running hook", f"{hook.event} {target} HTTP hook from {hook.source}")
    result = _post_hook(hook, hook_input, environment)
    append_session_event(
        workspace.session_dir, "hook_completed", {**event_payload, "result": result}
    )
    if logger:
        logger(
            "hook passed" if result.ok else "hook failed",
            summarize(result.message, 500),
        )
    return result


def _post_hook(
    hook: ProjectHook,
    hook_input: dict[str, object],
    environment: dict[str, str] | None,
) -> HookRunResult:
    try:
        body = json.dumps(
            hook_input, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        if len(body) > MAX_HTTP_HOOK_REQUEST_BYTES:
            raise ValueError(
                f"HTTP hook input exceeds {MAX_HTTP_HOOK_REQUEST_BYTES} bytes."
            )
        headers = _expanded_headers(hook, environment)
        headers["Content-Type"] = "application/json"
        headers.setdefault("Accept", "application/json, text/plain;q=0.9")
        headers.setdefault("User-Agent", "vibeagent-http-hook/1.0")
        request = urllib.request.Request(
            hook.url,
            data=body,
            headers=headers,
            method="POST",
        )
        with open_local_or_public_url(
            request, timeout=hook.timeout_ms / 1000
        ) as response:
            status = int(response.getcode())
            output = _read_response_text(response)
        return _result(
            hook,
            status="passed",
            ok=True,
            stdout=output,
            http_status=status,
            message=f"{hook.event} HTTP hook returned status {status}.",
        )
    except urllib.error.HTTPError as error:
        return _result(
            hook,
            status="failed",
            ok=False,
            http_status=int(error.code),
            non_blocking_error=True,
            message=(
                f"{hook.event} HTTP hook returned non-success status {error.code}; "
                "the hook error is non-blocking."
            ),
        )
    except (
        UrlSafetyError,
        urllib.error.URLError,
        TimeoutError,
        socket.timeout,
        OSError,
        ValueError,
        UnicodeError,
    ) as error:
        timed_out = isinstance(error, (TimeoutError, socket.timeout))
        return _result(
            hook,
            status="failed",
            ok=False,
            timed_out=timed_out,
            non_blocking_error=True,
            message=(
                f"{hook.event} HTTP hook request failed: "
                f"{redact_sensitive_text(str(error))}. The hook error is non-blocking."
            ),
        )


def _expanded_headers(
    hook: ProjectHook,
    environment: dict[str, str] | None,
) -> dict[str, str]:
    values = dict(os.environ)
    values.update(hook.environment)
    values.update(environment or {})
    allowed = set(hook.allowed_env_vars)

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        return values.get(name, "") if name in allowed else ""

    expanded: dict[str, str] = {}
    for name, value in hook.headers:
        rendered = ENV_REFERENCE_PATTERN.sub(replace, value)
        if (
            len(rendered) > MAX_HTTP_HOOK_HEADER_CHARS
            or "\r" in rendered
            or "\n" in rendered
        ):
            raise ValueError(f"HTTP hook header {name!r} is invalid after environment expansion.")
        try:
            rendered.encode("latin-1")
        except UnicodeEncodeError as error:
            raise ValueError(
                f"HTTP hook header {name!r} is not HTTP header encodable."
            ) from error
        expanded[name] = rendered
    return expanded


def _read_response_text(response: object) -> str:
    raw = response.read(MAX_HTTP_HOOK_RESPONSE_BYTES + 1)  # type: ignore[attr-defined]
    text = raw[:MAX_HTTP_HOOK_RESPONSE_BYTES].decode("utf-8", errors="replace")
    return text[:MAX_HTTP_HOOK_OUTPUT_CHARS]


def _result(
    hook: ProjectHook,
    *,
    status: str,
    ok: bool,
    message: str,
    stdout: str = "",
    timed_out: bool = False,
    http_status: int | None = None,
    non_blocking_error: bool = False,
) -> HookRunResult:
    return HookRunResult(
        event=hook.event,
        command=hook.url,
        source=hook.source,
        status=status,
        ok=ok,
        exit_code=None,
        timed_out=timed_out,
        stdout=stdout,
        stderr="",
        message=message,
        handler_type="http",
        http_status=http_status,
        non_blocking_error=non_blocking_error,
    )


__all__ = ["HttpHookAction", "run_project_http_hook"]
