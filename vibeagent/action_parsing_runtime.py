from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .action_parsing_helpers import (
    ActionParseError,
    parse_optional_nonnegative_int,
    parse_optional_positive_int,
    parse_run_command_items,
)
from .types import (
    CheckRunCommandsAction,
    CommandCheckAction,
    EnvironmentInfoAction,
    HttpCheckAction,
    HttpFetchAction,
    WebFetchAction,
    PortCheckAction,
)


RUNTIME_ACTION_TYPES = {
    "command_check",
    "check_run_commands",
    "port_check",
    "http_check",
    "http_fetch",
    "web_fetch",
    "environment_info",
}


def _parse_http_url(value: Any, raw: str, action_type: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty url.", raw)
    parsed_url = urlparse(value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ActionParseError(f"{action_type} action url must be an http or https URL.", raw)
    return value


def _parse_timeout_ms(value: Any, raw: str) -> int | None:
    timeout_ms = parse_optional_positive_int(value, "timeout_ms", raw, maximum=10_000)
    if timeout_ms is not None and timeout_ms < 100:
        raise ActionParseError("timeout_ms must be at least 100.", raw)
    return timeout_ms


def parse_runtime_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in RUNTIME_ACTION_TYPES:
        return None

    if action_type == "command_check":
        command = value.get("command")
        cwd = value.get("cwd")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError("command_check action requires a non-empty command.", raw)
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("command_check action cwd must be a string when provided.", raw)
        return CommandCheckAction(type="command_check", command=command, cwd=cwd)

    if action_type == "check_run_commands":
        return CheckRunCommandsAction(
            type="check_run_commands",
            commands=parse_run_command_items(value.get("commands"), raw, "check_run_commands"),
        )

    if action_type == "port_check":
        port = parse_optional_positive_int(value.get("port"), "port", raw, maximum=65_535)
        if port is None:
            raise ActionParseError("port_check action requires port.", raw)
        host = value.get("host", "127.0.0.1")
        timeout_ms = _parse_timeout_ms(value.get("timeout_ms"), raw)
        if port < 1:
            raise ActionParseError("port must be at least 1.", raw)
        if not isinstance(host, str) or not host.strip():
            raise ActionParseError("port_check action host must be a non-empty string when provided.", raw)
        return PortCheckAction(type="port_check", host=host, port=port, timeout_ms=timeout_ms)

    if action_type == "http_check":
        url = _parse_http_url(value.get("url"), raw, "http_check")
        max_body_chars = parse_optional_nonnegative_int(
            value.get("max_body_chars"),
            "max_body_chars",
            raw,
            maximum=50_000,
        )
        contains = value.get("contains")
        if contains is not None and (not isinstance(contains, str) or not contains.strip()):
            raise ActionParseError("http_check action contains must be a non-empty string when provided.", raw)
        regex = value.get("regex", False)
        if not isinstance(regex, bool):
            raise ActionParseError("http_check action regex must be a boolean when provided.", raw)
        return HttpCheckAction(
            type="http_check",
            url=url,
            timeout_ms=_parse_timeout_ms(value.get("timeout_ms"), raw),
            max_body_chars=max_body_chars,
            contains=contains,
            regex=regex,
        )

    if action_type == "http_fetch":
        url = _parse_http_url(value.get("url"), raw, "http_fetch")
        max_body_chars = parse_optional_positive_int(value.get("max_body_chars"), "max_body_chars", raw, maximum=100_000)
        return HttpFetchAction(
            type="http_fetch",
            url=url,
            timeout_ms=_parse_timeout_ms(value.get("timeout_ms"), raw),
            max_body_chars=max_body_chars,
        )

    if action_type == "web_fetch":
        url = _parse_http_url(value.get("url"), raw, "web_fetch")
        max_text_chars = parse_optional_positive_int(
            value.get("max_text_chars"), "max_text_chars", raw, maximum=100_000
        )
        return WebFetchAction(
            type="web_fetch",
            url=url,
            timeout_ms=_parse_timeout_ms(value.get("timeout_ms"), raw),
            max_text_chars=max_text_chars,
        )

    if action_type == "environment_info":
        return EnvironmentInfoAction(type="environment_info")

    raise AssertionError(f"Unhandled runtime action type: {action_type!r}")
