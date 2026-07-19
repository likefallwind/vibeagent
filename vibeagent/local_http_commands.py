from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .local_http_parsing import parse_http_fetch_request, parse_http_request, parse_port_request
from .types import HttpCheckAction, HttpFetchAction, PortCheckAction

PORT_USAGE = "Usage: /port <port> [host] [timeout-ms]"
HTTP_USAGE = "Usage: /http <url> [contains]"
HTTP_FETCH_USAGE = "Usage: /http-fetch <url>"


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def _port_failure_report(
    root: Path,
    message: str,
    *,
    port: int | None,
    host: str,
    timeout_ms: int,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "host": host,
        "port": port,
        "reachable": False,
        "timeoutMs": timeout_ms,
        "error": None,
        "message": message,
    }


def _http_failure_report(
    root: Path,
    message: str,
    *,
    url: str,
    contains: str | None,
    timeout_ms: int,
    max_body_chars: int,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "url": url,
        "finalUrl": None,
        "status": None,
        "reason": None,
        "reachable": False,
        "matched": False,
        "matchedPattern": contains,
        "timeoutMs": timeout_ms,
        "maxBodyChars": max_body_chars,
        "body": "",
        "bodyTruncated": False,
        "error": None,
        "message": message,
    }


def _http_fetch_failure_report(
    root: Path,
    message: str,
    *,
    url: str,
    timeout_ms: int,
    max_body_chars: int,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "url": url,
        "finalUrl": None,
        "status": None,
        "reason": None,
        "contentType": None,
        "reachable": False,
        "timeoutMs": timeout_ms,
        "maxBodyChars": max_body_chars,
        "body": "",
        "bodyTruncated": False,
        "error": None,
        "message": message,
    }


def get_port_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    timeout_ms: int = 1_000,
) -> str:
    return format_port_report_text(get_port_report(project_root, argument, port, host, timeout_ms))


def get_port_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    port: int | None = None,
    host: str = "127.0.0.1",
    timeout_ms: int = 1_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_port: int | None = port, selected_host: str = host, selected_timeout: int = timeout_ms) -> dict[str, object]:
        return _port_failure_report(
            root,
            message,
            port=selected_port,
            host=selected_host,
            timeout_ms=selected_timeout,
        )

    try:
        selected_port, selected_host, selected_timeout_ms = parse_port_request(argument, port, host, timeout_ms)
    except ValueError as error:
        return failure(_usage_error(PORT_USAGE, error))
    if selected_timeout_ms < 100:
        return failure(
            _usage_error(PORT_USAGE, "timeout_ms must be at least 100."),
            selected_port,
            selected_host,
            selected_timeout_ms,
        )
    if selected_timeout_ms > 600_000:
        return failure(
            _usage_error(PORT_USAGE, "timeout_ms must be at most 600000."),
            selected_port,
            selected_host,
            selected_timeout_ms,
        )

    workspace = local_command_workspace(root, "local-port")
    observation = _execute_action(
        workspace,
        PortCheckAction(type="port_check", port=selected_port, host=selected_host, timeout_ms=selected_timeout_ms),
    )
    if observation.kind != "port_check":
        return failure(f"Unexpected observation: {observation.kind}", selected_port, selected_host, selected_timeout_ms)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "host": observation.host,
        "port": observation.port,
        "reachable": observation.reachable,
        "timeoutMs": observation.timeout_ms,
        "error": observation.error,
        "message": observation.message,
    }


def format_port_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "Port:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  host: {report.get('host') or ''}",
        f"  port: {report.get('port') if report.get('port') is not None else '.'}",
        f"  reachable: {'yes' if bool(report.get('reachable')) else 'no'}",
        f"  timeoutMs: {int(report.get('timeoutMs', 0) or 0)}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    return "\n".join(lines)

def get_http_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    contains: str | None = None,
    timeout_ms: int = 2_000,
    max_body_chars: int = 2_000,
    regex: bool = False,
) -> str:
    return format_http_report_text(get_http_report(project_root, argument, url, contains, timeout_ms, max_body_chars, regex))


def get_http_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    contains: str | None = None,
    timeout_ms: int = 2_000,
    max_body_chars: int = 2_000,
    regex: bool = False,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_url: str = url or "", selected_contains: str | None = contains) -> dict[str, object]:
        return _http_failure_report(
            root,
            message,
            url=selected_url,
            contains=selected_contains,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
        )

    try:
        selected_url, selected_contains = parse_http_request(argument, url, contains)
    except ValueError as error:
        return failure(_usage_error(HTTP_USAGE, error))
    if timeout_ms < 100:
        return failure(
            _usage_error(HTTP_USAGE, "timeout_ms must be at least 100."),
            selected_url,
            selected_contains,
        )
    if timeout_ms > 600_000:
        return failure(
            _usage_error(HTTP_USAGE, "timeout_ms must be at most 600000."),
            selected_url,
            selected_contains,
        )
    if max_body_chars < 0:
        return failure(
            _usage_error(HTTP_USAGE, "max_body_chars must be non-negative."),
            selected_url,
            selected_contains,
        )
    if max_body_chars > 50_000:
        return failure(
            _usage_error(HTTP_USAGE, "max_body_chars must be at most 50000."),
            selected_url,
            selected_contains,
        )

    workspace = local_command_workspace(root, "local-http")
    observation = _execute_action(
        workspace,
        HttpCheckAction(
            type="http_check",
            url=selected_url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            contains=selected_contains,
            regex=regex,
        ),
    )
    if observation.kind != "http_check":
        return failure(f"Unexpected observation: {observation.kind}", selected_url, selected_contains)
    return serialize_http_report(root, observation)


def format_http_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "HTTP:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  url: {report.get('url') or ''}",
        f"  finalUrl: {report.get('finalUrl') or '.'}",
        f"  status: {report.get('status') if report.get('status') is not None else '.'}",
        f"  reason: {report.get('reason') or '.'}",
        f"  reachable: {'yes' if bool(report.get('reachable')) else 'no'}",
        f"  matched: {'yes' if bool(report.get('matched')) else 'no'}",
        f"  matchedPattern: {report.get('matchedPattern') or '.'}",
        f"  timeoutMs: {int(report.get('timeoutMs', 0) or 0)}",
        f"  maxBodyChars: {int(report.get('maxBodyChars', 0) or 0)}",
        f"  bodyTruncated: {'yes' if bool(report.get('bodyTruncated')) else 'no'}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    body = str(report.get("body") or "")
    if body:
        lines.append("  body:")
        lines.append(_indent_block(body.rstrip(), spaces=4))
    else:
        lines.append("  body: none")
    return "\n".join(lines)


def serialize_http_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok", False)),
        "url": str(getattr(observation, "url", "") or ""),
        "finalUrl": getattr(observation, "final_url", None),
        "status": getattr(observation, "status", None),
        "reason": getattr(observation, "reason", None),
        "reachable": bool(getattr(observation, "reachable", False)),
        "matched": bool(getattr(observation, "matched", False)),
        "matchedPattern": getattr(observation, "matched_pattern", None),
        "timeoutMs": int(getattr(observation, "timeout_ms", 0) or 0),
        "maxBodyChars": int(getattr(observation, "max_body_chars", 0) or 0),
        "body": str(getattr(observation, "body", "") or ""),
        "bodyTruncated": bool(getattr(observation, "body_truncated", False)),
        "error": getattr(observation, "error", None),
        "message": str(getattr(observation, "message", "") or ""),
    }


def get_http_fetch_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    timeout_ms: int = 5_000,
    max_body_chars: int = 12_000,
) -> str:
    return format_http_fetch_report_text(get_http_fetch_report(project_root, argument, url, timeout_ms, max_body_chars))


def get_http_fetch_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    url: str | None = None,
    timeout_ms: int = 5_000,
    max_body_chars: int = 12_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str, selected_url: str = url or "") -> dict[str, object]:
        return _http_fetch_failure_report(
            root,
            message,
            url=selected_url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
        )

    try:
        selected_url = parse_http_fetch_request(argument, url)
    except ValueError as error:
        return failure(_usage_error(HTTP_FETCH_USAGE, error))
    if timeout_ms < 100:
        return failure(
            _usage_error(HTTP_FETCH_USAGE, "timeout_ms must be at least 100."),
            selected_url,
        )
    if timeout_ms > 600_000:
        return failure(
            _usage_error(HTTP_FETCH_USAGE, "timeout_ms must be at most 600000."),
            selected_url,
        )
    if max_body_chars < 1:
        return failure(
            _usage_error(HTTP_FETCH_USAGE, "max_body_chars must be at least 1."),
            selected_url,
        )
    if max_body_chars > 100_000:
        return failure(
            _usage_error(HTTP_FETCH_USAGE, "max_body_chars must be at most 100000."),
            selected_url,
        )

    workspace = local_command_workspace(root, "local-http-fetch")
    observation = _execute_action(
        workspace,
        HttpFetchAction(
            type="http_fetch",
            url=selected_url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
        ),
    )
    if observation.kind != "http_fetch":
        return failure(f"Unexpected observation: {observation.kind}", selected_url)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "url": observation.url,
        "finalUrl": observation.final_url,
        "status": observation.status,
        "reason": observation.reason,
        "contentType": observation.content_type,
        "reachable": observation.reachable,
        "timeoutMs": observation.timeout_ms,
        "maxBodyChars": observation.max_body_chars,
        "body": observation.body,
        "bodyTruncated": observation.body_truncated,
        "error": observation.error,
        "message": observation.message,
    }


def format_http_fetch_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        "HTTP fetch:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  url: {report.get('url') or ''}",
        f"  finalUrl: {report.get('finalUrl') or '.'}",
        f"  status: {report.get('status') if report.get('status') is not None else '.'}",
        f"  reason: {report.get('reason') or '.'}",
        f"  contentType: {report.get('contentType') or '.'}",
        f"  reachable: {'yes' if bool(report.get('reachable')) else 'no'}",
        f"  timeoutMs: {int(report.get('timeoutMs', 0) or 0)}",
        f"  maxBodyChars: {int(report.get('maxBodyChars', 0) or 0)}",
        f"  bodyTruncated: {'yes' if bool(report.get('bodyTruncated')) else 'no'}",
    ]
    if report.get("error"):
        lines.append(f"  error: {report.get('error')}")
    lines.append(f"  message: {message}")
    body = str(report.get("body") or "")
    if body:
        lines.append("  body:")
        lines.append(_indent_block(body.rstrip(), spaces=4))
    else:
        lines.append("  body: none")
    return "\n".join(lines)
