from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

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

BASH_TOOL_NAMES = frozenset(
    {
        "run_command",
        "run_commands",
        "run_focused_test_commands",
        "run_session_verification",
        "run_suggested_checks",
        "start_command",
    }
)
FILE_EDIT_TOOL_NAMES = frozenset(
    {
        "append_file",
        "code_rename",
        "copy_dir",
        "copy_dirs",
        "copy_file",
        "copy_files",
        "create_dir",
        "create_dirs",
        "delete_empty_dir",
        "delete_empty_dirs",
        "delete_file",
        "delete_files",
        "edit_file",
        "insert_lines",
        "json_patch",
        "json_remove",
        "json_set",
        "move_dir",
        "move_dirs",
        "move_file",
        "move_files",
        "multi_edit_file",
        "patch_file",
        "patch_files",
        "python_rename",
        "regex_replace",
        "replace_lines",
        "replace_python_definition",
        "set_executable",
        "write_file",
        "write_files",
    }
)
FILE_READ_TOOL_NAMES = frozenset(
    {
        "code_definitions",
        "code_dependencies",
        "code_outline",
        "code_reference_contexts",
        "code_references",
        "config_check",
        "file_info",
        "find_files",
        "glob",
        "image_info",
        "list_files",
        "list_tree",
        "python_call_graph",
        "python_calls",
        "python_check",
        "python_definitions",
        "python_dependencies",
        "python_reference_contexts",
        "python_references",
        "python_symbols",
        "read_file",
        "read_file_context",
        "read_file_contexts",
        "read_file_ranges",
        "read_files",
        "repo_map",
        "search",
        "search_contexts",
        "tail_file",
        "view_image",
    }
)
CLAUDE_TOOL_ALIASES = {
    "Agent": frozenset({"delegate_task"}),
    "AskUserQuestion": frozenset({"ask_user"}),
    "Bash": BASH_TOOL_NAMES,
    "Edit": FILE_EDIT_TOOL_NAMES,
    "Read": FILE_READ_TOOL_NAMES,
    "WebFetch": frozenset({"web_fetch"}),
    "Write": FILE_EDIT_TOOL_NAMES,
}


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


def format_project_permissions_for_prompt(workspace: RunWorkspace) -> str:
    config = read_project_permissions(workspace)
    if config.error is not None:
        return f"Project permission configuration is invalid and tool calls will be denied: {config.error}"
    if not config.rules:
        return ""
    lines = [
        "Project permission rules (deny rules take precedence over ask, then allow):",
        "Allow rules skip side-effect approval only when project permissions were explicitly trusted for this run.",
    ]
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
    url = getattr(action, "url", None)
    if isinstance(url, str):
        return (url,)
    server = getattr(action, "server", None)
    name = getattr(action, "name", None)
    if isinstance(server, str) and isinstance(name, str):
        return (f"{server}/{name}",)
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
    aliases = CLAUDE_TOOL_ALIASES.get(rule_tool)
    if aliases is not None:
        return tool_name in aliases
    if rule_tool.startswith("mcp__") and tool_name == "mcp_call":
        parts = rule_tool.split("__", 2)
        return len(parts) == 3 and parts[1] == getattr(action, "server", None) and parts[2] == getattr(action, "name", None)
    return rule_tool == tool_name


def _specifier_matches(
    rule: ProjectPermissionRule,
    tool_name: str,
    action: object,
    subjects: tuple[str, ...],
) -> bool:
    specifier = rule.specifier or ""
    if rule.tool == "WebFetch" and specifier.startswith("domain:"):
        hostname = urlsplit(str(getattr(action, "url", ""))).hostname or ""
        return _wildcard_matches(specifier.removeprefix("domain:"), hostname, path_mode=False)
    if not subjects:
        return False
    path_mode = rule.tool in {"Read", "Edit", "Write"} or tool_category(tool_name) in {"edit", "code"}
    matches = [_wildcard_matches(specifier, subject, path_mode=path_mode) for subject in subjects]
    return all(matches) if rule.effect == "allow" else any(matches)


def _wildcard_matches(pattern: str, value: str, *, path_mode: bool) -> bool:
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
