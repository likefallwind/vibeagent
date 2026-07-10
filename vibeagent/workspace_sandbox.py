from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


SANDBOX_CONFIG_PATHS = (
    (".claude/settings.json", True),
    (".claude/settings.local.json", True),
    (".vibeagent/sandbox.json", False),
)
MAX_SANDBOX_CONFIG_BYTES = 128_000
MAX_SANDBOX_PATHS = 100
MAX_SANDBOX_EXCLUDED_COMMANDS = 50
MAX_SANDBOX_VALUE_CHARS = 1_000
GLOB_CHARACTERS = re.compile(r"[*?[]")


@dataclass(frozen=True)
class SandboxConfig:
    enabled: bool = False
    fail_if_unavailable: bool = False
    network_disabled: bool = False
    allow_write: tuple[Path, ...] = ()
    deny_write: tuple[Path, ...] = ()
    deny_read: tuple[Path, ...] = ()
    excluded_commands: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    bwrap_path: str | None = None
    available: bool = False
    network_available: bool = False
    error: str | None = None

    @property
    def active(self) -> bool:
        network_ready = not self.network_disabled or self.network_available or not self.fail_if_unavailable
        return self.enabled and self.available and network_ready and self.error is None


def read_workspace_sandbox(workspace: RunWorkspace) -> SandboxConfig:
    merged: dict[str, object] = {}
    array_values: dict[str, list[str]] = {
        "allowWrite": [],
        "denyWrite": [],
        "denyRead": [],
        "excludedCommands": [],
    }
    sources: list[str] = []
    try:
        for relative_path, nested in SANDBOX_CONFIG_PATHS:
            path = workspace.root / relative_path
            if not path.exists():
                continue
            payload = _read_config(workspace.root, path)
            sandbox = payload.get("sandbox") if nested else payload.get("sandbox", payload)
            if sandbox is None:
                continue
            if not isinstance(sandbox, dict):
                raise ValueError(f"{relative_path} sandbox must be an object.")
            sources.append(relative_path)
            for key in ("enabled", "failIfUnavailable"):
                if key in sandbox:
                    merged[key] = sandbox[key]
            excluded = sandbox.get("excludedCommands")
            if excluded is not None:
                array_values["excludedCommands"].extend(_string_list(excluded, relative_path, "excludedCommands"))
            filesystem = sandbox.get("filesystem")
            if filesystem is not None:
                if not isinstance(filesystem, dict):
                    raise ValueError(f"{relative_path} sandbox.filesystem must be an object.")
                for key in ("allowWrite", "denyWrite", "denyRead"):
                    if key in filesystem:
                        array_values[key].extend(_string_list(filesystem[key], relative_path, f"filesystem.{key}"))
                if filesystem.get("allowRead"):
                    raise ValueError("sandbox.filesystem.allowRead is not supported yet; refusing partial enforcement.")
            network = sandbox.get("network")
            if isinstance(network, bool):
                merged["networkDisabled"] = not network
            elif network is not None:
                if not isinstance(network, dict):
                    raise ValueError(f"{relative_path} sandbox.network must be an object or boolean.")
                allowed_domains = network.get("allowedDomains")
                if allowed_domains is not None:
                    domains = _string_list(allowed_domains, relative_path, "network.allowedDomains")
                    if domains:
                        raise ValueError("sandbox.network.allowedDomains requires a domain proxy and is not supported yet.")
                    merged["networkDisabled"] = True
                unsupported = set(network) - {"allowedDomains"}
                if unsupported:
                    names = ", ".join(sorted(str(key) for key in unsupported))
                    raise ValueError(f"Unsupported sandbox.network setting(s): {names}.")

        enabled = _boolean(merged.get("enabled", False), "sandbox.enabled")
        fail_if_unavailable = _boolean(merged.get("failIfUnavailable", False), "sandbox.failIfUnavailable")
        network_disabled = _boolean(merged.get("networkDisabled", False), "sandbox network mode")
        allow_write = _resolve_paths(workspace, array_values["allowWrite"], "allowWrite", external_requires_trust=True)
        deny_write = _resolve_paths(workspace, array_values["denyWrite"], "denyWrite")
        deny_read = _resolve_paths(workspace, array_values["denyRead"], "denyRead")
        excluded_commands = tuple(dict.fromkeys(array_values["excludedCommands"]))
        if len(excluded_commands) > MAX_SANDBOX_EXCLUDED_COMMANDS:
            raise ValueError(f"sandbox.excludedCommands exceeds {MAX_SANDBOX_EXCLUDED_COMMANDS} entries.")
        if excluded_commands and not workspace.project_config_trusted:
            raise ValueError("sandbox.excludedCommands requires explicit project configuration trust.")
        bwrap_path = shutil.which("bwrap") if os.name == "posix" else None
        available = bool(enabled and bwrap_path and _probe_bwrap(bwrap_path))
        network_available = bool(
            available and network_disabled and bwrap_path and _probe_bwrap(bwrap_path, unshare_network=True)
        )
        return SandboxConfig(
            enabled=enabled,
            fail_if_unavailable=fail_if_unavailable,
            network_disabled=network_disabled,
            allow_write=allow_write,
            deny_write=deny_write,
            deny_read=deny_read,
            excluded_commands=excluded_commands,
            sources=tuple(sources),
            bwrap_path=bwrap_path,
            available=available,
            network_available=network_available,
        )
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        return SandboxConfig(sources=tuple(sources), error=str(error))


def format_workspace_sandbox_for_prompt(workspace: RunWorkspace) -> str:
    config = read_workspace_sandbox(workspace)
    if config.error is not None:
        return f"Command sandbox configuration is invalid; shell commands will be blocked: {config.error}"
    if not config.enabled:
        return ""
    network = "network namespace disabled" if config.network_disabled else "host network available"
    availability = "Bubblewrap available" if config.available else "Bubblewrap unavailable"
    return (
        f"Command sandbox enabled ({availability}; {network}; "
        f"failIfUnavailable={'true' if config.fail_if_unavailable else 'false'}). "
        "Sandboxed commands can write the project and isolated /tmp only, plus trusted allowWrite paths."
    )


def _read_config(root: Path, path: Path) -> dict[str, object]:
    relative = path.relative_to(root).as_posix()
    if has_symlink_component(root, path):
        raise ValueError(f"{relative} contains a symbolic link.")
    raw = read_regular_file_bytes(path, max_bytes=MAX_SANDBOX_CONFIG_BYTES, label=relative)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relative} must contain a JSON object.")
    return payload


def _string_list(value: object, source: str, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{source} sandbox.{field} must be a list.")
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > MAX_SANDBOX_VALUE_CHARS:
            raise ValueError(f"{source} sandbox.{field} entries must contain 1-{MAX_SANDBOX_VALUE_CHARS} characters.")
        values.append(item.strip())
    return values


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean.")
    return value


def _resolve_paths(
    workspace: RunWorkspace,
    values: list[str],
    label: str,
    *,
    external_requires_trust: bool = False,
) -> tuple[Path, ...]:
    if len(values) > MAX_SANDBOX_PATHS:
        raise ValueError(f"sandbox.filesystem.{label} exceeds {MAX_SANDBOX_PATHS} entries.")
    paths: list[Path] = []
    for value in dict.fromkeys(values):
        if GLOB_CHARACTERS.search(value):
            raise ValueError(f"sandbox.filesystem.{label} does not support glob paths: {value}")
        if value.startswith("//"):
            candidate = Path(value[1:])
        elif value.startswith("~/"):
            candidate = Path(value).expanduser()
        elif Path(value).is_absolute():
            candidate = Path(value)
        else:
            candidate = workspace.root / value.removeprefix("./")
        resolved = candidate.resolve(strict=False)
        if external_requires_trust and not resolved.is_relative_to(workspace.root) and not workspace.project_config_trusted:
            raise ValueError(f"sandbox.filesystem.{label} outside the project requires explicit project configuration trust: {value}")
        paths.append(resolved)
    return tuple(paths)


@lru_cache(maxsize=4)
def _probe_bwrap(path: str, *, unshare_network: bool = False) -> bool:
    command = [
        path,
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--ro-bind",
        "/",
        "/",
    ]
    if unshare_network:
        command.append("--unshare-net")
    command.append("/bin/true")
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
