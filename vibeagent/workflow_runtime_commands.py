from __future__ import annotations

from pathlib import Path

from .command_hard_blocks import blocked_command_examples, get_command_hard_block_report
from .workflow_doctor_commands import format_doctor_report_text, get_doctor_report, get_doctor_text
from .workspace_core import RunWorkspace
from .workspace import list_files, read_project_command_hints, read_project_instructions, read_workspace_snapshot


def get_status_report(mode: str, approval_policy: str, resume_run_id: str | None = None, chat_turns: int = 0) -> dict[str, object]:
    return {
        "mode": mode,
        "approval": approval_policy,
        "resume": resume_run_id or "",
        "chatTurns": chat_turns,
        "message": "Runtime status resolved.",
    }


def format_status_report_text(report: dict[str, object]) -> str:
    resume = str(report.get("resume") or "none")
    return "\n".join(
        [
            "Status:",
            f"  mode: {report.get('mode') or ''}",
            f"  approval: {report.get('approval') or ''}",
            f"  resume: {resume}",
            f"  chatTurns: {int(report.get('chatTurns', 0) or 0)}",
        ]
    )


def get_status_text(mode: str, approval_policy: str, resume_run_id: str | None = None, chat_turns: int = 0) -> str:
    return format_status_report_text(get_status_report(mode, approval_policy, resume_run_id, chat_turns))


def get_context_text(
    project_root: str | Path = ".",
    resume_run_id: str | None = None,
    resume_context: str | None = None,
) -> str:
    return format_context_report_text(get_context_report(project_root, resume_run_id, resume_context))


def get_context_report(
    project_root: str | Path = ".",
    resume_run_id: str | None = None,
    resume_context: str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-context", session_dir=root / ".vibeagent" / "sessions" / "local-context")
    instructions = read_project_instructions(workspace, max_bytes=4_000, max_files=10)
    command_hints = read_project_command_hints(workspace, max_bytes=4_000, max_files=20)
    snapshot = read_workspace_snapshot(workspace, max_bytes=4_000)
    return {
        "projectRoot": str(root),
        "resume": resume_run_id or "",
        "resumeChars": len(resume_context or ""),
        "instructions": {
            "found": bool(instructions),
            "text": _clip(instructions or "No AGENTS.md or CLAUDE.md instructions found.", 4_000),
        },
        "commandHints": {
            "found": bool(command_hints),
            "text": _clip(command_hints or "No project command hints found.", 4_000),
        },
        "workspaceSnapshot": {
            "text": _clip(snapshot, 4_000),
        },
        "message": "Prompt context resolved.",
    }


def format_context_report_text(report: dict[str, object]) -> str:
    instructions = report.get("instructions") if isinstance(report.get("instructions"), dict) else {}
    command_hints = report.get("commandHints") if isinstance(report.get("commandHints"), dict) else {}
    workspace_snapshot = report.get("workspaceSnapshot") if isinstance(report.get("workspaceSnapshot"), dict) else {}
    lines = [
        "Context:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  resume: {report.get('resume') or 'none'}",
        f"  resumeChars: {int(report.get('resumeChars', 0) or 0)}",
        "",
        "Project instructions:",
        _indent_block(str(instructions.get("text") or "")),
        "",
        "Project command hints:",
        _indent_block(str(command_hints.get("text") or "")),
        "",
        "Workspace snapshot:",
        _indent_block(str(workspace_snapshot.get("text") or "")),
    ]
    return "\n".join(lines)


def get_init_report(project_root: str | Path = ".", file_name: str | None = "AGENTS.md") -> dict[str, object]:
    root = Path(project_root).resolve()
    normalized = normalize_project_instructions_file_name(file_name)
    if normalized is None:
        return {
            "projectRoot": str(root),
            "requestedFile": file_name or "",
            "fileName": "",
            "path": "",
            "ok": False,
            "created": False,
            "exists": False,
            "error": "invalid_file",
            "message": "Usage: /init [AGENTS.md|CLAUDE.md]",
        }
    target = root / normalized
    if target.exists():
        return {
            "projectRoot": str(root),
            "requestedFile": file_name or "",
            "fileName": normalized,
            "path": str(target),
            "ok": True,
            "created": False,
            "exists": True,
            "error": "",
            "message": f"{normalized} already exists; no changes made.",
        }
    content = build_project_instructions_template(root)
    try:
        target.write_text(content, encoding="utf-8")
    except OSError as error:
        return {
            "projectRoot": str(root),
            "requestedFile": file_name or "",
            "fileName": normalized,
            "path": str(target),
            "ok": False,
            "created": False,
            "exists": target.exists(),
            "error": str(error),
            "message": f"Could not create {normalized}: {error}",
        }
    return {
        "projectRoot": str(root),
        "requestedFile": file_name or "",
        "fileName": normalized,
        "path": str(target),
        "ok": True,
        "created": True,
        "exists": True,
        "error": "",
        "message": f"Created {normalized}.",
    }


def format_init_report_text(report: dict[str, object]) -> str:
    return str(report.get("message") or "")


def init_project_instructions(project_root: str | Path = ".", file_name: str | None = "AGENTS.md") -> str:
    return format_init_report_text(get_init_report(project_root, file_name))


def normalize_project_instructions_file_name(file_name: str | None) -> str | None:
    value = (file_name or "AGENTS.md").strip()
    aliases = {
        "agents": "AGENTS.md",
        "agents.md": "AGENTS.md",
        "claude": "CLAUDE.md",
        "claude.md": "CLAUDE.md",
    }
    return aliases.get(value.lower())


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


def _clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}\n[context output truncated]"


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


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
