from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes
from .workspace_sandbox_values import (
    MergedSandboxValues,
    ScopedValues,
    deduplicate_scoped_values,
    merged_sandbox_value,
    parse_sandbox_string_list,
    reject_untrusted_sandbox_weakening,
    resolve_sandbox_paths,
    sandbox_boolean,
)
from .workspace_settings_sources import claude_settings_files, project_config_file


SANDBOX_CONFIG_PATH = ".vibeagent/sandbox.json"
MAX_SANDBOX_CONFIG_BYTES = 128_000
MAX_SANDBOX_EXCLUDED_COMMANDS = 50


@dataclass(frozen=True)
class SandboxConfig:
    enabled: bool = False
    fail_if_unavailable: bool = False
    auto_allow_bash_if_sandboxed: bool = True
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
    merged: MergedSandboxValues = {}
    trusted_values: dict[str, object] = {}
    array_values: dict[str, ScopedValues] = {
        "allowWrite": [],
        "denyWrite": [],
        "denyRead": [],
        "excludedCommands": [],
    }
    sources: list[str] = []
    try:
        configs = (
            *claude_settings_files(workspace),
            project_config_file(workspace, SANDBOX_CONFIG_PATH),
        )
        for config in configs:
            if not config.path.exists():
                continue
            payload = _read_config(config.boundary, config.path, config.source)
            sandbox = (
                payload.get("sandbox")
                if config.source != SANDBOX_CONFIG_PATH
                else payload.get("sandbox", payload)
            )
            if sandbox is None:
                continue
            if not isinstance(sandbox, dict):
                raise ValueError(f"{config.source} sandbox must be an object.")
            sources.append(config.source)
            for key in ("enabled", "failIfUnavailable", "autoAllowBashIfSandboxed"):
                if key in sandbox:
                    merged[key] = (sandbox[key], config.trusted)
                    if config.trusted:
                        trusted_values[key] = sandbox[key]
            excluded = sandbox.get("excludedCommands")
            if excluded is not None:
                array_values["excludedCommands"].extend(
                    (value, config.trusted)
                    for value in parse_sandbox_string_list(excluded, config.source, "excludedCommands")
                )
            filesystem = sandbox.get("filesystem")
            if filesystem is not None:
                if not isinstance(filesystem, dict):
                    raise ValueError(f"{config.source} sandbox.filesystem must be an object.")
                for key in ("allowWrite", "denyWrite", "denyRead"):
                    if key in filesystem:
                        array_values[key].extend(
                            (value, config.trusted)
                            for value in parse_sandbox_string_list(
                                filesystem[key], config.source, f"filesystem.{key}"
                            )
                        )
                if filesystem.get("allowRead"):
                    raise ValueError("sandbox.filesystem.allowRead is not supported yet; refusing partial enforcement.")
            network = sandbox.get("network")
            if isinstance(network, bool):
                merged["networkDisabled"] = (not network, config.trusted)
                if config.trusted:
                    trusted_values["networkDisabled"] = not network
            elif network is not None:
                if not isinstance(network, dict):
                    raise ValueError(f"{config.source} sandbox.network must be an object or boolean.")
                allowed_domains = network.get("allowedDomains")
                if allowed_domains is not None:
                    domains = parse_sandbox_string_list(
                        allowed_domains, config.source, "network.allowedDomains"
                    )
                    if domains:
                        raise ValueError("sandbox.network.allowedDomains requires a domain proxy and is not supported yet.")
                    merged["networkDisabled"] = (True, config.trusted)
                    if config.trusted:
                        trusted_values["networkDisabled"] = True
                unsupported = set(network) - {"allowedDomains"}
                if unsupported:
                    names = ", ".join(sorted(str(key) for key in unsupported))
                    raise ValueError(f"Unsupported sandbox.network setting(s): {names}.")

        reject_untrusted_sandbox_weakening(workspace, merged, trusted_values)
        enabled = sandbox_boolean(
            merged_sandbox_value(merged, "enabled", False),
            "sandbox.enabled",
        )
        fail_if_unavailable = sandbox_boolean(
            merged_sandbox_value(merged, "failIfUnavailable", False),
            "sandbox.failIfUnavailable",
        )
        auto_allow_bash_if_sandboxed = sandbox_boolean(
            merged_sandbox_value(merged, "autoAllowBashIfSandboxed", True),
            "sandbox.autoAllowBashIfSandboxed",
        )
        network_disabled = sandbox_boolean(
            merged_sandbox_value(merged, "networkDisabled", False),
            "sandbox network mode",
        )
        allow_write = resolve_sandbox_paths(
            workspace,
            array_values["allowWrite"],
            "allowWrite",
            external_requires_trust=True,
        )
        deny_write = resolve_sandbox_paths(workspace, array_values["denyWrite"], "denyWrite")
        deny_read = resolve_sandbox_paths(workspace, array_values["denyRead"], "denyRead")
        scoped_exclusions = deduplicate_scoped_values(array_values["excludedCommands"])
        excluded_commands = tuple(value for value, _trusted in scoped_exclusions)
        if len(excluded_commands) > MAX_SANDBOX_EXCLUDED_COMMANDS:
            raise ValueError(f"sandbox.excludedCommands exceeds {MAX_SANDBOX_EXCLUDED_COMMANDS} entries.")
        has_untrusted_exclusion = any(not trusted for _value, trusted in scoped_exclusions)
        if has_untrusted_exclusion and not workspace.project_config_trusted:
            raise ValueError("sandbox.excludedCommands requires explicit project configuration trust.")
        bwrap_path = shutil.which("bwrap") if os.name == "posix" else None
        available = bool(enabled and bwrap_path and _probe_bwrap(bwrap_path))
        network_available = bool(
            available and network_disabled and bwrap_path and _probe_bwrap(bwrap_path, unshare_network=True)
        )
        return SandboxConfig(
            enabled=enabled,
            fail_if_unavailable=fail_if_unavailable,
            auto_allow_bash_if_sandboxed=auto_allow_bash_if_sandboxed,
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
        f"failIfUnavailable={'true' if config.fail_if_unavailable else 'false'}; "
        f"autoAllowBashIfSandboxed={'true' if config.auto_allow_bash_if_sandboxed else 'false'}). "
        "Sandboxed commands can write the project and isolated /tmp only, plus trusted allowWrite paths."
    )


def _read_config(root: Path, path: Path, source: str) -> dict[str, object]:
    if has_symlink_component(root, path):
        raise ValueError(f"{source} contains a symbolic link.")
    raw = read_regular_file_bytes(path, max_bytes=MAX_SANDBOX_CONFIG_BYTES, label=source)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{source} must contain a JSON object.")
    return payload


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
