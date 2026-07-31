from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .local_command_workspace import local_command_workspace
from .local_http_parsing import parse_http_fetch_request, parse_http_request, parse_port_request
from .local_http_reports import (
    format_http_fetch_report_text,
    format_http_report_text,
    format_port_report_text,
    http_failure_report,
    http_fetch_failure_report,
    port_failure_report,
    serialize_http_report,
    serialize_http_response_fields,
    usage_error,
)
from .types import HttpCheckAction, HttpFetchAction, PortCheckAction

PORT_USAGE = "Usage: /port <port> [host] [timeout-ms]"
HTTP_USAGE = "Usage: /http <url> [contains]"
HTTP_FETCH_USAGE = "Usage: /http-fetch <url>"


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


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
        return port_failure_report(
            root,
            message,
            port=selected_port,
            host=selected_host,
            timeout_ms=selected_timeout,
        )

    try:
        selected_port, selected_host, selected_timeout_ms = parse_port_request(argument, port, host, timeout_ms)
    except ValueError as error:
        return failure(usage_error(PORT_USAGE, error))
    if selected_timeout_ms < 100:
        return failure(
            usage_error(PORT_USAGE, "timeout_ms must be at least 100."),
            selected_port,
            selected_host,
            selected_timeout_ms,
        )
    if selected_timeout_ms > 600_000:
        return failure(
            usage_error(PORT_USAGE, "timeout_ms must be at most 600000."),
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
        return http_failure_report(
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
        return failure(usage_error(HTTP_USAGE, error))
    if timeout_ms < 100:
        return failure(
            usage_error(HTTP_USAGE, "timeout_ms must be at least 100."),
            selected_url,
            selected_contains,
        )
    if timeout_ms > 600_000:
        return failure(
            usage_error(HTTP_USAGE, "timeout_ms must be at most 600000."),
            selected_url,
            selected_contains,
        )
    if max_body_chars < 0:
        return failure(
            usage_error(HTTP_USAGE, "max_body_chars must be non-negative."),
            selected_url,
            selected_contains,
        )
    if max_body_chars > 50_000:
        return failure(
            usage_error(HTTP_USAGE, "max_body_chars must be at most 50000."),
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
        return http_fetch_failure_report(
            root,
            message,
            url=selected_url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
        )

    try:
        selected_url = parse_http_fetch_request(argument, url)
    except ValueError as error:
        return failure(usage_error(HTTP_FETCH_USAGE, error))
    if timeout_ms < 100:
        return failure(
            usage_error(HTTP_FETCH_USAGE, "timeout_ms must be at least 100."),
            selected_url,
        )
    if timeout_ms > 600_000:
        return failure(
            usage_error(HTTP_FETCH_USAGE, "timeout_ms must be at most 600000."),
            selected_url,
        )
    if max_body_chars < 1:
        return failure(
            usage_error(HTTP_FETCH_USAGE, "max_body_chars must be at least 1."),
            selected_url,
        )
    if max_body_chars > 100_000:
        return failure(
            usage_error(HTTP_FETCH_USAGE, "max_body_chars must be at most 100000."),
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
        **serialize_http_response_fields(
            observation,
            before_reachable={"contentType": observation.content_type},
        ),
    }
