from __future__ import annotations

import json

from .mcp_config import MCP_NAME_PATTERN
from .workspace_hooks import validate_inline_hooks


AGENT_PERMISSION_MODES = frozenset(
    {"default", "acceptEdits", "auto", "dontAsk", "bypassPermissions", "plan"}
)
AGENT_COLORS = frozenset(
    {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"}
)
MAX_AGENT_INITIAL_PROMPT_BYTES = 64_000
MAX_AGENT_MCP_SERVERS = 20


def parse_permission_mode(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Agent profile permissionMode must be a string.")
    mode = value.strip()
    if mode == "manual":
        mode = "default"
    if mode not in AGENT_PERMISSION_MODES:
        choices = ", ".join(sorted((*AGENT_PERMISSION_MODES, "manual")))
        raise ValueError(f"Agent profile permissionMode must be one of: {choices}.")
    return mode


def parse_background(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError("Agent profile background must be a boolean.")
    return value


def parse_color(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value.strip() not in AGENT_COLORS:
        raise ValueError(
            "Agent profile color must be red, blue, green, yellow, purple, orange, pink, or cyan."
        )
    return value.strip()


def parse_initial_prompt(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Agent profile initialPrompt must be a non-empty string.")
    prompt = value.strip()
    if len(prompt.encode("utf-8")) > MAX_AGENT_INITIAL_PROMPT_BYTES:
        raise ValueError(
            f"Agent profile initialPrompt exceeds {MAX_AGENT_INITIAL_PROMPT_BYTES} bytes."
        )
    return prompt


def parse_mcp_servers(value: object) -> list[object]:
    if value is None:
        return []
    parsed = _structured_value(value, "mcpServers")
    if not isinstance(parsed, list):
        raise ValueError("Agent profile mcpServers must be a list.")
    if len(parsed) > MAX_AGENT_MCP_SERVERS:
        raise ValueError(
            f"Agent profile mcpServers may contain at most {MAX_AGENT_MCP_SERVERS} entries."
        )
    names: set[str] = set()
    normalized: list[object] = []
    for entry in parsed:
        if isinstance(entry, str):
            name = entry.strip()
            if not MCP_NAME_PATTERN.fullmatch(name):
                raise ValueError(f"Agent profile MCP server name is invalid: {entry}")
            normalized_entry: object = name
        elif isinstance(entry, dict) and len(entry) == 1:
            name, definition = next(iter(entry.items()))
            if not isinstance(name, str) or not MCP_NAME_PATTERN.fullmatch(name):
                raise ValueError("Agent profile inline MCP server name is invalid.")
            if not isinstance(definition, dict):
                raise ValueError(
                    f"Agent profile inline MCP server {name!r} must contain an object."
                )
            normalized_entry = {name: _json_clone(definition, "mcpServers")}
        else:
            raise ValueError(
                "Agent profile mcpServers entries must be server names or one-key server objects."
            )
        if name in names:
            raise ValueError(f"Agent profile mcpServers contains duplicate server {name!r}.")
        names.add(name)
        normalized.append(normalized_entry)
    return normalized


def parse_hooks(value: object, source: str) -> dict[str, object] | None:
    if value is None:
        return None
    parsed = _structured_value(value, "hooks")
    if not isinstance(parsed, dict):
        raise ValueError("Agent profile hooks must be an object.")
    normalized = _json_clone(parsed, "hooks")
    assert isinstance(normalized, dict)
    validate_inline_hooks(normalized, source)
    return normalized


def _structured_value(value: object, field: str) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Agent profile {field} scalar form must contain valid JSON: {error}"
        ) from error


def _json_clone(value: object, field: str) -> object:
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Agent profile {field} must contain JSON-compatible values.") from error


__all__ = [
    "AGENT_COLORS",
    "AGENT_PERMISSION_MODES",
    "MAX_AGENT_INITIAL_PROMPT_BYTES",
    "MAX_AGENT_MCP_SERVERS",
    "parse_background",
    "parse_color",
    "parse_hooks",
    "parse_initial_prompt",
    "parse_mcp_servers",
    "parse_permission_mode",
]
