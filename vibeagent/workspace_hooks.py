from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from .action_tool_aliases import tool_name_candidates
from .plugin_runtime import (
    PluginComponentFile,
    enabled_plugin_component_files,
    expand_plugin_path_variables,
    inline_plugin_component,
    plugin_subprocess_environment,
    resolve_plugin_component_user_config,
)
from .plugin_store import enabled_plugin_manifests
from .workspace_core import RunWorkspace
from .workspace_hook_handlers import parse_hook_handler
from .workspace_hook_types import HOOK_EVENTS, HookEvent, ProjectHook, ProjectHooks
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes
from .workspace_settings_sources import claude_settings_files, project_config_file


HOOK_CONFIG_PATH = ".vibeagent/hooks.json"
MAX_HOOK_CONFIG_BYTES = 128_000
MAX_HOOKS = 100
MAX_HOOK_MATCHER_CHARS = 500


def read_project_hooks(workspace: RunWorkspace) -> ProjectHooks:
    hooks: list[ProjectHook] = []
    sources: list[str] = []
    try:
        configs = (
            *claude_settings_files(workspace),
            project_config_file(workspace, HOOK_CONFIG_PATH),
        )
        for config in configs:
            if not config.path.exists():
                continue
            sources.append(config.source)
            payload = _read_hook_config(config.boundary, config.path, config.source)
            hook_payload = (
                payload.get("hooks")
                if config.source != HOOK_CONFIG_PATH
                else payload.get("hooks", payload)
            )
            if hook_payload is None:
                continue
            if not isinstance(hook_payload, dict):
                raise ValueError(f"{config.source} hooks must be an object.")
            hooks.extend(_parse_hook_events(hook_payload, config.source))
            if len(hooks) > MAX_HOOKS:
                raise ValueError(
                    f"Workspace hook configuration exceeds {MAX_HOOKS} hooks."
                )
        for component in enabled_plugin_component_files(workspace, "hook"):
            source = f"{component.source}:{component.relative_path}"
            sources.append(source)
            payload = _read_hook_config(component.plugin_root, component.path, source)
            _append_plugin_hooks(hooks, workspace, component, payload, source)
            if len(hooks) > MAX_HOOKS:
                raise ValueError(f"Workspace and plugin hooks exceed {MAX_HOOKS} hooks.")
        for manifest in enabled_plugin_manifests(workspace.root):
            if manifest.inline_hooks is None:
                continue
            component = inline_plugin_component(manifest, "hook")
            source = f"{component.source}:{component.relative_path}#hooks"
            sources.append(source)
            _append_plugin_hooks(
                hooks,
                workspace,
                component,
                manifest.inline_hooks,
                source,
            )
            if len(hooks) > MAX_HOOKS:
                raise ValueError(f"Workspace and plugin hooks exceed {MAX_HOOKS} hooks.")
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        return ProjectHooks(hooks=(), sources=tuple(sources), error=str(error))
    return ProjectHooks(hooks=tuple(hooks), sources=tuple(sources))


def parse_inline_hooks(payload: dict[str, object], source: str) -> ProjectHooks:
    try:
        hooks = _parse_hook_events(payload, source)
        if len(hooks) > MAX_HOOKS:
            raise ValueError(f"{source} exceeds {MAX_HOOKS} hooks.")
    except ValueError as error:
        return ProjectHooks(sources=(source,), error=str(error))
    return ProjectHooks(hooks=tuple(hooks), sources=(source,))


def validate_inline_hooks(payload: dict[str, object], source: str) -> None:
    parsed = parse_inline_hooks(payload, source)
    if parsed.error is not None:
        raise ValueError(parsed.error)


def merge_project_hooks(base: ProjectHooks, extra: ProjectHooks | None) -> ProjectHooks:
    if extra is None:
        return base
    error = base.error or extra.error
    hooks = (*base.hooks, *extra.hooks)
    if len(hooks) > MAX_HOOKS:
        error = f"Combined hook configuration exceeds {MAX_HOOKS} hooks."
        hooks = ()
    return ProjectHooks(
        hooks=tuple(hooks),
        sources=tuple(dict.fromkeys((*base.sources, *extra.sources))),
        error=error,
    )


def subagent_project_hooks(config: ProjectHooks | None) -> ProjectHooks | None:
    if config is None:
        return None
    return replace(
        config,
        hooks=tuple(
            replace(hook, event="SubagentStop") if hook.event == "Stop" else hook
            for hook in config.hooks
        ),
    )


def _append_plugin_hooks(
    hooks: list[ProjectHook],
    workspace: RunWorkspace,
    component: PluginComponentFile,
    payload: dict[str, object],
    source: str,
) -> None:
    hook_payload = payload.get("hooks", payload)
    if not isinstance(hook_payload, dict):
        raise ValueError(f"{source} hooks must be an object.")
    plugin_hooks = _parse_hook_events(hook_payload, source)
    user_config = resolve_plugin_component_user_config(workspace, component)
    hooks.extend(
        replace(
            hook,
            command=expand_plugin_path_variables(
                hook.command,
                component,
                workspace,
                sensitive="environment",
                user_config=user_config,
            ),
            environment=plugin_subprocess_environment(
                workspace,
                component,
                user_config=user_config,
            ),
        )
        for hook in plugin_hooks
    )


def matching_project_hooks(
    config: ProjectHooks, event: HookEvent, tool_name: str, action: object | None = None
) -> list[ProjectHook]:
    names = tool_name_candidates(tool_name, action)
    return [
        hook
        for hook in config.hooks
        if hook.event == event
        and any(re.search(hook.matcher, name) is not None for name in names)
    ]


def matching_lifecycle_hooks(
    config: ProjectHooks, event: HookEvent, matcher_value: str
) -> list[ProjectHook]:
    return [
        hook
        for hook in config.hooks
        if hook.event == event and re.search(hook.matcher, matcher_value) is not None
    ]


def _read_hook_config(root: Path, path: Path, source: str) -> dict[str, object]:
    if has_symlink_component(root, path):
        raise ValueError(f"{source} contains a symbolic link.")
    raw = read_regular_file_bytes(path, max_bytes=MAX_HOOK_CONFIG_BYTES, label=source)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{source} must contain a JSON object.")
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
                raise ValueError(
                    f"{source} hook event {event_name} entries must be objects."
                )
            matcher = (
                ".*"
                if event_name in {"CwdChanged", "TaskCreated", "TaskCompleted"}
                else group.get("matcher", ".*")
            )
            if not isinstance(matcher, str) or len(matcher) > MAX_HOOK_MATCHER_CHARS:
                raise ValueError(
                    f"{source} hook matcher must be a string of at most {MAX_HOOK_MATCHER_CHARS} characters."
                )
            try:
                re.compile(matcher)
            except re.error as error:
                raise ValueError(
                    f"{source} hook matcher is invalid: {error}"
                ) from error
            commands = group.get("hooks")
            if not isinstance(commands, list) or not commands:
                raise ValueError(
                    f"{source} hook matcher {matcher!r} requires a non-empty hooks list."
                )
            for hook_payload in commands:
                parsed.append(parse_hook_handler(event_name, matcher, hook_payload, source))
    return parsed


__all__ = [
    "HOOK_EVENTS",
    "HookEvent",
    "ProjectHook",
    "ProjectHooks",
    "matching_lifecycle_hooks",
    "matching_project_hooks",
    "merge_project_hooks",
    "parse_inline_hooks",
    "read_project_hooks",
    "subagent_project_hooks",
    "validate_inline_hooks",
]
