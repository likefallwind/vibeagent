from __future__ import annotations

from .action_tool_aliases import CLAUDE_MCP_TOOL_NAME_PATTERN, profile_tool_names
from .tool_definitions import AGENT_TOOL_DEFINITIONS


KNOWN_TOOL_NAMES = frozenset(str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS)
MAX_TOOL_RESTRICTION_NAMES = 100


def parse_cli_tool_names(value: object) -> frozenset[str] | None:
    if value is None or value is True:
        return None
    if not isinstance(value, str):
        raise ValueError("--tools must be a comma-separated list, an empty string, or default.")
    text = value.strip()
    if text.lower() == "default":
        return None
    if not text:
        return frozenset()
    requested = [name.strip() for name in text.split(",")]
    if any(not name for name in requested):
        raise ValueError("--tools contains an empty tool name.")
    if len(requested) > MAX_TOOL_RESTRICTION_NAMES:
        raise ValueError(
            f"--tools may contain at most {MAX_TOOL_RESTRICTION_NAMES} names."
        )
    expanded = frozenset(
        tool_name
        for name in requested
        for tool_name in profile_tool_names(name)
    )
    unknown = sorted(
        name
        for name in expanded
        if name not in KNOWN_TOOL_NAMES
        and not CLAUDE_MCP_TOOL_NAME_PATTERN.fullmatch(name)
    )
    if unknown:
        raise ValueError(f"--tools references unknown tool(s): {', '.join(unknown)}.")
    return expanded


__all__ = ["parse_cli_tool_names"]
