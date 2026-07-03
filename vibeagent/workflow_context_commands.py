from __future__ import annotations

from pathlib import Path

from .workspace import read_project_command_hints, read_project_instructions, read_workspace_snapshot
from .workspace_core import RunWorkspace


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


def _clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}\n[context output truncated]"


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())
