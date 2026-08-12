from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .workspace_core import RunWorkspace
from .workspace_sandbox_values import ScopedValues, resolve_sandbox_paths


MAX_SANDBOX_CREDENTIAL_ENTRIES = 200
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")


@dataclass(frozen=True)
class SandboxCredentialSettings:
    denied_files: tuple[str, ...] = ()
    masked_files: tuple[str, ...] = ()
    denied_environment: tuple[str, ...] = ()
    masked_environment: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedSandboxCredentials:
    masked_files: tuple[Path, ...] = ()
    denied_environment: tuple[str, ...] = ()
    masked_environment: tuple[str, ...] = ()


class SandboxCredentialAccumulator:
    def __init__(self) -> None:
        self.masked_file_values: ScopedValues = []
        self.denied_environment: list[str] = []
        self.masked_environment: list[str] = []
        self.entry_count = 0

    def add(
        self,
        settings: SandboxCredentialSettings,
        *,
        trusted: bool,
    ) -> ScopedValues:
        self.masked_file_values.extend(
            (value, trusted) for value in settings.masked_files
        )
        self.denied_environment.extend(settings.denied_environment)
        self.masked_environment.extend(settings.masked_environment)
        self.entry_count += sum(
            len(values)
            for values in (
                settings.denied_files,
                settings.masked_files,
                settings.denied_environment,
                settings.masked_environment,
            )
        )
        return [(value, trusted) for value in settings.denied_files]

    def resolve(
        self,
        workspace: RunWorkspace,
        *,
        denied_files: tuple[Path, ...],
    ) -> ResolvedSandboxCredentials:
        if self.entry_count > MAX_SANDBOX_CREDENTIAL_ENTRIES:
            raise ValueError(
                "sandbox.credentials exceeds "
                f"{MAX_SANDBOX_CREDENTIAL_ENTRIES} merged entries."
            )
        masked_files = resolve_sandbox_paths(
            workspace,
            self.masked_file_values,
            "credentials.files",
        )
        denied_file_set = set(denied_files)
        masked_files = tuple(
            path for path in masked_files if path not in denied_file_set
        )
        denied_environment = tuple(dict.fromkeys(self.denied_environment))
        denied_environment_set = set(denied_environment)
        masked_environment = tuple(
            name
            for name in dict.fromkeys(self.masked_environment)
            if name not in denied_environment_set
        )
        return ResolvedSandboxCredentials(
            masked_files=masked_files,
            denied_environment=denied_environment,
            masked_environment=masked_environment,
        )


def parse_sandbox_credentials(
    value: object,
    *,
    source: str,
) -> SandboxCredentialSettings:
    if not isinstance(value, dict):
        raise ValueError(f"{source} sandbox.credentials must be an object.")
    unsupported = set(value) - {"files", "envVars"}
    if unsupported:
        names = ", ".join(sorted(str(key) for key in unsupported))
        raise ValueError(f"Unsupported {source} sandbox.credentials setting(s): {names}.")
    files = _credential_entries(
        value.get("files", []),
        source=source,
        field="files",
        key="path",
    )
    environment = _credential_entries(
        value.get("envVars", []),
        source=source,
        field="envVars",
        key="name",
    )
    if len(files) + len(environment) > MAX_SANDBOX_CREDENTIAL_ENTRIES:
        raise ValueError(
            f"{source} sandbox.credentials exceeds "
            f"{MAX_SANDBOX_CREDENTIAL_ENTRIES} entries."
        )
    for name, _mode in environment:
        if _ENVIRONMENT_NAME.fullmatch(name) is None:
            raise ValueError(
                f"{source} sandbox.credentials.envVars contains an invalid variable name."
            )
    return SandboxCredentialSettings(
        denied_files=tuple(item for item, mode in files if mode == "deny"),
        masked_files=tuple(item for item, mode in files if mode == "mask"),
        denied_environment=tuple(
            item for item, mode in environment if mode == "deny"
        ),
        masked_environment=tuple(
            item for item, mode in environment if mode == "mask"
        ),
    )


def _credential_entries(
    value: object,
    *,
    source: str,
    field: str,
    key: str,
) -> list[tuple[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{source} sandbox.credentials.{field} must be a list.")
    parsed: list[tuple[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {key, "mode"}:
            raise ValueError(
                f"{source} sandbox.credentials.{field} entries require only "
                f"{key} and mode."
            )
        item = entry.get(key)
        mode = entry.get("mode")
        if not isinstance(item, str) or not item.strip() or len(item) > 1_000:
            raise ValueError(
                f"{source} sandbox.credentials.{field}.{key} must contain "
                "1-1000 characters."
            )
        if mode not in {"deny", "mask"}:
            raise ValueError(
                f"{source} sandbox.credentials.{field} mode {mode!r} is not "
                "supported; use deny or mask."
            )
        parsed.append((item.strip(), mode))
    return parsed


__all__ = [
    "MAX_SANDBOX_CREDENTIAL_ENTRIES",
    "ResolvedSandboxCredentials",
    "SandboxCredentialAccumulator",
    "SandboxCredentialSettings",
    "parse_sandbox_credentials",
]
