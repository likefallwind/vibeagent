from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
from typing import Literal

from .config import resolve_cost_rates, resolve_provider_config
from .providers import get_model_text as get_provider_model_text
from .session import build_session_resume_context, format_cost, format_session_summary, format_sessions, format_usage, get_last_session_id, summarize_session
from .workspace import RunWorkspace, list_files, read_project_command_hints, read_project_instructions, read_workspace_snapshot


@dataclass(frozen=True)
class LocalCommand:
    type: Literal["exit", "help", "model", "status", "context", "init", "doctor", "clear", "usage", "cost", "chat", "code", "approval", "sessions", "session", "last", "resume", "compact"]
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
    if trimmed == "/status":
        return LocalCommand(type="status")
    if trimmed == "/context":
        return LocalCommand(type="context")
    if trimmed == "/init":
        return LocalCommand(type="init")
    if trimmed == "/doctor":
        return LocalCommand(type="doctor")
    if trimmed == "/clear":
        return LocalCommand(type="clear")
    if trimmed == "/usage":
        return LocalCommand(type="usage")
    if trimmed == "/cost":
        return LocalCommand(type="cost")
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
    if trimmed == "/compact" or trimmed.startswith("/compact "):
        return LocalCommand(type="compact", argument=trimmed[9:].strip() or None)
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
            "  /status Show current mode, approval policy, and resume context.",
            "  /context  Show the current project context sources for coding tasks.",
            "  /init   Create a starter AGENTS.md if one does not exist.",
            "  /doctor Show local configuration and workspace diagnostics.",
            "  /clear  Clear chat history and loaded resume context.",
            "  /usage  Show local session usage from recorded events.",
            "  /cost   Show token usage and configured cost estimate.",
            "  /approval [ask|allow|deny]  Show or set the session approval policy.",
            "  /sessions  List recent local sessions.",
            "  /session <run-id>  Show a compact session summary.",
            "  /last   Show a compact summary of the newest session.",
            "  /resume [run-id|off]  Use a previous session summary as context, or clear it.",
            "  /compact [run-id]  Compact the newest or selected session into resume context.",
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


def get_status_text(mode: str, approval_policy: str, resume_run_id: str | None = None, chat_turns: int = 0) -> str:
    resume = resume_run_id or "none"
    return "\n".join(
        [
            "Status:",
            f"  mode: {mode}",
            f"  approval: {approval_policy}",
            f"  resume: {resume}",
            f"  chatTurns: {chat_turns}",
        ]
    )


def get_context_text(
    project_root: str | Path = ".",
    resume_run_id: str | None = None,
    resume_context: str | None = None,
) -> str:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-context", session_dir=root / ".vibeagent" / "sessions" / "local-context")
    instructions = read_project_instructions(workspace, max_bytes=4_000, max_files=10)
    command_hints = read_project_command_hints(workspace, max_bytes=4_000, max_files=20)
    snapshot = read_workspace_snapshot(workspace, max_bytes=4_000)
    lines = [
        "Context:",
        f"  projectRoot: {root}",
        f"  resume: {resume_run_id or 'none'}",
        f"  resumeChars: {len(resume_context or '')}",
        "",
        "AGENTS.md:",
        _indent_block(_clip(instructions or "No AGENTS.md instructions found.", 4_000)),
        "",
        "Project command hints:",
        _indent_block(_clip(command_hints or "No project command hints found.", 4_000)),
        "",
        "Workspace snapshot:",
        _indent_block(_clip(snapshot, 4_000)),
    ]
    return "\n".join(lines)


def init_project_instructions(project_root: str | Path = ".") -> str:
    root = Path(project_root).resolve()
    target = root / "AGENTS.md"
    if target.exists():
        return "AGENTS.md already exists; no changes made."
    content = build_project_instructions_template(root)
    try:
        target.write_text(content, encoding="utf-8")
    except OSError as error:
        return f"Could not create AGENTS.md: {error}"
    return "Created AGENTS.md."


def get_doctor_text(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> str:
    root = Path(project_root).resolve()
    lines = [
        "Doctor:",
        f"  projectRoot: {root}",
        f"  python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        f"  sessionsDir: {_exists_text(root / '.vibeagent' / 'sessions')}",
        f"  projectConfig: {_exists_text(root / '.vibeagent' / 'config.json')}",
        f"  gitRepo: {_exists_text(root / '.git')}",
        f"  agentsMd: {_exists_text(root / 'AGENTS.md')}",
    ]
    try:
        config = resolve_provider_config(env)
        key_text = f"configured via {config.api_key_source}" if config.api_key_source else "missing"
        lines.extend(
            [
                f"  provider: {config.provider}",
                f"  model: {config.model}",
                f"  baseUrl: {config.base_url}",
                f"  apiKey: {key_text}",
            ]
        )
    except ValueError as error:
        lines.append(f"  provider: {error}")

    rates, cost_errors = resolve_cost_rates(env)
    configured_rates = sum(
        rate is not None
        for rate in (
            rates.input_usd_per_million,
            rates.output_usd_per_million,
            rates.cache_creation_usd_per_million,
            rates.cache_read_usd_per_million,
        )
    )
    if cost_errors:
        lines.append("  costRates: invalid")
        lines.extend(f"    - {error}" for error in cost_errors)
    else:
        lines.append(f"  costRates: {configured_rates}/4 configured")

    lines.append("  executables:")
    for name in ("python3", "git", "npm"):
        lines.append(f"    - {name}: {'available' if shutil.which(name) else 'missing'}")
    return "\n".join(lines)


def build_project_instructions_template(project_root: str | Path = ".") -> str:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-init", session_dir=root / ".vibeagent" / "sessions" / "local-init")
    top_entries = _top_level_entries(root)
    command_hints = read_project_command_hints(workspace, max_bytes=2_000, max_files=10)
    command_lines = _extract_command_lines(command_hints or "")
    structure_lines = top_entries or ["- Add the main source, test, and documentation paths for this project."]
    command_section = command_lines or ["- Add the project-specific test, build, lint, and run commands."]
    return "\n".join(
        [
            "# Repository Guidelines",
            "",
            "## Project Structure & Module Organization",
            *structure_lines,
            "",
            "## Build, Test, and Development Commands",
            *command_section,
            "",
            "## Coding Style & Naming Conventions",
            "- Follow the language and framework conventions already used in this repository.",
            "- Keep changes focused, explicit, and consistent with nearby code.",
            "",
            "## Testing Guidelines",
            "- Run the narrowest relevant checks after changes, then broader checks when shared behavior changes.",
            "- Prefer deterministic tests and avoid real external provider calls unless validating integration behavior.",
            "",
            "## Security & Configuration Tips",
            "- Do not commit API keys, credentials, local runtime artifacts, or generated caches.",
            "- Preserve workspace safety rules and avoid changing git history unless explicitly requested.",
            "",
        ]
    )


def get_sessions_text(project_root: str | Path = ".") -> str:
    return format_sessions(project_root)


def get_usage_text(project_root: str | Path = ".") -> str:
    return format_usage(project_root)


def get_cost_text(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> str:
    rates, errors = resolve_cost_rates(env)
    return format_cost(project_root, rates, errors)


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


def get_compact_context(run_id: str | None, project_root: str | Path = ".") -> tuple[str | None, str | None, str]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None, None, "No sessions found."
    try:
        context = build_session_resume_context(project_root, selected)
    except ValueError as error:
        return None, None, str(error)
    return selected, context, f"Compacted context loaded from session {selected}."


def _clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}\n[context output truncated]"


def _indent_block(value: str) -> str:
    return "\n".join(f"  {line}" if line else "" for line in value.splitlines())


def _exists_text(path: Path) -> str:
    return "yes" if path.exists() else "no"


def _top_level_entries(project_root: Path) -> list[str]:
    try:
        files = list_files(project_root)
    except OSError:
        return []
    seen: list[str] = []
    for relative in files:
        name = relative.split("/", 1)[0]
        if name not in seen:
            seen.append(name)
        if len(seen) >= 12:
            break
    return [f"- `{name}`" for name in seen]


def _extract_command_lines(command_hints: str) -> list[str]:
    lines: list[str] = []
    current_cwd = "."
    for raw_line in command_hints.splitlines():
        line = raw_line.strip()
        if line.startswith("Cwd: "):
            current_cwd = line[5:] or "."
        elif line.startswith("- "):
            lines.append(f"- `{line[2:]}` from `{current_cwd}`")
        if len(lines) >= 8:
            break
    return lines
