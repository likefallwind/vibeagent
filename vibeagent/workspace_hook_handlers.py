from __future__ import annotations

import json
import re
from typing import Literal, cast
from urllib.parse import urlsplit

from .mcp_config import MCP_NAME_PATTERN
from .workspace_hook_types import PROMPT_HOOK_EVENTS, HookEvent, ProjectHook


MAX_HOOK_COMMAND_CHARS = 4_000
MAX_HOOK_URL_CHARS = 4_000
MAX_HOOK_HEADERS = 32
MAX_HOOK_HEADER_CHARS = 4_000
MAX_HOOK_PROMPT_CHARS = 50_000
MAX_HOOK_MODEL_CHARS = 200
HOOK_HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FORBIDDEN_HOOK_HEADERS = frozenset(
    {"content-length", "content-type", "host", "transfer-encoding"}
)


def parse_hook_handler(
    event: str, matcher: str, payload: object, source: str
) -> ProjectHook:
    if not isinstance(payload, dict):
        raise ValueError(f"{source} hook handlers must be objects.")
    handler_type = payload.get("type")
    if handler_type == "command":
        return _parse_command_hook(event, matcher, payload, source)
    if handler_type == "http":
        return _parse_http_hook(event, matcher, payload, source)
    if handler_type == "mcp_tool":
        return _parse_mcp_tool_hook(event, matcher, payload, source)
    if handler_type == "prompt":
        return _parse_model_hook(event, matcher, payload, source, handler_type="prompt")
    if handler_type == "agent":
        return _parse_model_hook(event, matcher, payload, source, handler_type="agent")
    raise ValueError(
        f"{source} hook type must be command, http, mcp_tool, prompt, or agent."
    )


def _parse_command_hook(
    event: str, matcher: str, payload: dict[str, object], source: str
) -> ProjectHook:
    command = payload.get("command")
    if (
        not isinstance(command, str)
        or not command.strip()
        or len(command) > MAX_HOOK_COMMAND_CHARS
    ):
        raise ValueError(
            f"{source} hook command must contain 1-{MAX_HOOK_COMMAND_CHARS} characters."
        )
    timeout_ms = _parse_hook_timeout(
        payload,
        source,
        default_ms=_default_hook_timeout_ms(event),
    )
    async_value = payload.get("async", False)
    async_rewake = payload.get("asyncRewake", False)
    if not isinstance(async_value, bool):
        raise ValueError(f"{source} hook async must be a boolean.")
    if not isinstance(async_rewake, bool):
        raise ValueError(f"{source} hook asyncRewake must be a boolean.")
    return ProjectHook(
        event=cast(HookEvent, event),
        matcher=matcher,
        command=command.strip(),
        timeout_ms=timeout_ms,
        source=source,
        async_=async_value or async_rewake,
        async_rewake=async_rewake,
    )


def _parse_http_hook(
    event: str, matcher: str, payload: dict[str, object], source: str
) -> ProjectHook:
    if "async" in payload or "asyncRewake" in payload:
        raise ValueError(f"{source} HTTP hooks do not support async or asyncRewake.")
    url = payload.get("url")
    if not isinstance(url, str) or not url.strip() or len(url) > MAX_HOOK_URL_CHARS:
        raise ValueError(
            f"{source} HTTP hook URL must contain 1-{MAX_HOOK_URL_CHARS} characters."
        )
    normalized_url = url.strip()
    parsed_url = urlsplit(normalized_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise ValueError(f"{source} HTTP hook URL must use HTTP or HTTPS and include a host.")
    if parsed_url.username is not None or parsed_url.password is not None:
        raise ValueError(f"{source} HTTP hook URL credentials are not allowed.")
    try:
        parsed_url.port
    except ValueError as error:
        raise ValueError(f"{source} HTTP hook URL has an invalid port: {error}.") from error

    headers_payload = payload.get("headers", {})
    if not isinstance(headers_payload, dict) or len(headers_payload) > MAX_HOOK_HEADERS:
        raise ValueError(
            f"{source} HTTP hook headers must be an object with at most {MAX_HOOK_HEADERS} entries."
        )
    headers: list[tuple[str, str]] = []
    for name, value in headers_payload.items():
        if (
            not isinstance(name, str)
            or not HOOK_HEADER_NAME_PATTERN.fullmatch(name)
            or name.lower() in FORBIDDEN_HOOK_HEADERS
        ):
            raise ValueError(
                f"{source} HTTP hook header name is invalid or reserved: {name!r}."
            )
        if (
            not isinstance(value, str)
            or len(value) > MAX_HOOK_HEADER_CHARS
            or "\r" in value
            or "\n" in value
        ):
            raise ValueError(
                f"{source} HTTP hook header {name!r} must be a single-line string of at most {MAX_HOOK_HEADER_CHARS} characters."
            )
        headers.append((name, value))

    allowed_payload = payload.get("allowedEnvVars", [])
    if (
        not isinstance(allowed_payload, list)
        or len(allowed_payload) > MAX_HOOK_HEADERS
        or any(
            not isinstance(name, str) or not ENVIRONMENT_NAME_PATTERN.fullmatch(name)
            for name in allowed_payload
        )
    ):
        raise ValueError(
            f"{source} HTTP hook allowedEnvVars must contain at most {MAX_HOOK_HEADERS} environment variable names."
        )
    timeout_ms = _parse_hook_timeout(
        payload,
        source,
        default_ms=_default_hook_timeout_ms(event),
    )
    return ProjectHook(
        event=cast(HookEvent, event),
        matcher=matcher,
        command="",
        timeout_ms=timeout_ms,
        source=source,
        handler_type="http",
        url=normalized_url,
        headers=tuple(headers),
        allowed_env_vars=tuple(dict.fromkeys(cast(list[str], allowed_payload))),
    )


def _parse_mcp_tool_hook(
    event: str, matcher: str, payload: dict[str, object], source: str
) -> ProjectHook:
    if "async" in payload or "asyncRewake" in payload:
        raise ValueError(f"{source} MCP tool hooks do not support async or asyncRewake.")
    server = payload.get("server")
    tool = payload.get("tool")
    if not isinstance(server, str) or not MCP_NAME_PATTERN.fullmatch(server):
        raise ValueError(
            f"{source} MCP hook server must use 1-64 letters, digits, dots, underscores, or hyphens."
        )
    if not isinstance(tool, str) or not MCP_NAME_PATTERN.fullmatch(tool):
        raise ValueError(
            f"{source} MCP hook tool must use 1-64 letters, digits, dots, underscores, or hyphens."
        )
    input_payload = payload.get("input", {})
    if not isinstance(input_payload, dict):
        raise ValueError(f"{source} MCP hook input must be an object.")
    try:
        encoded = json.dumps(input_payload, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{source} MCP hook input must be JSON serializable: {error}.") from error
    if len(encoded) > 50_000:
        raise ValueError(f"{source} MCP hook input exceeds 50000 characters.")
    return ProjectHook(
        event=cast(HookEvent, event),
        matcher=matcher,
        command="",
        timeout_ms=_parse_hook_timeout(
            payload,
            source,
            default_ms=_default_hook_timeout_ms(event),
        ),
        source=source,
        handler_type="mcp_tool",
        mcp_server=server,
        mcp_tool=tool,
        mcp_input=input_payload,
    )


def _parse_model_hook(
    event: str,
    matcher: str,
    payload: dict[str, object],
    source: str,
    *,
    handler_type: Literal["prompt", "agent"],
) -> ProjectHook:
    if event not in PROMPT_HOOK_EVENTS:
        raise ValueError(
            f"{source} {event} hooks do not support {handler_type} handlers."
        )
    if "async" in payload or "asyncRewake" in payload:
        raise ValueError(
            f"{source} {handler_type} hooks do not support async or asyncRewake."
        )
    prompt = payload.get("prompt")
    if (
        not isinstance(prompt, str)
        or not prompt.strip()
        or len(prompt) > MAX_HOOK_PROMPT_CHARS
        or "\x00" in prompt
    ):
        raise ValueError(
            f"{source} hook prompt must contain 1-{MAX_HOOK_PROMPT_CHARS} characters."
        )
    model = payload.get("model")
    if model is not None and (
        not isinstance(model, str)
        or not model.strip()
        or len(model) > MAX_HOOK_MODEL_CHARS
        or any(not character.isprintable() for character in model)
    ):
        raise ValueError(
            f"{source} hook model must contain 1-{MAX_HOOK_MODEL_CHARS} printable characters."
        )
    continue_on_block = payload.get("continueOnBlock", False)
    if not isinstance(continue_on_block, bool):
        raise ValueError(f"{source} hook continueOnBlock must be a boolean.")
    return ProjectHook(
        event=cast(HookEvent, event),
        matcher=matcher,
        command="",
        timeout_ms=_parse_hook_timeout(
            payload,
            source,
            default_ms=60_000 if handler_type == "agent" else 30_000,
        ),
        source=source,
        handler_type=handler_type,
        prompt=prompt.strip(),
        model=model.strip() if isinstance(model, str) else None,
        continue_on_block=continue_on_block,
    )


def _parse_hook_timeout(
    payload: dict[str, object], source: str, *, default_ms: int = 600_000
) -> int:
    if "timeout" in payload and "timeout_ms" in payload:
        raise ValueError(f"{source} hook cannot define both timeout and timeout_ms.")
    timeout_seconds = payload.get("timeout")
    timeout_ms = payload.get("timeout_ms", default_ms)
    if timeout_seconds is not None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds < 0.1
            or timeout_seconds > 600
        ):
            raise ValueError(f"{source} hook timeout must be between 0.1 and 600 seconds.")
        timeout_ms = round(timeout_seconds * 1000)
    if (
        isinstance(timeout_ms, bool)
        or not isinstance(timeout_ms, int)
        or timeout_ms < 100
        or timeout_ms > 600_000
    ):
        raise ValueError(f"{source} hook timeout_ms must be between 100 and 600000.")
    return timeout_ms


def _default_hook_timeout_ms(event: str) -> int:
    return 1_500 if event == "SessionEnd" else 600_000


__all__ = ["parse_hook_handler"]
