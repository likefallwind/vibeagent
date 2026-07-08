from __future__ import annotations

from pathlib import Path
import re
import shlex


def shell_command_segments(command: str) -> list[list[str]]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token and all(character in ";&|" for character in token):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def unwrapped_shell_executable_name(parts: list[str]) -> str | None:
    remaining = unwrapped_shell_command_parts(parts)
    return Path(remaining[0]).name.lower() if remaining else None


def unwrapped_shell_command_parts(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        executable = Path(remaining[0]).name.lower()
        if executable in {"nohup", "setsid"}:
            remaining = remaining[1:]
            continue
        if executable == "env":
            remaining = strip_env_command_prefix(remaining[1:])
            continue
        if executable == "dbus-launch":
            remaining = strip_dbus_launch_prefix(remaining[1:])
            continue
        if executable == "dbus-run-session":
            remaining = strip_dbus_run_session_prefix(remaining[1:])
            continue
        if executable == "systemd-run":
            remaining = strip_systemd_run_prefix(remaining[1:])
            continue
        if executable == "timeout":
            remaining = strip_timeout_prefix(remaining[1:])
            continue
        if executable == "nice":
            remaining = strip_nice_prefix(remaining[1:])
            continue
        if executable == "ionice":
            remaining = strip_ionice_prefix(remaining[1:])
            continue
        if executable == "taskset":
            remaining = strip_taskset_prefix(remaining[1:])
            continue
        if executable == "stdbuf":
            remaining = strip_stdbuf_prefix(remaining[1:])
            continue
        break
    return remaining


TIMEOUT_OPTIONS_WITH_VALUES = {"-k", "-s", "--kill-after", "--signal"}
NICE_OPTIONS_WITH_VALUES = {"-n", "--adjustment"}
IONICE_OPTIONS_WITH_VALUES = {"-c", "-n", "-p", "--class", "--classdata", "--pid"}
STDBUF_OPTIONS_WITH_VALUES = {"-i", "-o", "-e", "--input", "--output", "--error"}


def strip_timeout_prefix(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            remaining = remaining[1:]
            break
        option = token.split("=", 1)[0]
        if option in TIMEOUT_OPTIONS_WITH_VALUES:
            remaining = remaining[2:] if "=" not in token and len(remaining) > 1 else remaining[1:]
            continue
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        break
    if not remaining:
        return []
    remaining = remaining[1:]
    if remaining and remaining[0] == "--":
        remaining = remaining[1:]
    return remaining


def strip_command_wrapper_options(
    parts: list[str],
    options_with_values: set[str],
    combined_value_prefixes: set[str] | None = None,
) -> list[str]:
    combined_prefixes = combined_value_prefixes or set()
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            return remaining[1:]
        option = token.split("=", 1)[0]
        if option in options_with_values:
            remaining = remaining[2:] if "=" not in token and len(remaining) > 1 else remaining[1:]
            continue
        if len(token) > 2 and token[:2] in combined_prefixes:
            remaining = remaining[1:]
            continue
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        break
    return remaining


def strip_nice_prefix(parts: list[str]) -> list[str]:
    return strip_command_wrapper_options(parts, NICE_OPTIONS_WITH_VALUES)


def strip_ionice_prefix(parts: list[str]) -> list[str]:
    return strip_command_wrapper_options(parts, IONICE_OPTIONS_WITH_VALUES, {"-c", "-n", "-p"})


def strip_taskset_prefix(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            remaining = remaining[1:]
            break
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        break
    if not remaining:
        return []
    return remaining[1:]


def strip_stdbuf_prefix(parts: list[str]) -> list[str]:
    return strip_command_wrapper_options(parts, STDBUF_OPTIONS_WITH_VALUES, {"-i", "-o", "-e"})


def strip_dbus_run_session_prefix(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            return remaining[1:]
        option = token.split("=", 1)[0]
        if option in {"--config-file", "--dbus-daemon"}:
            remaining = remaining[2:] if "=" not in token and len(remaining) > 1 else remaining[1:]
            continue
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        break
    return remaining


def strip_dbus_launch_prefix(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            return remaining[1:]
        option = token.split("=", 1)[0]
        if option in {"--autolaunch", "--config-file"}:
            remaining = remaining[2:] if "=" not in token and len(remaining) > 1 else remaining[1:]
            continue
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        break
    return remaining


SYSTEMD_RUN_OPTIONS_WITH_VALUES = {
    "-E",
    "-G",
    "-M",
    "-p",
    "--description",
    "--gid",
    "--machine",
    "--nice",
    "--on-active",
    "--on-boot",
    "--on-calendar",
    "--on-startup",
    "--on-unit-active",
    "--on-unit-inactive",
    "--property",
    "--service-type",
    "--setenv",
    "--slice",
    "--timer-property",
    "--uid",
    "--unit",
    "--working-directory",
}


def strip_systemd_run_prefix(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            return remaining[1:]
        option = token.split("=", 1)[0]
        if option in SYSTEMD_RUN_OPTIONS_WITH_VALUES:
            remaining = remaining[2:] if "=" not in token and len(remaining) > 1 else remaining[1:]
            continue
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        break
    return remaining


def strip_env_command_prefix(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            return remaining[1:]
        if token in {"-u", "--unset", "--chdir", "-C"}:
            remaining = remaining[2:] if len(remaining) > 1 else []
            continue
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            remaining = remaining[1:]
            continue
        break
    return remaining


def shell_pipeline_segments(command: str) -> list[list[str]]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token and all(character == "|" for character in token):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def segment_invokes_network_fetch(parts: list[str]) -> bool:
    executable = unwrapped_shell_executable_name(parts)
    return executable in {"curl", "wget"}


def segment_invokes_script_interpreter(parts: list[str]) -> bool:
    executable = unwrapped_shell_executable_name(parts)
    return executable in {"sh", "bash", "zsh", "fish", "dash", "ksh", "python", "python3", "ruby", "perl", "node"}


__all__ = [
    "segment_invokes_network_fetch",
    "segment_invokes_script_interpreter",
    "shell_command_segments",
    "shell_pipeline_segments",
    "strip_command_wrapper_options",
    "strip_dbus_launch_prefix",
    "strip_dbus_run_session_prefix",
    "strip_env_command_prefix",
    "strip_ionice_prefix",
    "strip_nice_prefix",
    "strip_stdbuf_prefix",
    "strip_systemd_run_prefix",
    "strip_taskset_prefix",
    "strip_timeout_prefix",
    "unwrapped_shell_command_parts",
    "unwrapped_shell_executable_name",
]
