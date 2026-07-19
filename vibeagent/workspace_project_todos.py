from __future__ import annotations

from .workspace_core import PROJECT_TODO_MARKERS, PROJECT_TODO_PATTERN, RunWorkspace
from .workspace_resolve import resolve_inside_run
from .workspace_search_files import list_search_files


def read_project_todos(
    workspace: RunWorkspace,
    relative_path: str | None = None,
    max_items: int = 100,
    max_files: int = 1000,
) -> dict[str, object]:
    if max_items < 1:
        raise ValueError("max_items must be at least 1.")
    if max_items > 500:
        raise ValueError("max_items must be at most 500.")
    if max_files < 1:
        raise ValueError("max_files must be at least 1.")
    if max_files > 5000:
        raise ValueError("max_files must be at most 5000.")

    selected_path = relative_path.strip() if relative_path else None
    files = list_search_files(workspace, selected_path)
    scanned_files = files[:max_files]
    todos: list[dict[str, object]] = []
    total = 0
    for relative in scanned_files:
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            match = PROJECT_TODO_PATTERN.search(line)
            if not match:
                continue
            total += 1
            if len(todos) >= max_items:
                continue
            todos.append(
                {
                    "path": relative,
                    "line": line_number,
                    "marker": match.group(1).upper(),
                    "text": line.strip(),
                }
            )

    truncated = len(files) > len(scanned_files) or total > len(todos)
    return {
        "ok": True,
        "todos": todos,
        "total": total,
        "truncated": truncated,
        "total_files": len(files),
        "scanned_files": len(scanned_files),
        "path": selected_path or ".",
        "markers": list(PROJECT_TODO_MARKERS),
        "message": f"Found {total} project TODO marker(s) in {len(scanned_files)}/{len(files)} scanned file(s).",
    }
