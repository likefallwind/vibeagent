from __future__ import annotations

from pathlib import Path
import re
import shlex

from .command_safety_node import node_script_blocked_command_reason
from .command_safety_python import python_script_blocked_command_reason
from .command_safety_wrappers import unwrapped_shell_command_parts


def interpreter_heredoc_blocked_command_reason(command: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    heredoc = shell_heredoc_script(command)
    if heredoc is None:
        return None
    parts, script = heredoc
    parts = unwrapped_shell_command_parts(parts)
    if not parts:
        return None
    executable = Path(parts[0]).name.lower()
    args = parts[1:]
    if executable in {"node", "nodejs"} and interpreter_stdin_script_args(args, node=True):
        return node_script_blocked_command_reason(script, depth)
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?", executable) and interpreter_stdin_script_args(args, node=False):
        return python_script_blocked_command_reason(script, depth)
    return None


def shell_heredoc_script(command: str) -> tuple[list[str], str] | None:
    match = re.match(
        r"(?s)^\s*(?P<prefix>.*?)\s*<<-?\s*(?P<quote>['\"]?)(?P<tag>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)[ \t]*\r?\n"
        r"(?P<body>.*)\r?\n(?P=tag)[ \t]*$",
        command,
    )
    if not match:
        return None
    try:
        parts = shlex.split(match.group("prefix"))
    except ValueError:
        return None
    if not parts:
        return None
    return parts, match.group("body")


def interpreter_stdin_script_args(args: list[str], *, node: bool) -> bool:
    has_operand = False
    skip_next = False
    options_with_values = {"-r", "--require", "--import", "--loader"} if node else {"-c", "-m", "-W", "-X"}
    for token in args:
        if skip_next:
            skip_next = False
            continue
        if token == "--":
            continue
        if token == "-":
            return True
        option = token.split("=", 1)[0]
        if option in {"-e", "--eval", "-p", "--print", "-c", "-m"}:
            return False
        if option in options_with_values and "=" not in token:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        has_operand = True
    return not has_operand


__all__ = [
    "interpreter_heredoc_blocked_command_reason",
    "interpreter_stdin_script_args",
    "shell_heredoc_script",
]
