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
from .sandbox_permission_paths import SandboxPermissionPaths, sandbox_permission_paths
from .sandbox_seccomp_filter import unix_socket_filter_available
from .workspace_core import RunWorkspace
from .workspace_permissions import read_project_permissions
from .workspace_sandbox_credentials import (
    SandboxCredentialAccumulator,
    parse_sandbox_credentials,
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
MAX_SANDBOX_UNIX_SOCKETS = 100


@dataclass(frozen=True)
class SandboxConfig:
    enabled: bool = False
    fail_if_unavailable: bool = False
    auto_allow_bash_if_sandboxed: bool = True
    allow_unsandboxed_commands: bool = True
    network_disabled: bool = False
    allow_all_unix_sockets: bool = False
    allowed_unix_sockets: tuple[str, ...] = ()
    unix_socket_filter_available: bool = False
    unix_socket_filter_active: bool = False
    allowed_domains: tuple[str, ...] = ()
    denied_domains: tuple[str, ...] = ()
    permission_allowed_domains: tuple[str, ...] = ()
    permission_allow_write: tuple[Path, ...] = ()
    permission_deny_write: tuple[Path, ...] = ()
    permission_deny_read: tuple[Path, ...] = ()
    managed_domains_only: bool = False
    allow_write: tuple[Path, ...] = ()
    allow_read: tuple[Path, ...] = ()
    deny_write: tuple[Path, ...] = ()
    deny_read: tuple[Path, ...] = ()
    allow_managed_read_paths_only: bool = False
    denied_environment_variables: tuple[str, ...] = ()
    masked_credential_files: tuple[Path, ...] = ()
    masked_environment_variables: tuple[str, ...] = ()
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
    allowed_unix_sockets: list[str] = []
    credential_accumulator = SandboxCredentialAccumulator()
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
            for key in (
                "enabled",
                "failIfUnavailable",
                "autoAllowBashIfSandboxed",
                "allowUnsandboxedCommands",
            ):
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
                credential_settings = parse_sandbox_credentials(
                    credentials,
                    source=config.source,
                )
                array_values["denyRead"].extend(
                    credential_accumulator.add(
                        credential_settings,
                        trusted=config.trusted,
                    )
                )
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
                if "allowUnixSockets" in network:
                    allowed_unix_sockets.extend(
                        parse_sandbox_string_list(
                            network["allowUnixSockets"],
                            config.source,
                            "network.allowUnixSockets",
                        )
                    )
                if "allowAllUnixSockets" in network:
                    merged["allowAllUnixSockets"] = (
                        network["allowAllUnixSockets"],
                        config.trusted,
                    )
                    if config.trusted:
                        trusted_values["allowAllUnixSockets"] = network[
                            "allowAllUnixSockets"
                        ]
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
                    "allowUnixSockets",
                    "allowAllUnixSockets",
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
        allow_unsandboxed_commands = sandbox_boolean(
            merged_sandbox_value(merged, "allowUnsandboxedCommands", True),
            "sandbox.allowUnsandboxedCommands",
        )
        network_disabled = sandbox_boolean(
            merged_sandbox_value(merged, "networkDisabled", False),
            "sandbox network mode",
        )
        allow_all_unix_sockets = sandbox_boolean(
            merged_sandbox_value(merged, "allowAllUnixSockets", False),
            "sandbox.network.allowAllUnixSockets",
        )
        allowed_unix_socket_values = tuple(dict.fromkeys(allowed_unix_sockets))
        if len(allowed_unix_socket_values) > MAX_SANDBOX_UNIX_SOCKETS:
            raise ValueError(
                f"sandbox.network.allowUnixSockets exceeds {MAX_SANDBOX_UNIX_SOCKETS} entries."
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
        static_permission_paths = (
            sandbox_permission_paths(workspace, permissions)
            if permissions.error is None
            else SandboxPermissionPaths()
        )
        permission_allow_write = tuple(
            dict.fromkeys(
                (
                    *static_permission_paths.allow_write,
                    *workspace.sandbox_permission_allow_write,
                )
            )
        )
        permission_deny_write = tuple(
            dict.fromkeys(
                (
                    *static_permission_paths.deny_write,
                    *workspace.sandbox_permission_deny_write,
                )
            )
        )
        permission_deny_read = tuple(
            dict.fromkeys(
                (
                    *static_permission_paths.deny_read,
                    *workspace.sandbox_permission_deny_read,
                )
            )
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
        allow_write = tuple(dict.fromkeys((*allow_write, *permission_allow_write)))
        allow_read = resolve_sandbox_paths(
            workspace,
            [(value, trusted) for value, trusted, _managed in effective_allow_read],
            "allowRead",
        )
        deny_write = resolve_sandbox_paths(workspace, array_values["denyWrite"], "denyWrite")
        deny_read = resolve_sandbox_paths(workspace, array_values["denyRead"], "denyRead")
        deny_write = tuple(dict.fromkeys((*deny_write, *permission_deny_write)))
        deny_read = tuple(dict.fromkeys((*deny_read, *permission_deny_read)))
        resolved_credentials = credential_accumulator.resolve(
            workspace,
            denied_files=deny_read,
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
        socket_filter_available = bool(available and unix_socket_filter_available())
        socket_filter_active = socket_filter_available and not allow_all_unix_sockets
        network_available = bool(
            available and network_disabled and bwrap_path and _probe_bwrap(bwrap_path, unshare_network=True)
        )
        return SandboxConfig(
            enabled=enabled,
            fail_if_unavailable=fail_if_unavailable,
            auto_allow_bash_if_sandboxed=auto_allow_bash_if_sandboxed,
            allow_unsandboxed_commands=allow_unsandboxed_commands,
            network_disabled=network_disabled,
            allow_all_unix_sockets=allow_all_unix_sockets,
            allowed_unix_sockets=allowed_unix_socket_values,
            unix_socket_filter_available=socket_filter_available,
            unix_socket_filter_active=socket_filter_active,
            allowed_domains=allowed_domains,
            denied_domains=denied_domains,
            permission_allowed_domains=permission_allowed_domains,
            permission_allow_write=permission_allow_write,
            permission_deny_write=permission_deny_write,
            permission_deny_read=permission_deny_read,
            managed_domains_only=managed_domains_only,
            allow_write=allow_write,
            allow_read=allow_read,
            deny_write=deny_write,
            deny_read=deny_read,
            allow_managed_read_paths_only=allow_managed_read_paths_only,
            denied_environment_variables=resolved_credentials.denied_environment,
            masked_credential_files=resolved_credentials.masked_files,
            masked_environment_variables=resolved_credentials.masked_environment,
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
    if config.unix_socket_filter_active:
        unix_sockets = "Unix domain sockets blocked"
    elif config.allow_all_unix_sockets:
        unix_sockets = "Unix domain sockets allowed by trusted policy"
    else:
        unix_sockets = "Unix domain socket filtering unavailable"
    escape = (
        "A sandbox-incompatible command may request dangerouslyDisableSandbox, "
        "which requires normal permission approval. "
        if config.allow_unsandboxed_commands
        else "dangerouslyDisableSandbox is disabled and will be ignored. "
    )
    return (
        f"Command sandbox enabled ({availability}; {network}; {unix_sockets}; "
        f"failIfUnavailable={'true' if config.fail_if_unavailable else 'false'}; "
        f"autoAllowBashIfSandboxed={'true' if config.auto_allow_bash_if_sandboxed else 'false'}). "
        f"{escape}"
        "Sandboxed commands can write the project and isolated /tmp only, plus trusted allowWrite paths. "
        f"Read policy has {len(config.allow_read)} exception(s); "
        f"{len(config.denied_environment_variables)} credential environment variable(s) are removed; "
        f"{len(config.masked_environment_variables) + len(config.masked_credential_files)} "
        "credential source(s) are masked from command output."
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
