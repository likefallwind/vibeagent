from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from .action_tool_aliases import tool_name_candidates
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


HookEvent = Literal["PreToolUse", "PostToolUse", "PostToolUseFailure"]
HOOK_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PostToolUseFailure"})
HOOK_CONFIG_PATHS = (
    (".claude/settings.json", True),
    (".claude/settings.local.json", True),
    (".vibeagent/hooks.json", False),
)
MAX_HOOK_CONFIG_BYTES = 128_000
MAX_HOOKS = 100
MAX_HOOK_COMMAND_CHARS = 4_000
MAX_HOOK_MATCHER_CHARS = 500


@dataclass(frozen=True)
class ProjectHook:
    event: HookEvent
    matcher: str
    command: str
    timeout_ms: int
    source: str


@dataclass(frozen=True)
class ProjectHooks:
    hooks: tuple[ProjectHook, ...] = ()
    sources: tuple[str, ...] = ()
    error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.hooks) or self.error is not None


def read_project_hooks(workspace: RunWorkspace) -> ProjectHooks:
    hooks: list[ProjectHook] = []
    sources: list[str] = []
    try:
        for relative_path, nested in HOOK_CONFIG_PATHS:
            path = workspace.root / relative_path
            if not path.exists():
                continue
            sources.append(relative_path)
            payload = _read_hook_config(workspace.root, path)
            hook_payload = payload.get("hooks") if nested else payload.get("hooks", payload)
            if hook_payload is None:
                continue
            if not isinstance(hook_payload, dict):
                raise ValueError(f"{relative_path} hooks must be an object.")
            hooks.extend(_parse_hook_events(hook_payload, relative_path))
            if len(hooks) > MAX_HOOKS:
                raise ValueError(f"Project hook configuration exceeds {MAX_HOOKS} command hooks.")
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        return ProjectHooks(hooks=(), sources=tuple(sources), error=str(error))
    return ProjectHooks(hooks=tuple(hooks), sources=tuple(sources))


def matching_project_hooks(config: ProjectHooks, event: HookEvent, tool_name: str, action: object | None = None) -> list[ProjectHook]:
    names = tool_name_candidates(tool_name, action)
    return [
        hook
        for hook in config.hooks
        if hook.event == event and any(re.search(hook.matcher, name) is not None for name in names)
    ]


def _read_hook_config(root: Path, path: Path) -> dict[str, object]:
    relative = path.relative_to(root).as_posix()
    if has_symlink_component(root, path):
        raise ValueError(f"{relative} contains a symbolic link.")
    raw = read_regular_file_bytes(path, max_bytes=MAX_HOOK_CONFIG_BYTES, label=relative)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relative} must contain a JSON object.")
    return payload


def _parse_hook_events(payload: dict[str, object], source: str) -> list[ProjectHook]:
    parsed: list[ProjectHook] = []
    for event_name, groups in payload.items():
        if event_name not in HOOK_EVENTS:
            continue
        if not isinstance(groups, list):
            raise ValueError(f"{source} hook event {event_name} must be a list.")
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError(f"{source} hook event {event_name} entries must be objects.")
            matcher = group.get("matcher", ".*")
            if not isinstance(matcher, str) or len(matcher) > MAX_HOOK_MATCHER_CHARS:
                raise ValueError(f"{source} hook matcher must be a string of at most {MAX_HOOK_MATCHER_CHARS} characters.")
            try:
                re.compile(matcher)
            except re.error as error:
                raise ValueError(f"{source} hook matcher is invalid: {error}") from error
            commands = group.get("hooks")
            if not isinstance(commands, list) or not commands:
                raise ValueError(f"{source} hook matcher {matcher!r} requires a non-empty hooks list.")
            for command_hook in commands:
                parsed.append(_parse_command_hook(event_name, matcher, command_hook, source))
    return parsed


def _parse_command_hook(event: str, matcher: str, payload: object, source: str) -> ProjectHook:
    if not isinstance(payload, dict) or payload.get("type") != "command":
        raise ValueError(f"{source} supports command hooks only.")
    command = payload.get("command")
    if not isinstance(command, str) or not command.strip() or len(command) > MAX_HOOK_COMMAND_CHARS:
        raise ValueError(f"{source} hook command must contain 1-{MAX_HOOK_COMMAND_CHARS} characters.")
    timeout_ms = payload.get("timeout_ms", 30_000)
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or timeout_ms < 100 or timeout_ms > 120_000:
        raise ValueError(f"{source} hook timeout_ms must be between 100 and 120000.")
    return ProjectHook(
        event=cast(HookEvent, event),
        matcher=matcher,
        command=command.strip(),
        timeout_ms=timeout_ms,
        source=source,
    )
