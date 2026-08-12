from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .sandbox_network_policy import normalize_sandbox_domains
from .sandbox_permission_domains import sandbox_webfetch_allow_domains
from .workspace_core import RunWorkspace
from .workspace_permissions import read_project_permissions
from .workspace_sandbox_credentials import (
    MAX_SANDBOX_CREDENTIAL_ENTRIES,
    parse_sandbox_credential_denies,
)
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
from .workspace_settings_sources import (
    project_config_file,
    read_settings_payload,
    settings_file_exists,
    settings_files_with_project_config,
)


SANDBOX_CONFIG_PATH = ".vibeagent/sandbox.json"
MAX_SANDBOX_CONFIG_BYTES = 128_000
MAX_SANDBOX_EXCLUDED_COMMANDS = 50


@dataclass(frozen=True)
class SandboxConfig:
    enabled: bool = False
    fail_if_unavailable: bool = False
    auto_allow_bash_if_sandboxed: bool = True
    network_disabled: bool = False
    allowed_domains: tuple[str, ...] = ()
    denied_domains: tuple[str, ...] = ()
    permission_allowed_domains: tuple[str, ...] = ()
    managed_domains_only: bool = False
    allow_write: tuple[Path, ...] = ()
    allow_read: tuple[Path, ...] = ()
    deny_write: tuple[Path, ...] = ()
    deny_read: tuple[Path, ...] = ()
    allow_managed_read_paths_only: bool = False
    denied_environment_variables: tuple[str, ...] = ()
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
    domain_values: dict[str, list[tuple[str, bool, bool]]] = {
        "allowedDomains": [],
        "deniedDomains": [],
    }
    allow_read_values: list[tuple[str, bool, bool]] = []
    denied_environment_variables: list[str] = []
    credential_entry_count = 0
    managed_domains_only = False
    allow_managed_read_paths_only = False
    sources: list[str] = []
    try:
        configs = settings_files_with_project_config(
            workspace,
            project_config_file(workspace, SANDBOX_CONFIG_PATH),
        )
        for config in configs:
            if not settings_file_exists(config):
                continue
            payload = read_settings_payload(config, max_bytes=MAX_SANDBOX_CONFIG_BYTES)
            managed_domain_lock_loaded = False
            if config.managed and "allowManagedDomainsOnly" in payload:
                managed_domains_value = payload["allowManagedDomainsOnly"]
                if not isinstance(managed_domains_value, bool):
                    raise ValueError(
                        f"{config.source} allowManagedDomainsOnly must be a boolean."
                    )
                managed_domains_only = managed_domains_value
                managed_domain_lock_loaded = True
            sandbox = (
                payload.get("sandbox")
                if config.source != SANDBOX_CONFIG_PATH
                else payload.get("sandbox", payload)
            )
            if sandbox is None:
                if managed_domain_lock_loaded:
                    sources.append(config.source)
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
                if "allowRead" in filesystem:
                    allow_read_values.extend(
                        (value, config.trusted, config.managed)
                        for value in parse_sandbox_string_list(
                            filesystem["allowRead"], config.source, "filesystem.allowRead"
                        )
                    )
                if config.managed and "allowManagedReadPathsOnly" in filesystem:
                    allow_managed_read_paths_only = sandbox_boolean(
                        filesystem["allowManagedReadPathsOnly"],
                        f"{config.source} sandbox.filesystem.allowManagedReadPathsOnly",
                    )
                unsupported = set(filesystem) - {
                    "allowWrite",
                    "allowRead",
                    "denyWrite",
                    "denyRead",
                    "allowManagedReadPathsOnly",
                }
                if unsupported:
                    names = ", ".join(sorted(str(key) for key in unsupported))
                    raise ValueError(f"Unsupported sandbox.filesystem setting(s): {names}.")
            credentials = sandbox.get("credentials")
            if credentials is not None:
                credential_files, credential_environment = parse_sandbox_credential_denies(
                    credentials,
                    source=config.source,
                )
                array_values["denyRead"].extend(
                    (value, config.trusted) for value in credential_files
                )
                denied_environment_variables.extend(credential_environment)
                credential_entry_count += len(credential_files) + len(credential_environment)
            network = sandbox.get("network")
            if isinstance(network, bool):
                merged["networkDisabled"] = (not network, config.trusted)
                if config.trusted:
                    trusted_values["networkDisabled"] = not network
            elif network is not None:
                if not isinstance(network, dict):
                    raise ValueError(f"{config.source} sandbox.network must be an object or boolean.")
                merged["networkDisabled"] = (True, config.trusted)
                if config.trusted:
                    trusted_values["networkDisabled"] = True
                for key in ("allowedDomains", "deniedDomains"):
                    if key in network:
                        domain_values[key].extend(
                            (value, config.trusted, config.managed)
                            for value in parse_sandbox_string_list(
                                network[key], config.source, f"network.{key}"
                            )
                        )
                if "strictAllowlist" in network:
                    strict_allowlist = sandbox_boolean(
                        network["strictAllowlist"],
                        f"{config.source} sandbox.network.strictAllowlist",
                    )
                    if not strict_allowlist:
                        raise ValueError(
                            "sandbox.network.strictAllowlist=false is not supported because "
                            "subprocess network prompts are unavailable; use a strict allowlist."
                        )
                unsupported = set(network) - {
                    "allowedDomains",
                    "deniedDomains",
                    "strictAllowlist",
                }
                if unsupported:
                    names = ", ".join(sorted(str(key) for key in unsupported))
                    raise ValueError(f"Unsupported sandbox.network setting(s): {names}.")

        if managed_domains_only:
            merged["networkDisabled"] = (True, True)
            trusted_values["networkDisabled"] = True
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
        allowed_entries = domain_values["allowedDomains"]
        if managed_domains_only:
            allowed_entries = [entry for entry in allowed_entries if entry[2]]
        permissions = read_project_permissions(workspace)
        static_permission_domains = (
            sandbox_webfetch_allow_domains(
                permissions,
                project_config_trusted=workspace.project_config_trusted,
                managed_only=managed_domains_only,
            )
            if permissions.error is None
            else ()
        )
        runtime_permission_domains = (
            () if managed_domains_only else workspace.sandbox_permission_domains
        )
        permission_allowed_domains = tuple(
            dict.fromkeys((*static_permission_domains, *runtime_permission_domains))
        )
        allowed_domains = normalize_sandbox_domains(
            [
                *(value for value, _trusted, _managed in allowed_entries),
                *permission_allowed_domains,
            ],
            field="allowedDomains",
        )
        denied_domains = normalize_sandbox_domains(
            [value for value, _trusted, _managed in domain_values["deniedDomains"]],
            field="deniedDomains",
        )
        if (
            any(not trusted for _value, trusted, _managed in allowed_entries)
            and not workspace.project_config_trusted
        ):
            raise ValueError(
                "sandbox.network.allowedDomains from project configuration requires "
                "explicit project configuration trust."
            )
        effective_allow_read = allow_read_values
        if allow_managed_read_paths_only:
            effective_allow_read = [entry for entry in effective_allow_read if entry[2]]
        if (
            any(not trusted for _value, trusted, _managed in effective_allow_read)
            and not workspace.project_config_trusted
        ):
            raise ValueError(
                "sandbox.filesystem.allowRead from project configuration requires "
                "explicit project configuration trust."
            )
        allow_write = resolve_sandbox_paths(
            workspace,
            array_values["allowWrite"],
            "allowWrite",
            external_requires_trust=True,
        )
        allow_read = resolve_sandbox_paths(
            workspace,
            [(value, trusted) for value, trusted, _managed in effective_allow_read],
            "allowRead",
        )
        deny_write = resolve_sandbox_paths(workspace, array_values["denyWrite"], "denyWrite")
        deny_read = resolve_sandbox_paths(workspace, array_values["denyRead"], "denyRead")
        denied_environment = tuple(dict.fromkeys(denied_environment_variables))
        if credential_entry_count > MAX_SANDBOX_CREDENTIAL_ENTRIES:
            raise ValueError(
                "sandbox.credentials exceeds "
                f"{MAX_SANDBOX_CREDENTIAL_ENTRIES} merged entries."
            )
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
            allowed_domains=allowed_domains,
            denied_domains=denied_domains,
            permission_allowed_domains=permission_allowed_domains,
            managed_domains_only=managed_domains_only,
            allow_write=allow_write,
            allow_read=allow_read,
            deny_write=deny_write,
            deny_read=deny_read,
            allow_managed_read_paths_only=allow_managed_read_paths_only,
            denied_environment_variables=denied_environment,
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
    if config.allowed_domains:
        network = f"strict network proxy with {len(config.allowed_domains)} allowed domain(s)"
    elif config.network_disabled:
        network = "network namespace disconnected"
    else:
        network = "host network available"
    availability = "Bubblewrap available" if config.available else "Bubblewrap unavailable"
    return (
        f"Command sandbox enabled ({availability}; {network}; "
        f"failIfUnavailable={'true' if config.fail_if_unavailable else 'false'}; "
        f"autoAllowBashIfSandboxed={'true' if config.auto_allow_bash_if_sandboxed else 'false'}). "
        "Sandboxed commands can write the project and isolated /tmp only, plus trusted allowWrite paths. "
        f"Read policy has {len(config.allow_read)} exception(s); "
        f"{len(config.denied_environment_variables)} credential environment variable(s) are removed."
    )


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
