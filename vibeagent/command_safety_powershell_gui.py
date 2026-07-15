from __future__ import annotations

import base64
from collections.abc import Callable
from pathlib import Path
import re
import shlex


POWERSHELL_SCRIPT_BLOCK_LAUNCHERS = {
    "foreach-object",
    "invoke-command",
    "start-job",
    "start-threadjob",
    "threadjob",
}
POWERSHELL_SCRIPT_BLOCK_PATTERN = re.compile(
    r"\b(?P<launcher>foreach-object|invoke-command|start-job|start-threadjob|threadjob)\b[^{]*\{(?P<body>[^{}]+)\}",
    re.IGNORECASE,
)
POWERSHELL_SCRIPTBLOCK_CREATE_PATTERN = re.compile(
    r"\[\s*scriptblock\s*\]\s*::\s*create\s*\(\s*(?P<quote>['\"])(?P<body>.*?)(?P=quote)\s*\)",
    re.IGNORECASE,
)


def powershell_invocation_launches_gui(
    args: list[str],
    nested_command_launches_gui: Callable[[str], bool],
) -> bool:
    joined = " ".join(args)
    if "url.dll,fileprotocolhandler" in joined:
        return True
    encoded_payload = powershell_encoded_command_payload(args)
    if encoded_payload:
        return powershell_payload_launches_gui(encoded_payload, nested_command_launches_gui)
    payload = powershell_command_payload(args)
    if payload:
        return powershell_payload_launches_gui(payload, nested_command_launches_gui)
    return False


POWERSHELL_DIRECT_GUI_LAUNCHERS = {
    "explorer",
    "explorer.exe",
    "ii",
    "invoke-item",
    "saps",
    "start-process",
}


def powershell_payload_launches_gui(
    payload: str,
    nested_command_launches_gui: Callable[[str], bool],
) -> bool:
    return (
        nested_command_launches_gui(payload)
        or powershell_direct_payload_launches_gui(payload, nested_command_launches_gui)
        or powershell_expression_payload_launches_gui(payload, nested_command_launches_gui)
        or powershell_script_block_payload_launches_gui(payload, nested_command_launches_gui)
        or powershell_scriptblock_create_payload_launches_gui(payload, nested_command_launches_gui)
    )


def powershell_direct_payload_launches_gui(
    payload: str,
    nested_command_launches_gui: Callable[[str], bool],
) -> bool:
    try:
        parts = shlex.split(payload)
    except ValueError:
        return False
    if not parts:
        return False
    launcher = _shell_token_basename(parts[0])
    if launcher not in POWERSHELL_DIRECT_GUI_LAUNCHERS:
        return False
    if launcher in {"explorer", "explorer.exe"}:
        return True
    if launcher in {"start-process", "saps"}:
        target = powershell_start_process_target(parts[1:])
        return bool(target and powershell_launch_target_is_gui(target, nested_command_launches_gui))
    return any(powershell_direct_target_launches_gui(part) for part in parts[1:] if not part.startswith("-"))


POWERSHELL_START_PROCESS_VALUE_OPTIONS = {
    "-argumentlist",
    "-credential",
    "-filepath",
    "-loaduserprofile",
    "-redirectstandarderror",
    "-redirectstandardinput",
    "-redirectstandardoutput",
    "-verb",
    "-wait",
    "-windowstyle",
    "-workingdirectory",
}


def powershell_start_process_target(args: list[str]) -> str:
    positional: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        option, separator, inline_value = token.partition(":")
        normalized = normalize_powershell_option(option, preserve_slash=False)
        if normalized == "-filepath":
            return inline_value.strip() if separator else args[index + 1].strip() if index + 1 < len(args) else ""
        if normalized in POWERSHELL_START_PROCESS_VALUE_OPTIONS:
            index += 2 if not separator else 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        positional.append(token)
        index += 1
    return positional[0] if positional else ""


def powershell_launch_target_is_gui(
    target: str,
    nested_command_launches_gui: Callable[[str], bool],
) -> bool:
    return powershell_direct_target_launches_gui(target) or nested_command_launches_gui(target)


def powershell_direct_target_launches_gui(target: str) -> bool:
    if re.match(r"(?:\.|~|[a-z]:[\\/]|https?://|file:)", target, re.IGNORECASE):
        return True
    return _shell_token_basename(target) in {"explorer", "explorer.exe"}


POWERSHELL_ENCODED_COMMAND_OPTIONS = {"-e", "-ec", "-enc", "-encodedcommand"}


def powershell_encoded_command_payload(args: list[str]) -> str:
    for index, token in enumerate(args):
        option, separator, inline_value = token.partition(":")
        if normalize_powershell_option(option, preserve_slash=False) not in POWERSHELL_ENCODED_COMMAND_OPTIONS:
            continue
        encoded = inline_value.strip() if separator else args[index + 1].strip() if index + 1 < len(args) else ""
        if not encoded:
            return ""
        try:
            return base64.b64decode(encoded, validate=True).decode("utf-16le").strip()
        except (ValueError, UnicodeDecodeError):
            return ""
    return ""


def powershell_script_block_payload_launches_gui(
    payload: str,
    nested_command_launches_gui: Callable[[str], bool],
) -> bool:
    for match in POWERSHELL_SCRIPT_BLOCK_PATTERN.finditer(payload):
        launcher = match.group("launcher").lower()
        if launcher not in POWERSHELL_SCRIPT_BLOCK_LAUNCHERS:
            continue
        body = match.group("body").strip()
        if body and nested_command_launches_gui(body):
            return True
    return False


def powershell_scriptblock_create_payload_launches_gui(
    payload: str,
    nested_command_launches_gui: Callable[[str], bool],
) -> bool:
    for match in POWERSHELL_SCRIPTBLOCK_CREATE_PATTERN.finditer(payload):
        body = match.group("body").strip()
        if body and nested_command_launches_gui(body):
            return True
    return False


def powershell_expression_payload_launches_gui(
    payload: str,
    nested_command_launches_gui: Callable[[str], bool],
) -> bool:
    try:
        parts = shlex.split(payload)
    except ValueError:
        return False
    for index, token in enumerate(parts[:-1]):
        if token.lower() not in {"iex", "invoke-expression"}:
            continue
        nested_parts = parts[index + 1 :]
        if nested_parts and nested_parts[0].lower() in {"-command", "/command"}:
            nested_parts = nested_parts[1:]
        nested = " ".join(nested_parts).strip()
        if nested and nested_command_launches_gui(nested):
            return True
    return False


def powershell_command_payload(args: list[str]) -> str:
    command_options = {"-c", "-command", "/c", "/command"}
    for index, token in enumerate(args):
        option, separator, inline_value = token.partition(":")
        normalized_option = normalize_powershell_option(option, preserve_slash=True)
        if normalized_option in command_options:
            return (
                " ".join(part for part in [inline_value, *args[index + 1 :]] if part).strip()
                if separator
                else " ".join(args[index + 1 :]).strip()
            )
    if args and args[0].lower() not in {"-file", "/file"} and not args[0].startswith("-"):
        return " ".join(args).strip()
    return ""


def normalize_powershell_option(option: str, *, preserve_slash: bool) -> str:
    prefix = "/" if preserve_slash and option.startswith("/") else "-"
    return prefix + option.lstrip("-/").lower()


def _shell_token_basename(token: str) -> str:
    return Path(token.replace("\\", "/")).name.lower()


__all__ = [
    "powershell_invocation_launches_gui",
]
