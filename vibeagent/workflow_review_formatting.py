from __future__ import annotations

from .types import ProcessInfo


def filter_handoff_status(status: str) -> str:
    lines: list[str] = []
    for raw_line in status.splitlines():
        path_text = raw_line[3:] if len(raw_line) > 3 else raw_line.strip()
        paths = path_text.split(" -> ") if " -> " in path_text else [path_text]
        if any(is_runtime_status_path(path.strip()) for path in paths):
            continue
        lines.append(raw_line)
    return "\n".join(lines)


def is_runtime_status_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return normalized == ".git" or normalized.startswith(".git/") or normalized == ".vibeagent" or normalized.startswith(".vibeagent/")


def format_review_file(item: dict[str, object]) -> str:
    states = [
        label
        for key, label in (
            ("staged", "staged"),
            ("unstaged", "unstaged"),
            ("untracked", "untracked"),
        )
        if item.get(key) is True
    ]
    changes = []
    insertions = int(item.get("staged_insertions") or 0) + int(item.get("unstaged_insertions") or 0)
    deletions = int(item.get("staged_deletions") or 0) + int(item.get("unstaged_deletions") or 0)
    if insertions:
        changes.append(f"+{insertions}")
    if deletions:
        changes.append(f"-{deletions}")
    if item.get("binary") is True:
        changes.append("binary")
    suffix = f" ({', '.join(states + changes)})" if states or changes else ""
    return f"    - {item.get('path')}{suffix}"


def format_review_check(item: dict[str, object]) -> str:
    availability = "available" if item.get("available") is not False else f"missing {item.get('missing_tool')}"
    return f"    - [{availability}] {item.get('command')} (cwd: {item.get('cwd')})"


def format_focused_test_command(item: dict[str, object]) -> str:
    availability = "available" if item.get("available") is not False else f"missing {item.get('missingTool')}"
    test = f"; test: {item.get('test')}" if item.get("test") else ""
    return f"    - [{availability}] {item.get('command')} (cwd: {item.get('cwd')}{test})"


def format_review_syntax_check(item: dict[str, object]) -> str:
    location = format_check_location(item.get("line"), item.get("column"))
    return f"    - {item.get('path')}: failed{location} - {item.get('message')}"


def format_review_process(process: ProcessInfo) -> str:
    return f"    - {process.process_id}: pid={process.pid}; cwd={process.cwd}; command={process.command}"


def pass_text(value: bool) -> str:
    return "pass" if value else "fail"


def clip_text(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}\n[context output truncated]"


def indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def format_check_location(line: int | None, column: int | None) -> str:
    if line is None:
        return ""
    if column is None:
        return f" at line {line}"
    return f" at line {line}, column {column}"
