from __future__ import annotations

from pathlib import Path
import re

from .command_safety_powershell_gui import powershell_invocation_launches_gui
from .command_safety_shell import shell_command_segments, unwrapped_shell_command_parts


GUI_LAUNCHER_EXECUTABLES = {
    "explorer",
    "explorer.exe",
    "xdg-open",
    "wslview",
    "wsl-open",
    "gvfs-open",
    "gnome-open",
    "kde-open",
    "kde-open5",
    "kde-open6",
    "kioclient",
    "kioclient5",
    "kioclient6",
    "exo-open",
    "mimeopen",
    "rifle",
    "open",
    "nautilus",
    "dolphin",
    "thunar",
    "nemo",
    "pcmanfm",
    "caja",
    "konqueror",
    "code",
    "code-insiders",
    "cursor",
    "windsurf",
    "subl",
    "mate",
    "gedit",
    "mousepad",
    "kate",
    "firefox",
    "sensible-browser",
    "x-www-browser",
    "www-browser",
    "gnome-www-browser",
    "google-chrome",
    "chrome",
    "google-chrome-stable",
    "brave-browser",
    "vivaldi",
    "vivaldi-stable",
    "opera",
    "librewolf",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "msedge",
    "msedge.exe",
    "notepad",
    "notepad.exe",
    "mspaint",
    "mspaint.exe",
    "wordpad",
    "wordpad.exe",
    "write",
    "write.exe",
}

WINDOWS_START_VALUE_OPTIONS = {"d", "node"}
WINDOWS_START_FLAG_OPTIONS = {
    "abovenormal",
    "affinity",
    "b",
    "belownormal",
    "high",
    "i",
    "low",
    "machine",
    "max",
    "min",
    "normal",
    "realtime",
    "separate",
    "shared",
    "wait",
}


def command_launches_gui_application(lowered_command: str) -> bool:
    if command_segments_launch_gui_application(lowered_command):
        return True
    segment = r"(^|[;&|]\s*)"
    env_option = r"(?:(?:-u|--unset|--chdir|-C)\s+\S+|--|-[a-z0-9_-]+|[a-z_][a-z0-9_]*=\S+)"
    wrappers = rf"(?:(?:nohup|setsid)\s+|env\s+(?:{env_option}\s+)*)*"
    executable_path = r"(?:[./~]?\S*[/\\])?"
    launcher = (
        r"(?:explorer(?:\.exe)?|xdg-open|wslview|wsl-open|gvfs-open|gio\s+open|"
        r"gnome-open|kde-open(?:5|6)?|kioclient(?:5|6)?|exo-open|mimeopen|rifle|"
        r"open|nautilus|dolphin|thunar|nemo|pcmanfm|caja|konqueror|"
        r"code|code-insiders|cursor|windsurf|subl|mate|gedit|mousepad|kate|"
        r"firefox|sensible-browser|x-www-browser|www-browser|gnome-www-browser|"
        r"google-chrome|google-chrome-stable|brave-browser|vivaldi|vivaldi-stable|opera|librewolf|"
        r"chromium|chromium-browser|microsoft-edge)\b"
    )
    file_protocol_handler = r"rundll32(?:\.exe)?\s+url\.dll,fileprotocolhandler\b"
    bare_start_flag_options = "|".join(sorted(WINDOWS_START_FLAG_OPTIONS))
    bare_start_value_options = "|".join(sorted(WINDOWS_START_VALUE_OPTIONS))
    bare_start_option = (
        rf"/(?:{bare_start_flag_options})(?:\s+|$)"
        rf"|/(?:{bare_start_value_options})\s+\S+\s+"
    )
    bare_start_gui = rf"start\b\s+(?:\"[^\"]*\"\s+)?(?:(?:{bare_start_option})*)?(?:\.|~|[a-z]:[\\/]|https?://|file:)"
    cmd_option = r"/[a-z]"
    cmd_shell_gui = rf"{executable_path}cmd(?:\.exe)?\s+(?:{cmd_option}\s+)*/[ck]\s+\"?(?:{bare_start_gui}|explorer(?:\.exe)?\b|{file_protocol_handler})"
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


def command_segments_launch_gui_application(lowered_command: str) -> bool:
    for segment in shell_command_segments(lowered_command):
        if command_segment_launches_gui_application(segment):
            return True
    return False


def command_segment_launches_gui_application(parts: list[str]) -> bool:
    remaining = unwrapped_shell_command_parts(parts)
    if not remaining:
        return False
    executable = shell_token_basename(remaining[0])
    args = remaining[1:]
    if executable in GUI_LAUNCHER_EXECUTABLES:
        return True
    if executable == "gio" and args[:1] == ["open"]:
        return True
    if executable == "start":
        return start_invocation_launches_gui(args)
    if executable in {"rundll32", "rundll32.exe"}:
        return rundll32_invocation_launches_gui(args)
    if executable in {"cmd", "cmd.exe"}:
        return cmd_invocation_launches_gui(args)
    if executable in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}:
        return powershell_invocation_launches_gui(args, command_launches_gui_application)
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?", executable):
        return args[:2] == ["-m", "webbrowser"]
    return False


def cmd_invocation_launches_gui(args: list[str]) -> bool:
    for index, token in enumerate(args):
        if token in {"/c", "/k"}:
            payload = " ".join(args[index + 1 :])
            return bool(payload and command_launches_gui_application(payload))
    return False


def rundll32_invocation_launches_gui(args: list[str]) -> bool:
    return bool(args and args[0] == "url.dll,fileprotocolhandler")


def start_invocation_launches_gui(args: list[str]) -> bool:
    remaining = windows_start_target_candidates(args)
    if not remaining:
        return False
    return any(windows_start_target_launches_gui(target) for target in remaining)


def windows_start_target_candidates(args: list[str]) -> list[str]:
    remaining = list(args)
    candidates: list[str] = []
    while remaining:
        token = remaining.pop(0)
        if token == "":
            continue
        if token.startswith("/"):
            option = token.lstrip("/")
            if option in WINDOWS_START_VALUE_OPTIONS and remaining:
                remaining.pop(0)
            continue
        candidates.append(token)
        # Windows start treats the first quoted argument as a window title.
        # The shell parser drops quote metadata, so keep scanning for a GUI
        # target after a non-GUI first token instead of trusting only token 0.
    return candidates


def windows_start_target_launches_gui(target: str) -> bool:
    if bool(re.match(r"(?:\.|~|[a-z]:[\\/]|https?://|file:)", target)):
        return True
    return shell_token_basename(target) in GUI_LAUNCHER_EXECUTABLES


def shell_token_basename(token: str) -> str:
    return Path(token.replace("\\", "/")).name.lower()


__all__ = [
    "command_launches_gui_application",
]
