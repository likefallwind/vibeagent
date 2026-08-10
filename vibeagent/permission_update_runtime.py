from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import cast

from .agent_profile_permissions import PROFILE_ACCEPT_EDITS_RULES
from .cli_additional_directories import MAX_ADDITIONAL_DIRECTORIES
from .types import ApprovalPolicy
from .user_paths import user_home
from .workspace_core import RunWorkspace, normalize_additional_roots
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes
from .workspace_permissions import (
    MAX_PERMISSION_RULES,
    PermissionEffect,
    ProjectPermissionRule,
    ProjectPermissions,
    permission_rules_from_values,
)


MAX_SETTINGS_BYTES = 512_000
PERMISSION_UPDATE_LOCK = RLock()
SESSION_PERMISSION_SOURCE = "<PermissionRequest session>"
SESSION_ACCEPT_EDITS_SOURCE = "<PermissionRequest mode acceptEdits>"
DESTINATION_SOURCES = {
    "localSettings": ".claude/settings.local.json",
    "projectSettings": ".claude/settings.json",
    "userSettings": "~/.claude/settings.json",
}


@dataclass(frozen=True)
class PermissionUpdateApplication:
    workspace: RunWorkspace
    permissions: ProjectPermissions
    approval_policy: ApprovalPolicy
    applied: tuple[dict[str, object], ...] = ()
    warnings: tuple[str, ...] = ()


def apply_permission_updates(
    workspace: RunWorkspace,
    permissions: ProjectPermissions,
    approval_policy: ApprovalPolicy,
    entries: tuple[dict[str, object], ...],
    *,
    bypass_available: bool,
) -> PermissionUpdateApplication:
    if not entries:
        return PermissionUpdateApplication(workspace, permissions, approval_policy)
    with PERMISSION_UPDATE_LOCK:
        settings_payloads = _load_target_settings(workspace, entries)
        current_rules = list(permissions.rules)
        trusted_sources = list(permissions.trusted_allow_sources)
        additional_roots = list(workspace.additional_roots)
        next_policy = approval_policy
        applied: list[dict[str, object]] = []
        warnings: list[str] = []
        for entry in entries:
            destination = str(entry["destination"])
            source = DESTINATION_SOURCES.get(destination, SESSION_PERMISSION_SOURCE)
            entry_type = str(entry["type"])
            if entry_type in {"addRules", "replaceRules", "removeRules"}:
                _apply_rules_to_runtime(current_rules, trusted_sources, entry, source)
                _apply_rules_to_settings(settings_payloads.get(destination), entry)
            elif entry_type == "setMode":
                mode = str(entry["mode"])
                if mode == "bypassPermissions" and not bypass_available:
                    warnings.append(
                        "Ignored bypassPermissions because this session did not start with bypass permission available."
                    )
                    continue
                next_policy = _apply_mode_to_runtime(
                    current_rules,
                    trusted_sources,
                    mode,
                )
                _apply_mode_to_settings(settings_payloads.get(destination), mode)
            else:
                additional_roots = _apply_directories_to_runtime(
                    workspace,
                    additional_roots,
                    entry,
                )
                _apply_directories_to_settings(
                    settings_payloads.get(destination),
                    entry,
                    workspace.root,
                )
            applied.append(entry)
        normalized_roots = normalize_additional_roots(
            workspace.root,
            tuple(additional_roots),
        )
        if len(normalized_roots) > MAX_ADDITIONAL_DIRECTORIES:
            raise ValueError(
                f"Permission updates exceed the {MAX_ADDITIONAL_DIRECTORIES}-directory session limit."
            )
        if len(current_rules) > MAX_PERMISSION_RULES:
            raise ValueError(
                f"Permission updates exceed the {MAX_PERMISSION_RULES}-rule session limit."
            )
        _write_target_settings(workspace, settings_payloads)
    effective_workspace = replace(workspace, additional_roots=normalized_roots)
    effective_permissions = ProjectPermissions(
        rules=tuple(current_rules),
        sources=tuple(
            dict.fromkeys(
                (
                    *permissions.sources,
                    *(
                        DESTINATION_SOURCES.get(
                            str(entry["destination"]), SESSION_PERMISSION_SOURCE
                        )
                        for entry in applied
                    ),
                )
            )
        ),
        error=permissions.error,
        allow_rules_trusted=permissions.allow_rules_trusted,
        trusted_allow_sources=tuple(dict.fromkeys(trusted_sources)),
        default_mode=permissions.default_mode,
        default_mode_source=permissions.default_mode_source,
        additional_directories=permissions.additional_directories,
    )
    return PermissionUpdateApplication(
        effective_workspace,
        effective_permissions,
        next_policy,
        tuple(applied),
        tuple(warnings),
    )


def _load_target_settings(
    workspace: RunWorkspace,
    entries: tuple[dict[str, object], ...],
) -> dict[str, dict[str, object]]:
    destinations = {
        str(entry["destination"])
        for entry in entries
        if entry["destination"] != "session"
    }
    payloads: dict[str, dict[str, object]] = {}
    payloads_by_path: dict[Path, dict[str, object]] = {}
    for destination in destinations:
        _root, path, _mode = _settings_location(workspace, destination)
        payload = payloads_by_path.get(path)
        if payload is None:
            payload = _read_settings(workspace, destination)
            payloads_by_path[path] = payload
        payloads[destination] = payload
    return payloads


def _settings_location(
    workspace: RunWorkspace,
    destination: str,
) -> tuple[Path, Path, int]:
    if destination == "userSettings":
        root = user_home().resolve()
        return root, root / ".claude/settings.json", 0o600
    name = "settings.local.json" if destination == "localSettings" else "settings.json"
    mode = 0o600 if destination == "localSettings" else 0o644
    return workspace.root, workspace.root / ".claude" / name, mode


def _read_settings(workspace: RunWorkspace, destination: str) -> dict[str, object]:
    root, path, _mode = _settings_location(workspace, destination)
    if not path.exists() and not path.is_symlink():
        return {}
    if has_symlink_component(root, path) or not path.is_file():
        raise ValueError(f"Permission update destination must be a regular file: {path}")
    raw = read_regular_file_bytes(path, max_bytes=MAX_SETTINGS_BYTES, label=str(path))
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Permission update destination is invalid: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"Permission update destination must contain an object: {path}")
    permission_payload = payload.get("permissions", {})
    if not isinstance(permission_payload, dict):
        raise ValueError(f"Permission update destination permissions must be an object: {path}")
    return dict(payload)


def _write_target_settings(
    workspace: RunWorkspace,
    payloads: dict[str, dict[str, object]],
) -> None:
    prepared: list[tuple[Path, Path, str, int]] = []
    seen_paths: set[Path] = set()
    try:
        for destination, payload in payloads.items():
            root, path, default_mode = _settings_location(workspace, destination)
            if path in seen_paths:
                continue
            seen_paths.add(path)
            if has_symlink_component(root, path):
                raise ValueError(f"Permission update destination contains a symbolic link: {path}")
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else default_mode
            encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            if len(encoded.encode("utf-8")) > MAX_SETTINGS_BYTES:
                raise ValueError(
                    f"Permission update destination exceeds {MAX_SETTINGS_BYTES} bytes: {path}"
                )
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
            ) as handle:
                handle.write(encoded)
                temporary = Path(handle.name)
            os.chmod(temporary, mode)
            prepared.append((temporary, path, destination, mode))
        for temporary, path, _destination, _mode in prepared:
            temporary.replace(path)
    finally:
        for temporary, _path, _destination, _mode in prepared:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _permission_payload(payload: dict[str, object]) -> dict[str, object]:
    permissions = payload.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        raise ValueError("Permission update destination permissions must be an object.")
    return permissions


def _rules_from_entry(entry: dict[str, object], source: str) -> tuple[ProjectPermissionRule, ...]:
    behavior = str(entry["behavior"])
    raw_rules = tuple(_raw_rule(rule) for rule in entry["rules"] if isinstance(rule, dict))
    return permission_rules_from_values(
        cast(PermissionEffect, behavior), raw_rules, source
    )


def _raw_rule(rule: dict[str, object]) -> str:
    tool = str(rule["toolName"])
    if "ruleContent" not in rule:
        return tool
    return f"{tool}({rule['ruleContent']})"


def _apply_rules_to_runtime(
    current: list[ProjectPermissionRule],
    trusted_sources: list[str],
    entry: dict[str, object],
    source: str,
) -> None:
    behavior = str(entry["behavior"])
    candidates = _rules_from_entry(entry, source)
    candidate_raw = {rule.raw for rule in candidates}
    if entry["type"] == "replaceRules":
        current[:] = [
            rule
            for rule in current
            if not (rule.source == source and rule.effect == behavior)
        ]
    elif entry["type"] == "removeRules":
        current[:] = [
            rule
            for rule in current
            if not (
                rule.source == source
                and rule.effect == behavior
                and rule.raw in candidate_raw
            )
        ]
        return
    existing = {(rule.effect, rule.raw, rule.source) for rule in current}
    current.extend(
        rule
        for rule in candidates
        if (rule.effect, rule.raw, rule.source) not in existing
    )
    if behavior == "allow" and source not in trusted_sources:
        trusted_sources.append(source)


def _apply_rules_to_settings(
    payload: dict[str, object] | None,
    entry: dict[str, object],
) -> None:
    if payload is None:
        return
    permissions = _permission_payload(payload)
    behavior = str(entry["behavior"])
    existing_value = permissions.get(behavior, [])
    if not isinstance(existing_value, list) or any(not isinstance(item, str) for item in existing_value):
        raise ValueError(f"Permission settings {behavior} must be an array of strings.")
    candidates = [_raw_rule(rule) for rule in entry["rules"] if isinstance(rule, dict)]
    if entry["type"] == "replaceRules":
        updated = candidates
    elif entry["type"] == "removeRules":
        removed = set(candidates)
        updated = [rule for rule in existing_value if rule not in removed]
    else:
        updated = list(dict.fromkeys((*existing_value, *candidates)))
    permissions[behavior] = updated


def _apply_mode_to_runtime(
    current: list[ProjectPermissionRule],
    trusted_sources: list[str],
    mode: str,
) -> ApprovalPolicy:
    current[:] = [rule for rule in current if rule.source != SESSION_ACCEPT_EDITS_SOURCE]
    if mode == "acceptEdits":
        rules = permission_rules_from_values(
            "allow",
            PROFILE_ACCEPT_EDITS_RULES,
            SESSION_ACCEPT_EDITS_SOURCE,
        )
        current.extend(rules)
        if SESSION_ACCEPT_EDITS_SOURCE not in trusted_sources:
            trusted_sources.append(SESSION_ACCEPT_EDITS_SOURCE)
        return "ask"
    if mode == "bypassPermissions":
        return "allow"
    if mode in {"auto", "dontAsk"}:
        return "dontAsk"
    if mode == "plan":
        return "plan"
    return "ask"


def _apply_mode_to_settings(payload: dict[str, object] | None, mode: str) -> None:
    if payload is not None:
        _permission_payload(payload)["defaultMode"] = "default" if mode == "manual" else mode


def _apply_directories_to_runtime(
    workspace: RunWorkspace,
    current: list[Path],
    entry: dict[str, object],
) -> list[Path]:
    candidates = [_resolve_directory(workspace.root, str(value)) for value in entry["directories"]]
    if entry["type"] == "removeDirectories":
        removed = set(candidates)
        return [path for path in current if path not in removed]
    return list(dict.fromkeys((*current, *candidates)))


def _apply_directories_to_settings(
    payload: dict[str, object] | None,
    entry: dict[str, object],
    project_root: Path,
) -> None:
    if payload is None:
        return
    permissions = _permission_payload(payload)
    existing_value = permissions.get("additionalDirectories", [])
    if not isinstance(existing_value, list) or any(not isinstance(item, str) for item in existing_value):
        raise ValueError("Permission settings additionalDirectories must be an array of strings.")
    normalized_existing = {
        str(_resolve_directory(project_root, path)): path for path in existing_value
    }
    candidates = [str(_resolve_directory(project_root, str(value))) for value in entry["directories"]]
    if entry["type"] == "removeDirectories":
        removed = set(candidates)
        permissions["additionalDirectories"] = [
            original
            for resolved, original in normalized_existing.items()
            if resolved not in removed
        ]
    else:
        permissions["additionalDirectories"] = list(
            dict.fromkeys((*existing_value, *candidates))
        )


def _resolve_directory(project_root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"Cannot resolve permission directory {value!r}: {error}") from error
    if not resolved.is_dir():
        raise ValueError(f"Permission directory is not a directory: {value}")
    return resolved


__all__ = ["PermissionUpdateApplication", "apply_permission_updates"]
