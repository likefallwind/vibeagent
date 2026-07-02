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


def command_contains_dangerous_rm(lowered_command: str) -> bool:
    for args in shell_command_invocations(lowered_command, "rm"):
        recursive = False
        force = False
        targets: list[str] = []
        parse_options = True
        for token in args:
            if parse_options and token == "--":
                parse_options = False
                continue
            if parse_options and token.startswith("--"):
                option = token.split("=", 1)[0]
                if option == "--recursive":
                    recursive = True
                elif option == "--force":
                    force = True
                continue
            if parse_options and token.startswith("-") and token != "-":
                flags = token[1:]
                if "r" in flags:
                    recursive = True
                if "f" in flags:
                    force = True
                continue
            targets.append(token)
        if not recursive or not force:
            continue
        for target in targets:
            if is_dangerous_recursive_delete_target(target):
                return True
    return False


def is_dangerous_recursive_delete_target(path: str) -> bool:
    dangerous_targets = {
        "/",
        "/*",
        ".",
        "./",
        "*",
        "~",
        "~/",
        "$home",
        "${home}",
        "/home",
        "/home/",
        "/tmp",
        "/tmp/",
        "/var",
        "/var/",
        "/usr",
        "/usr/",
    }
    target = path.strip().strip("'\"").casefold()
    normalized = target.rstrip("/") if target not in {"/", "./", "~/"} else target
    return target in dangerous_targets or normalized in dangerous_targets


def command_contains_dangerous_git_clean(lowered_command: str) -> bool:
    for args in shell_command_invocations(lowered_command, "git"):
        if not args or args[0] != "clean":
            continue
        force = False
        directories = False
        dry_run = False
        for token in args[1:]:
            if token in {"--dry-run", "-n"}:
                dry_run = True
                continue
            if token == "--force":
                force = True
                continue
            if token == "--directory":
                directories = True
                continue
            if token.startswith("-") and not token.startswith("--"):
                flags = token.lstrip("-")
                if "f" in flags:
                    force = True
                if "d" in flags:
                    directories = True
                if "n" in flags:
                    dry_run = True
        if force and directories and not dry_run:
            return True
    return False


def command_recursively_changes_broad_permissions(lowered_command: str) -> bool:
    for executable in ("chmod", "chown", "chgrp"):
        for args in shell_command_invocations(lowered_command, executable):
            if permission_invocation_targets_broad_path_recursively(args):
                return True
    return False


def permission_invocation_targets_broad_path_recursively(args: list[str]) -> bool:
    recursive = False
    uses_reference = False
    operands: list[str] = []
    parse_options = True
    skip_next_option_arg = False
    for token in args:
        if skip_next_option_arg:
            skip_next_option_arg = False
            continue
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and token == "--reference":
            uses_reference = True
            skip_next_option_arg = True
            continue
        if parse_options and token.startswith("--"):
            option = token.split("=", 1)[0]
            if option == "--recursive":
                recursive = True
            elif option == "--reference":
                uses_reference = True
            continue
        if parse_options and token.startswith("-") and token != "-":
            flags = token.lstrip("-")
            if "r" in flags:
                recursive = True
            continue
        operands.append(token)
    if not recursive:
        return False
    target_start = 0 if uses_reference else 1
    targets = operands[target_start:]
    return any(is_dangerous_recursive_delete_target(target) for target in targets)


def shell_command_invocations(lowered_command: str, executable_name: str) -> list[list[str]]:
    invocations: list[list[str]] = []
    executable_path = r"(?:[^\s;&|]*/)?"
    pattern = re.compile(rf"(^|[;&|]\s*){executable_path}{re.escape(executable_name)}(?=\s|$)(?P<args>[^;&|]*)")
    for match in pattern.finditer(lowered_command):
        try:
            invocations.append(shlex.split(match.group("args")))
        except ValueError:
            continue
    return invocations


def command_writes_to_device(lowered_command: str) -> bool:
    for target in re.findall(r"(?:^|[\s;&|])(?:\d?>|>>|>|&>)\s*(/dev/[^\s;&|]+)", lowered_command):
        if is_raw_device_write_target(target):
            return True
    for target in re.findall(r"\bof=(/dev/[^\s;&|]+)", lowered_command):
        if is_raw_device_write_target(target):
            return True
    for args in shell_command_invocations(lowered_command, "tee"):
        if any(is_raw_device_write_target(token) for token in command_path_arguments(args)):
            return True
    for args in shell_command_invocations(lowered_command, "cp"):
        paths = command_path_arguments(args)
        if paths and is_raw_device_write_target(paths[-1]):
            return True
    return False


def command_path_arguments(args: list[str]) -> list[str]:
    paths: list[str] = []
    parse_options = True
    for token in args:
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and token.startswith("-") and token != "-":
            continue
        paths.append(token)
    return paths


def is_raw_device_write_target(path: str) -> bool:
    normalized = path.strip().strip("'\"")
    if not normalized.startswith("/dev/"):
        return False
    safe_character_devices = {
        "/dev/null",
        "/dev/zero",
        "/dev/full",
        "/dev/random",
        "/dev/urandom",
    }
    if normalized in safe_character_devices:
        return False
    raw_device_patterns = (
        r"/dev/[svhx]d[a-z]\d*",
        r"/dev/nvme\d+n\d+(?:p\d+)?",
        r"/dev/mmcblk\d+(?:p\d+)?",
        r"/dev/loop\d+",
        r"/dev/mapper/[^/]+",
        r"/dev/disk/(?:by-id|by-path|by-uuid|by-label)/[^/]+",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in raw_device_patterns)


def command_pipes_network_script_to_shell(lowered_command: str) -> bool:
    segments = shell_pipeline_segments(lowered_command)
    if len(segments) < 2:
        return False
    for index, segment in enumerate(segments[:-1]):
        if not segment_invokes_network_fetch(segment):
            continue
        for sink in segments[index + 1 :]:
            if segment_invokes_script_interpreter(sink):
                return True
    return False


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


def command_executes_powershell_network_script(lowered_command: str) -> bool:
    segment = r"(^|[;&|]\s*)"
    wrappers = r"(?:(?:nohup|setsid)\s+|env\s+(?:(?:--|-[A-Za-z0-9_-]+|[a-z_][a-z0-9_]*=\S+)\s+)*)*"
    executable_path = r"(?:[^\s;&|]*/)?"
    powershell = rf"{executable_path}(?:powershell|pwsh)(?:\.exe)?\b"
    fetch = r"\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b"
    execute = r"\|\s*(?:[^\s;&|]*/)?(?:iex|invoke-expression)\b"
    return bool(re.search(segment + wrappers + powershell + r".*" + fetch + r".*" + execute, lowered_command))


def command_launches_gui_application(lowered_command: str) -> bool:
    segment = r"(^|[;&|]\s*)"
    wrappers = r"(?:nohup\s+|setsid\s+|env\s+(?:[a-z_][a-z0-9_]*=\S+\s+)*)?"
    executable_path = r"(?:[./~]?\S*[/\\])?"
    launcher = (
        r"(?:explorer(?:\.exe)?|xdg-open|wslview|wsl-open|gio\s+open|"
        r"gnome-open|kde-open(?:5)?|open|nautilus|dolphin|thunar|nemo|pcmanfm|caja|konqueror|"
        r"code|code-insiders|cursor|windsurf|subl|mate|gedit|mousepad|kate|"
        r"firefox|google-chrome|google-chrome-stable|chromium|chromium-browser|microsoft-edge)\b"
    )
    file_protocol_handler = r"rundll32(?:\.exe)?\s+url\.dll,fileprotocolhandler\b"
    bare_start_gui = r"start\b\s+(?:\"[^\"]*\"\s+)?(?:\.|~|/|[a-z]:[\\/]|https?://|file:)"
    cmd_shell_gui = rf"{executable_path}cmd(?:\.exe)?\s+/[cs]\s+(?:{bare_start_gui}|explorer(?:\.exe)?\b|{file_protocol_handler})"
    powershell_gui = (
        rf"{executable_path}(?:powershell|pwsh)(?:\.exe)?\b.*\b"
        rf"(?:start-process|invoke-item|ii|explorer(?:\.exe)?|{file_protocol_handler})\b"
    )
    python_webbrowser = r"python(?:3(?:\.\d+)?)?\s+-m\s+webbrowser\b"
    return bool(
        re.search(segment + wrappers + executable_path + launcher, lowered_command)
        or re.search(segment + wrappers + executable_path + file_protocol_handler, lowered_command)
        or re.search(segment + wrappers + bare_start_gui, lowered_command)
        or re.search(segment + wrappers + cmd_shell_gui, lowered_command)
        or re.search(segment + wrappers + powershell_gui, lowered_command)
        or re.search(segment + wrappers + python_webbrowser, lowered_command)
    )


__all__ = [
    "command_contains_dangerous_git_clean",
    "command_contains_dangerous_rm",
    "command_executes_powershell_network_script",
    "command_launches_gui_application",
    "command_path_arguments",
    "command_pipes_network_script_to_shell",
    "command_recursively_changes_broad_permissions",
    "command_writes_to_device",
    "is_dangerous_recursive_delete_target",
    "is_raw_device_write_target",
    "permission_invocation_targets_broad_path_recursively",
    "segment_invokes_network_fetch",
    "segment_invokes_script_interpreter",
    "shell_command_invocations",
    "shell_command_segments",
    "shell_pipeline_segments",
    "strip_env_command_prefix",
    "unwrapped_shell_command_parts",
    "unwrapped_shell_executable_name",
]
