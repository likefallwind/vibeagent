from __future__ import annotations

import re
import shlex


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


__all__ = [
    "command_contains_dangerous_git_clean",
    "command_contains_dangerous_rm",
    "command_path_arguments",
    "command_recursively_changes_broad_permissions",
    "command_writes_to_device",
    "is_dangerous_recursive_delete_target",
    "is_raw_device_write_target",
    "permission_invocation_targets_broad_path_recursively",
    "shell_command_invocations",
]
