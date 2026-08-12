from __future__ import annotations

from dataclasses import dataclass
import glob
from pathlib import Path
import re

from .user_paths import user_home
from .workspace_core import RunWorkspace
from .workspace_permissions import ProjectPermissions


MAX_SANDBOX_PERMISSION_PATHS = 500
_GLOB_PATTERN = re.compile(r"[*?[]")


@dataclass(frozen=True)
class SandboxPermissionPaths:
    allow_write: tuple[Path, ...] = ()
    deny_write: tuple[Path, ...] = ()
    deny_read: tuple[Path, ...] = ()


def sandbox_permission_paths(
    workspace: RunWorkspace,
    permissions: ProjectPermissions,
) -> SandboxPermissionPaths:
    allow_write: list[Path] = []
    deny_write: list[Path] = []
    deny_read: list[Path] = []
    trusted_sources = frozenset(permissions.trusted_allow_sources)
    for rule in permissions.rules:
        if rule.specifier is None or rule.effect == "ask":
            continue
        destination: list[Path] | None = None
        if rule.tool == "Edit" and rule.effect == "allow":
            if not (
                rule.managed
                or permissions.allow_rules_trusted
                or workspace.project_config_trusted
                or rule.source in trusted_sources
            ):
                continue
            destination = allow_write
        elif rule.tool == "Edit" and rule.effect == "deny":
            destination = deny_write
        elif rule.tool == "Read" and rule.effect == "deny":
            destination = deny_read
        if destination is not None:
            destination.extend(
                _resolve_permission_pattern(
                    workspace,
                    rule.specifier,
                    allow=destination is allow_write,
                )
            )
    result = SandboxPermissionPaths(
        allow_write=_deduplicate(allow_write),
        deny_write=_deduplicate(deny_write),
        deny_read=_deduplicate(deny_read),
    )
    count = len(result.allow_write) + len(result.deny_write) + len(result.deny_read)
    if count > MAX_SANDBOX_PERMISSION_PATHS:
        raise ValueError(
            "Sandbox permission path expansion exceeds "
            f"{MAX_SANDBOX_PERMISSION_PATHS} entries."
        )
    return result


def _resolve_permission_pattern(
    workspace: RunWorkspace,
    specifier: str,
    *,
    allow: bool,
) -> tuple[Path, ...]:
    candidate = _permission_candidate(workspace, specifier)
    candidate_text = candidate.as_posix()
    recursive_root = _recursive_directory_root(candidate_text)
    if recursive_root is not None:
        path = Path(recursive_root)
        return (
            (path.resolve(),)
            if path.exists() and not (allow and path.is_symlink())
            else ()
        )
    if _GLOB_PATTERN.search(candidate_text) is None:
        return (
            (candidate.resolve(),)
            if candidate.exists() and not (allow and candidate.is_symlink())
            else ()
        )
    matches = glob.glob(candidate_text, recursive=True, include_hidden=True)
    return _deduplicate(
        [
            Path(match).resolve()
            for match in matches
            if Path(match).exists() and not (allow and Path(match).is_symlink())
        ]
    )


def _permission_candidate(workspace: RunWorkspace, specifier: str) -> Path:
    value = specifier.strip()
    if value.startswith("//"):
        return Path(value[1:])
    if value == "~":
        return user_home()
    if value.startswith("~/"):
        return user_home() / value[2:]
    if value.startswith("/"):
        return workspace.root / value[1:]
    return workspace.root / value.removeprefix("./")


def _recursive_directory_root(pattern: str) -> str | None:
    if not pattern.endswith("/**"):
        return None
    root = pattern[:-3].rstrip("/") or "/"
    return root if _GLOB_PATTERN.search(root) is None else None


def _deduplicate(paths: list[Path]) -> tuple[Path, ...]:
    return tuple(dict.fromkeys(paths))


__all__ = [
    "MAX_SANDBOX_PERMISSION_PATHS",
    "SandboxPermissionPaths",
    "sandbox_permission_paths",
]
