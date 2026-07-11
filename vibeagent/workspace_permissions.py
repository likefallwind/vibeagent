from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

from .action_tool_aliases import tool_name_candidates
from .tool_catalog_core import tool_category
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


PermissionEffect = Literal["deny", "ask", "allow"]
PERMISSION_EFFECTS: tuple[PermissionEffect, ...] = ("deny", "ask", "allow")
PERMISSION_CONFIG_PATHS = (
    (".vibeagent/permissions.json", False),
    (".claude/settings.local.json", True),
    (".claude/settings.json", True),
)
MAX_PERMISSION_CONFIG_BYTES = 128_000
MAX_PERMISSION_RULES = 200
MAX_PERMISSION_RULE_CHARS = 1_000
RULE_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_.:-]*)(?:\((.*)\))?$")
PATH_PERMISSION_RULE_TOOLS = frozenset({"Edit", "Glob", "LS", "MultiEdit", "NotebookEdit", "NotebookRead", "Read", "Write"})


@dataclass(frozen=True)
class ProjectPermissionRule:
    effect: PermissionEffect
    tool: str
    specifier: str | None
    raw: str
    source: str


@dataclass(frozen=True)
class ProjectPermissions:
    rules: tuple[ProjectPermissionRule, ...] = ()
    sources: tuple[str, ...] = ()
    error: str | None = None
    allow_rules_trusted: bool = False
    trusted_allow_sources: tuple[str, ...] = ()

    @property
    def enabled(self) -> bool:
        return bool(self.rules) or self.error is not None


@dataclass(frozen=True)
class PermissionRuleMatch:
    effect: PermissionEffect
    rule: ProjectPermissionRule
    subjects: tuple[str, ...]


def read_project_permissions(workspace: RunWorkspace) -> ProjectPermissions:
    rules: list[ProjectPermissionRule] = []
    sources: list[str] = []
    try:
        for relative_path, nested in PERMISSION_CONFIG_PATHS:
            path = workspace.root / relative_path
            if not path.exists():
                continue
            payload = _read_permission_config(workspace.root, path)
            permission_payload = payload.get("permissions") if nested else payload.get("permissions", payload)
            if permission_payload is None:
                continue
            sources.append(relative_path)
            if not isinstance(permission_payload, dict):
                raise ValueError(f"{relative_path} permissions must be an object.")
            rules.extend(_parse_permission_rules(permission_payload, relative_path))
            if len(rules) > MAX_PERMISSION_RULES:
                raise ValueError(f"Project permissions exceed {MAX_PERMISSION_RULES} rules.")
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        return ProjectPermissions(sources=tuple(sources), error=str(error))
    return ProjectPermissions(rules=tuple(rules), sources=tuple(sources))


def read_project_permissions_from_root(root: str | Path) -> ProjectPermissions:
    resolved = Path(root).resolve()
    workspace = RunWorkspace(root=resolved, run_id="", session_dir=resolved / ".vibeagent/sessions")
    return read_project_permissions(workspace)


def permission_rules_from_values(
    effect: PermissionEffect,
    values: list[str] | tuple[str, ...],
    source: str,
) -> tuple[ProjectPermissionRule, ...]:
    return tuple(_parse_permission_rules({effect: list(values)}, source))


def merge_project_permissions(
    base: ProjectPermissions,
    extra: ProjectPermissions | None,
) -> ProjectPermissions:
    if extra is None or not extra.enabled:
        return base
    error = base.error or extra.error
    return ProjectPermissions(
        rules=base.rules + extra.rules,
        sources=tuple(dict.fromkeys((*base.sources, *extra.sources))),
        error=error,
        allow_rules_trusted=base.allow_rules_trusted,
        trusted_allow_sources=tuple(dict.fromkeys((*base.trusted_allow_sources, *extra.trusted_allow_sources))),
    )


def format_project_permissions_for_prompt(workspace: RunWorkspace) -> str:
    config = read_project_permissions(workspace)
    return format_permissions_for_prompt(config)


def format_permissions_for_prompt(config: ProjectPermissions) -> str:
    if config.error is not None:
        return f"Project permission configuration is invalid and tool calls will be denied: {config.error}"
    if not config.rules:
        return ""
    lines = [
        "Permission rules (deny rules take precedence over ask, then allow):",
        "Allow rules skip side-effect approval only when project permissions were explicitly trusted for this run.",
    ]
    if config.trusted_allow_sources:
        sources = ", ".join(config.trusted_allow_sources)
        lines.append(f"Allow rules from these sources are trusted for this run: {sources}.")
    lines.extend(f"- {rule.effect}: {rule.raw} ({rule.source})" for rule in config.rules)
    return "\n".join(lines)


def match_project_permission(
    config: ProjectPermissions,
    tool_name: str,
    action: object,
) -> PermissionRuleMatch | None:
    subjects = permission_subjects(action)
    for effect in PERMISSION_EFFECTS:
        for rule in config.rules:
            if rule.effect != effect or not _tool_matches(rule.tool, tool_name, action):
                continue
            if rule.specifier is None or _specifier_matches(rule, tool_name, action, subjects):
                return PermissionRuleMatch(effect=effect, rule=rule, subjects=subjects)
    return None


def permission_subjects(action: object) -> tuple[str, ...]:
    command = getattr(action, "command", None)
    if isinstance(command, str):
        return (command,)
    commands = getattr(action, "commands", None)
    if isinstance(commands, list):
        values = tuple(str(item.command) for item in commands if isinstance(getattr(item, "command", None), str))
        if values:
            return values
    files = getattr(action, "files", None)
    if isinstance(files, list):
        values = tuple(str(item.path) for item in files if isinstance(getattr(item, "path", None), str))
        if values:
            return values
    paths = getattr(action, "paths", None)
    if isinstance(paths, list) and all(isinstance(item, str) for item in paths):
        return tuple(paths)
    transfers = getattr(action, "transfers", None)
    if isinstance(transfers, list):
        values = tuple(
            value
            for item in transfers
            for value in (getattr(item, "source", None), getattr(item, "destination", None))
            if isinstance(value, str)
        )
        if values:
            return values
    source = getattr(action, "source", None)
    destination = getattr(action, "destination", None)
    if isinstance(source, str) and isinstance(destination, str):
        return source, destination
    path = getattr(action, "path", None)
    if isinstance(path, str):
        return (path,)
    pattern = getattr(action, "pattern", None)
    if isinstance(pattern, str):
        return (pattern,)
    query = getattr(action, "query", None)
    if isinstance(query, str):
        return (query,)
    url = getattr(action, "url", None)
    if isinstance(url, str):
        return (url,)
    server = getattr(action, "server", None)
    name = getattr(action, "name", None)
    if isinstance(server, str) and isinstance(name, str):
        return (f"{server}/{name}",)
    process_id = getattr(action, "process_id", None)
    if isinstance(process_id, str):
        return (process_id,)
    return ()


def _read_permission_config(root: Path, path: Path) -> dict[str, object]:
    relative = path.relative_to(root).as_posix()
    if has_symlink_component(root, path):
        raise ValueError(f"{relative} contains a symbolic link.")
    raw = read_regular_file_bytes(path, max_bytes=MAX_PERMISSION_CONFIG_BYTES, label=relative)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relative} must contain a JSON object.")
    return payload


def _parse_permission_rules(payload: dict[str, object], source: str) -> list[ProjectPermissionRule]:
    parsed: list[ProjectPermissionRule] = []
    for effect in PERMISSION_EFFECTS:
        values = payload.get(effect, [])
        if not isinstance(values, list):
            raise ValueError(f"{source} permissions.{effect} must be a list.")
        for value in values:
            if not isinstance(value, str) or not value.strip() or len(value) > MAX_PERMISSION_RULE_CHARS:
                raise ValueError(f"{source} permissions.{effect} entries must contain 1-{MAX_PERMISSION_RULE_CHARS} characters.")
            raw = value.strip()
            match = RULE_PATTERN.fullmatch(raw)
            if match is None:
                raise ValueError(f"{source} permission rule is invalid: {raw}")
            tool, specifier = match.groups()
            parsed.append(
                ProjectPermissionRule(
                    effect=cast(PermissionEffect, effect),
                    tool=tool,
                    specifier=specifier,
                    raw=raw,
                    source=source,
                )
            )
    return parsed


def _tool_matches(rule_tool: str, tool_name: str, action: object) -> bool:
    action_type = getattr(action, "type", None)
    if rule_tool.startswith("mcp__") and (tool_name == "mcp_call" or action_type == "mcp_call"):
        parts = rule_tool.split("__", 2)
        return len(parts) == 3 and parts[1] == getattr(action, "server", None) and parts[2] == getattr(action, "name", None)
    return rule_tool in tool_name_candidates(tool_name, action)


def _specifier_matches(
    rule: ProjectPermissionRule,
    tool_name: str,
    action: object,
    subjects: tuple[str, ...],
) -> bool:
    specifier = rule.specifier or ""
    if _specifier_is_web_fetch_domain(rule.tool, tool_name, action, specifier):
        hostname = urlsplit(str(getattr(action, "url", ""))).hostname or ""
        return wildcard_matches(specifier.removeprefix("domain:"), hostname, path_mode=False)
    if not subjects:
        return False
    path_mode = _specifier_uses_path_matching(rule.tool, tool_name, action)
    matches = [wildcard_matches(specifier, subject, path_mode=path_mode) for subject in subjects]
    return all(matches) if rule.effect == "allow" else any(matches)


def _specifier_is_web_fetch_domain(rule_tool: str, tool_name: str, action: object, specifier: str) -> bool:
    names = tool_name_candidates(tool_name, action)
    return specifier.startswith("domain:") and "WebFetch" in names and rule_tool in names


def _specifier_uses_path_matching(rule_tool: str, tool_name: str, action: object) -> bool:
    action_type = getattr(action, "type", None)
    return (
        rule_tool in PATH_PERMISSION_RULE_TOOLS
        or tool_category(tool_name) in {"edit", "code"}
        or (isinstance(action_type, str) and tool_category(action_type) in {"edit", "code"})
    )


def wildcard_matches(pattern: str, value: str, *, path_mode: bool) -> bool:
    normalized_pattern = pattern.replace("\\", "/")
    normalized_value = value.replace("\\", "/")
    if path_mode:
        normalized_pattern = normalized_pattern.removeprefix("./").removeprefix("/")
        normalized_value = normalized_value.removeprefix("./").removeprefix("/")
    if normalized_pattern.endswith(":*"):
        normalized_pattern = f"{normalized_pattern[:-2]} *"
    optional_trailing_arguments = not path_mode and normalized_pattern.endswith(" *")
    if optional_trailing_arguments:
        normalized_pattern = normalized_pattern[:-2]
    regex: list[str] = ["^"]
    index = 0
    while index < len(normalized_pattern):
        character = normalized_pattern[index]
        if character == "*":
            if path_mode and index + 1 < len(normalized_pattern) and normalized_pattern[index + 1] == "*":
                if index + 2 < len(normalized_pattern) and normalized_pattern[index + 2] == "/":
                    regex.append("(?:.*/)?")
                    index += 3
                else:
                    regex.append(".*")
                    index += 2
                continue
            regex.append("[^/]*" if path_mode else ".*")
        elif character == "?":
            regex.append("[^/]" if path_mode else ".")
        else:
            regex.append(re.escape(character))
        index += 1
    if optional_trailing_arguments:
        regex.append("(?: .*)?")
    regex.append("$")
    return re.fullmatch("".join(regex), normalized_value) is not None
