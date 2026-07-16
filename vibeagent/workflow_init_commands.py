from __future__ import annotations

from pathlib import Path

from .local_command_workspace import local_command_workspace
from .workspace import list_files, read_project_command_hints


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
    workspace = local_command_workspace(root, "local-init")
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
