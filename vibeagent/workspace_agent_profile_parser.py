from __future__ import annotations

import json
from pathlib import Path
import re

from .agent_profile_frontmatter import parse_agent_frontmatter
from .action_tool_aliases import CLAUDE_MCP_TOOL_NAME_PATTERN, profile_tool_names
from .action_tool_alias_sets import CLAUDE_TOOL_ACTION_ALIASES
from .agent_delegate_policy import (
    CODE_DELEGATE_EXCLUDED_TOOL_NAMES,
    DELEGATE_TOOL_NAMES,
    NESTED_DELEGATE_TOOL_NAMES,
    READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES,
)
from .tool_catalog_core import APPROVAL_REQUIRED_TOOL_NAMES
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .workspace_agent_profile_extended_fields import (
    parse_background,
    parse_color,
    parse_hooks,
    parse_initial_prompt,
    parse_mcp_servers,
    parse_permission_mode,
)
from .workspace_metadata_files import unquote_scalar
from .workspace_skills import SKILL_NAME_PATTERN


AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
AGENT_REFERENCE_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9]):)?[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
)
AGENT_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
AGENT_EFFORT_LEVELS = frozenset({"low", "medium", "high", "xhigh", "max"})
MAX_AGENT_PROFILE_SKILLS = 10
MAX_AGENT_TURNS = 50
AGENT_MEMORY_SCOPES = frozenset({"user", "project", "local"})
KNOWN_TOOL_NAMES = frozenset(str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS) | frozenset(
    CLAUDE_TOOL_ACTION_ALIASES.values()
)
DYNAMIC_AGENT_FIELDS = frozenset(
    {
        "name",
        "description",
        "prompt",
        "model",
        "effort",
        "mode",
        "tools",
        "disallowedTools",
        "maxTurns",
        "skills",
        "memory",
        "isolation",
        "permissionMode",
        "mcpServers",
        "hooks",
        "initialPrompt",
        "background",
        "color",
    }
)


def parse_agent_content(path: Path, content: str) -> tuple[dict[str, object], str]:
    metadata, body = parse_agent_frontmatter(content)
    return _normalize_agent_profile(path.stem, metadata, body, require_matching_name=True)


def parse_agent_mapping(name: str, payload: dict[str, object]) -> tuple[dict[str, object], str]:
    unknown = sorted(str(field) for field in payload if field not in DYNAMIC_AGENT_FIELDS)
    if unknown:
        raise ValueError(f"Agent profile contains unknown field(s): {', '.join(unknown)}.")
    declared_name = payload.get("name")
    if declared_name is not None and declared_name != name:
        raise ValueError("Agent profile name must match its --agents object key.")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        raise ValueError("Agent profile requires a string prompt field.")
    metadata = {field: value for field, value in payload.items() if field != "prompt"}
    metadata["name"] = name
    return _normalize_agent_profile(name, metadata, prompt, require_matching_name=False)


def _normalize_agent_profile(
    expected_name: str,
    metadata: dict[str, object],
    body: str,
    *,
    require_matching_name: bool,
) -> tuple[dict[str, object], str]:
    raw_name = metadata.get("name", "")
    raw_description = metadata.get("description", "")
    if not isinstance(raw_name, str) or not isinstance(raw_description, str):
        raise ValueError("Agent profile name and description fields must be strings.")
    name = raw_name.strip()
    description = raw_description.strip()
    mode = str(metadata.get("mode", "explore")).strip().lower()
    model = _parse_model(metadata.get("model"))
    effort = _parse_effort(metadata.get("effort"))
    if not name or not description:
        raise ValueError("Agent profile frontmatter requires non-empty name and description fields.")
    if not AGENT_NAME_PATTERN.fullmatch(name):
        raise ValueError("Agent profile frontmatter name is invalid.")
    if require_matching_name and name != expected_name:
        raise ValueError(f"Agent profile name {name!r} does not match filename {expected_name!r}.")
    if mode not in {"explore", "code"}:
        raise ValueError("Agent profile mode must be explore or code.")
    tools = _parse_tool_names(metadata.get("tools"), "tools")
    disallowed_tools = (
        _parse_tool_names(metadata.get("disallowedTools"), "disallowedTools", allow_empty=True)
        or frozenset()
    )
    _validate_agent_tools(mode, tools)
    _validate_known_tools(disallowed_tools, "disallowedTools")
    max_turns = _parse_max_turns(metadata.get("maxTurns"))
    skills = _parse_skill_names(metadata.get("skills"))
    memory = _parse_memory_scope(metadata.get("memory"))
    isolation = _parse_isolation(metadata.get("isolation"))
    permission_mode = parse_permission_mode(metadata.get("permissionMode"))
    mcp_servers = parse_mcp_servers(metadata.get("mcpServers"))
    hooks = parse_hooks(metadata.get("hooks"), f"agent:{name}#hooks")
    initial_prompt = parse_initial_prompt(metadata.get("initialPrompt"))
    background = parse_background(metadata.get("background"))
    color = parse_color(metadata.get("color"))
    if not body.strip():
        raise ValueError("Agent profile body must contain a non-empty system prompt.")
    return {
        "name": name,
        "description": " ".join(description.split())[:500],
        "mode": mode,
        "model": model,
        "effort": effort,
        "tools": sorted(tools) if tools is not None else None,
        "disallowed_tools": sorted(disallowed_tools),
        "max_turns": max_turns,
        "skills": list(skills),
        "memory": memory,
        "isolation": isolation,
        "permission_mode": permission_mode,
        "mcp_servers": mcp_servers,
        "hooks": hooks,
        "initial_prompt": initial_prompt,
        "background": background,
        "color": color,
    }, body.strip()


def _parse_model(value: object) -> str | None:
    if value is None or not str(value).strip():
        return None
    model = str(value).strip()
    if not AGENT_MODEL_PATTERN.fullmatch(model):
        raise ValueError("Agent profile model must be a valid model ID or inherit.")
    return model


def _parse_effort(value: object) -> str | None:
    if value is None or not str(value).strip():
        return None
    effort = str(value).strip().lower()
    if effort not in AGENT_EFFORT_LEVELS:
        raise ValueError(
            "Agent profile effort must be low, medium, high, xhigh, or max."
        )
    return effort


def _parse_tool_names(
    value: object,
    field: str,
    *,
    allow_empty: bool = False,
) -> frozenset[str] | None:
    names = _parse_string_list(value, field)
    if names is None:
        return None
    normalized = frozenset(
        tool_name
        for name in names
        if name.strip()
        for tool_name in profile_tool_names(name.strip())
    )
    if not normalized and not allow_empty:
        raise ValueError(f"Agent profile {field} must not be empty when declared.")
    return normalized


def _parse_skill_names(value: object) -> tuple[str, ...]:
    names = _parse_string_list(value, "skills") or []
    if len(names) > MAX_AGENT_PROFILE_SKILLS:
        raise ValueError(f"Agent profile skills may contain at most {MAX_AGENT_PROFILE_SKILLS} names.")
    normalized: list[str] = []
    for name in names:
        skill_name = name.strip()
        if not SKILL_NAME_PATTERN.fullmatch(skill_name):
            raise ValueError(f"Agent profile skill name is invalid: {name}")
        if skill_name not in normalized:
            normalized.append(skill_name)
    return tuple(normalized)


def _parse_max_turns(value: object) -> int | None:
    if value is None or not str(value).strip():
        return None
    try:
        parsed = int(str(value).strip())
    except ValueError as error:
        raise ValueError("Agent profile maxTurns must be an integer.") from error
    if parsed < 1 or parsed > MAX_AGENT_TURNS:
        raise ValueError(f"Agent profile maxTurns must be between 1 and {MAX_AGENT_TURNS}.")
    return parsed


def _parse_memory_scope(value: object) -> str | None:
    if value is None or not str(value).strip():
        return None
    scope = str(value).strip().lower()
    if scope not in AGENT_MEMORY_SCOPES:
        raise ValueError("Agent profile memory must be user, project, or local.")
    return scope


def _parse_isolation(value: object) -> str | None:
    if value is None or not str(value).strip():
        return None
    isolation = str(value).strip().lower()
    if isolation != "worktree":
        raise ValueError("Agent profile isolation must be worktree.")
    return isolation


def _parse_string_list(value: object, field: str) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ValueError(f"Agent profile {field} list must contain strings only.")
        return list(value)
    if not isinstance(value, str):
        raise ValueError(f"Agent profile {field} must be a string or string list.")
    if not value.strip():
        return None
    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text.replace("'", '"'))
        except json.JSONDecodeError as error:
            if not text.endswith("]"):
                raise ValueError(
                    f"Agent profile {field} must be a comma-separated or inline list: {error}"
                ) from error
            parsed = [unquote_scalar(item.strip()) for item in text[1:-1].split(",") if item.strip()]
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError(f"Agent profile {field} list must contain strings only.")
        return parsed
    return text.split(",")


def _validate_agent_tools(mode: str, tools: frozenset[str] | None) -> None:
    if tools is None:
        return
    _validate_known_tools(tools, "tools")
    forbidden = sorted(tools & CODE_DELEGATE_EXCLUDED_TOOL_NAMES)
    if forbidden:
        raise ValueError(f"Agent profile references forbidden tool(s): {', '.join(forbidden)}.")
    if mode == "explore":
        unavailable = sorted(
            name
            for name in tools
            if (
                name not in DELEGATE_TOOL_NAMES
                and name not in NESTED_DELEGATE_TOOL_NAMES
                and name != "finish"
                and name not in READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES
            ) or name in APPROVAL_REQUIRED_TOOL_NAMES
        )
        if unavailable:
            raise ValueError(f"Explore agent profile references non-read-only tool(s): {', '.join(unavailable)}.")


def _validate_known_tools(tools: frozenset[str], field: str) -> None:
    unknown = sorted(
        name
        for name in tools
        if name not in KNOWN_TOOL_NAMES and not CLAUDE_MCP_TOOL_NAME_PATTERN.fullmatch(name)
    )
    if unknown:
        raise ValueError(f"Agent profile {field} references unknown tool(s): {', '.join(unknown)}.")


__all__ = ["AGENT_NAME_PATTERN", "parse_agent_content", "parse_agent_mapping"]
