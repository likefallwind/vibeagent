from __future__ import annotations

from pathlib import Path
import re

from .user_paths import user_home
from .workspace_core import RunWorkspace


MAX_SANDBOX_PATHS = 100
MAX_SANDBOX_VALUE_CHARS = 1_000
GLOB_CHARACTERS = re.compile(r"[*?[]")
ScopedValues = list[tuple[str, bool]]
MergedSandboxValues = dict[str, tuple[object, bool]]


def parse_sandbox_string_list(value: object, source: str, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{source} sandbox.{field} must be a list.")
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > MAX_SANDBOX_VALUE_CHARS:
            raise ValueError(
                f"{source} sandbox.{field} entries must contain 1-{MAX_SANDBOX_VALUE_CHARS} characters."
            )
        values.append(item.strip())
    return values


def sandbox_boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean.")
    return value


def merged_sandbox_value(
    merged: MergedSandboxValues,
    key: str,
    default: object,
) -> object:
    return merged.get(key, (default, False))[0]


def reject_untrusted_sandbox_weakening(
    workspace: RunWorkspace,
    merged: MergedSandboxValues,
    trusted_values: dict[str, object],
) -> None:
    if workspace.project_config_trusted:
        return
    labels = {
        "enabled": "sandbox.enabled",
        "failIfUnavailable": "sandbox.failIfUnavailable",
        "networkDisabled": "sandbox network isolation",
    }
    for key, label in labels.items():
        trusted_value = trusted_values.get(key)
        effective = merged.get(key)
        if trusted_value is True and effective == (False, False):
            raise ValueError(
                f"Disabling user {label} requires explicit project configuration trust."
            )
    trusted_escape = trusted_values.get("allowUnsandboxedCommands")
    effective_escape = merged.get("allowUnsandboxedCommands")
    if trusted_escape is False and effective_escape == (True, False):
        raise ValueError(
            "Enabling user sandbox.allowUnsandboxedCommands requires explicit "
            "project configuration trust."
        )
    unix_sockets = merged.get("allowAllUnixSockets")
    if unix_sockets == (True, False):
        raise ValueError(
            "Enabling sandbox.network.allowAllUnixSockets from project configuration "
            "requires explicit project configuration trust."
        )


def deduplicate_scoped_values(values: ScopedValues) -> ScopedValues:
    trusted_by_value: dict[str, bool] = {}
    for value, trusted in values:
        trusted_by_value[value] = trusted_by_value.get(value, False) or trusted
    return list(trusted_by_value.items())


def resolve_sandbox_paths(
    workspace: RunWorkspace,
    values: ScopedValues,
    label: str,
    *,
    external_requires_trust: bool = False,
) -> tuple[Path, ...]:
    deduplicated = deduplicate_scoped_values(values)
    if len(deduplicated) > MAX_SANDBOX_PATHS:
        raise ValueError(f"sandbox.filesystem.{label} exceeds {MAX_SANDBOX_PATHS} entries.")
    paths: list[Path] = []
    for value, trusted in deduplicated:
        if GLOB_CHARACTERS.search(value):
            raise ValueError(f"sandbox.filesystem.{label} does not support glob paths: {value}")
        if value.startswith("//"):
            candidate = Path(value[1:])
        elif value.startswith("~/"):
            candidate = user_home() / value[2:]
        elif Path(value).is_absolute():
            candidate = Path(value)
        else:
            candidate = workspace.root / value.removeprefix("./")
        resolved = candidate.resolve(strict=False)
        if (
            external_requires_trust
            and not resolved.is_relative_to(workspace.root)
            and not trusted
            and not workspace.project_config_trusted
        ):
            raise ValueError(
                f"sandbox.filesystem.{label} outside the project requires explicit project configuration trust: {value}"
            )
        paths.append(resolved)
    return tuple(paths)


__all__ = [
    "MergedSandboxValues",
    "ScopedValues",
    "deduplicate_scoped_values",
    "merged_sandbox_value",
    "parse_sandbox_string_list",
    "reject_untrusted_sandbox_weakening",
    "resolve_sandbox_paths",
    "sandbox_boolean",
]
