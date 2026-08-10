from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .command_safety import get_blocked_command_reason
from .plugin_environment import plugin_command_environment
from .types import RunCommandAction, RunCommandsAction, StartCommandAction
from .workspace_core import RunWorkspace
from .workspace_permissions import wildcard_matches
from .workspace_resolve import resolve_command_cwd
from .workspace_sandbox import SandboxConfig, read_workspace_sandbox


@dataclass(frozen=True)
class CommandLaunch:
    argv: tuple[str, ...]
    sandboxed: bool
    config: SandboxConfig
    environment: dict[str, str] | None = None
    warning: str | None = None
    error: str | None = None


def sandbox_auto_approval_reason(workspace: RunWorkspace, action: object) -> str | None:
    config = read_workspace_sandbox(workspace)
    if not (
        config.active
        and config.auto_allow_bash_if_sandboxed
        and config.network_disabled
        and config.network_available
    ):
        return None
    if isinstance(action, (RunCommandAction, StartCommandAction)):
        commands = ((action.command, action.cwd),)
    elif isinstance(action, RunCommandsAction):
        commands = tuple((item.command, item.cwd) for item in action.commands)
    else:
        return None
    if not commands:
        return None
    for command, cwd in commands:
        if get_blocked_command_reason(command) is not None:
            return None
        try:
            command_cwd = resolve_command_cwd(workspace, cwd)
        except ValueError:
            return None
        launch = prepare_command_launch(workspace, command, command_cwd)
        if not launch.sandboxed or launch.warning is not None or launch.error is not None:
            return None
    return "Approved automatically because every command will run with filesystem and network sandbox isolation."


def prepare_command_launch(
    workspace: RunWorkspace,
    command: str,
    cwd: Path,
    executed_command: str | None = None,
) -> CommandLaunch:
    config = read_workspace_sandbox(workspace)
    command_to_execute = executed_command if executed_command is not None else command
    shell_argv = ("/bin/sh", "-c", command_to_execute)
    try:
        environment = plugin_command_environment(workspace)
    except (OSError, ValueError) as error:
        return CommandLaunch(
            shell_argv,
            False,
            config,
            error=f"Plugin executable environment error: {error}",
        )
    if config.error is not None:
        return CommandLaunch(
            shell_argv,
            False,
            config,
            environment,
            error=f"Sandbox configuration error: {config.error}",
        )
    if not config.enabled:
        return CommandLaunch(shell_argv, False, config, environment)
    if any(wildcard_matches(pattern, command, path_mode=False) for pattern in config.excluded_commands):
        return CommandLaunch(
            shell_argv,
            False,
            config,
            environment,
            warning="Command excluded from the sandbox by trusted configuration.",
        )
    if not config.available or config.bwrap_path is None:
        message = "Bubblewrap sandbox is enabled but unavailable on this system."
        if config.fail_if_unavailable:
            return CommandLaunch(shell_argv, False, config, environment, error=message)
        return CommandLaunch(
            shell_argv,
            False,
            config,
            environment,
            warning=f"Sandbox warning: {message} Running unsandboxed.",
        )
    network_warning: str | None = None
    if config.network_disabled and not config.network_available:
        message = "Bubblewrap network isolation is unavailable on this system."
        if config.fail_if_unavailable:
            return CommandLaunch(shell_argv, False, config, environment, error=message)
        network_warning = f"Sandbox warning: {message} Filesystem isolation remains active with host networking."
    external_allow_write = tuple(path for path in config.allow_write if not path.is_relative_to(workspace.root))
    missing_mounts = [path for path in (*external_allow_write, *config.deny_write, *config.deny_read) if not path.exists()]
    if missing_mounts:
        paths = ", ".join(path.as_posix() for path in missing_mounts)
        return CommandLaunch(
            shell_argv,
            False,
            config,
            environment,
            error=f"Sandbox path does not exist: {paths}",
        )

    argv = [
        config.bwrap_path,
        "--new-session",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        "/run",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--bind",
        workspace.root.as_posix(),
        workspace.root.as_posix(),
    ]
    for path in workspace.additional_roots:
        argv.extend(("--bind", path.as_posix(), path.as_posix()))
    for path in external_allow_write:
        argv.extend(("--bind", path.as_posix(), path.as_posix()))
    for path in config.deny_write:
        argv.extend(("--ro-bind", path.as_posix(), path.as_posix()))
    for path in config.deny_read:
        if path.is_dir():
            argv.extend(("--tmpfs", path.as_posix()))
        else:
            argv.extend(("--ro-bind", "/dev/null", path.as_posix()))
    if config.network_disabled and config.network_available:
        argv.append("--unshare-net")
    argv.extend(("--setenv", "VIBEAGENT_SANDBOX", "1", "--chdir", cwd.as_posix(), "/bin/sh", "-c", command_to_execute))
    return CommandLaunch(tuple(argv), True, config, environment, warning=network_warning)
