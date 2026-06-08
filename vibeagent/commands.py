from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .providers import get_model_text as get_provider_model_text
from .session import build_session_resume_context, format_session_summary, format_sessions, get_last_session_id, summarize_session


@dataclass(frozen=True)
class LocalCommand:
    type: Literal["exit", "help", "model", "chat", "code", "approval", "sessions", "session", "last", "resume"]
    argument: str | None = None


def parse_local_command(value: str) -> LocalCommand | None:
    # Recognize slash commands before sending anything to the model.
    trimmed = value.strip()
    if trimmed == "/exit":
        return LocalCommand(type="exit")
    if trimmed == "/help":
        return LocalCommand(type="help")
    if trimmed == "/model":
        return LocalCommand(type="model")
    if trimmed == "/approval" or trimmed.startswith("/approval "):
        return LocalCommand(type="approval", argument=trimmed[9:].strip() or None)
    if trimmed == "/sessions":
        return LocalCommand(type="sessions")
    if trimmed == "/last":
        return LocalCommand(type="last")
    if trimmed == "/session" or trimmed.startswith("/session "):
        return LocalCommand(type="session", argument=trimmed[8:].strip() or None)
    if trimmed == "/resume" or trimmed.startswith("/resume "):
        return LocalCommand(type="resume", argument=trimmed[8:].strip() or None)
    if trimmed == "/chat" or trimmed.startswith("/chat "):
        return LocalCommand(type="chat", argument=trimmed[5:].strip() or None)
    if trimmed == "/code" or trimmed.startswith("/code "):
        return LocalCommand(type="code", argument=trimmed[5:].strip() or None)
    return None


def is_exit_command(value: str) -> bool:
    # Helper for tests and callers that only care whether input is an exit command.
    command = parse_local_command(value)
    return command is not None and command.type == "exit"


def get_help_text() -> str:
    # Static help text shown by `/help` in the interactive prompt.
    return "\n".join(
        [
            "Commands:",
            "  /help   Show this help.",
            "  /model  Show model provider configuration.",
            "  /approval [ask|allow|deny]  Show or set the session approval policy.",
            "  /sessions  List recent local sessions.",
            "  /session <run-id>  Show a compact session summary.",
            "  /last   Show a compact summary of the newest session.",
            "  /resume [run-id|off]  Use a previous session summary as context, or clear it.",
            "  /chat   Switch to daily conversation mode, or chat once with /chat <message>.",
            "  /code   Switch to coding mode, or run one coding task with /code <task>.",
            "  /exit   Exit the interactive prompt.",
            "",
            "In coding mode, normal input is treated as a programming task.",
            "In chat mode, normal input is treated as daily conversation.",
        ]
    )


def get_model_text(env: dict[str, str | None] | None = None) -> str:
    # Show resolved model and key-source info without leaking secret material.
    return get_provider_model_text(env)


def get_sessions_text(project_root: str | Path = ".") -> str:
    return format_sessions(project_root)


def get_session_text(run_id: str | None, project_root: str | Path = ".") -> str:
    if not run_id:
        return "Usage: /session <run-id>"
    try:
        return format_session_summary(summarize_session(project_root, run_id))
    except ValueError as error:
        return str(error)


def get_last_session_text(project_root: str | Path = ".") -> str:
    run_id = get_last_session_id(project_root)
    if not run_id:
        return "No sessions found."
    return format_session_summary(summarize_session(project_root, run_id))


def get_resume_context(run_id: str | None, project_root: str | Path = ".") -> tuple[str | None, str | None, str]:
    if run_id and run_id.strip().lower() in {"off", "clear", "none"}:
        return None, None, "Resume context cleared."
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None, None, "No sessions found."
    try:
        context = build_session_resume_context(project_root, selected)
    except ValueError as error:
        return None, None, str(error)
    return selected, context, f"Resume context loaded from session {selected}."
