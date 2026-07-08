from __future__ import annotations

from .session_input import normalize_optional_run_id


def select_session_run_id(action_run_id: str | None, workspace_run_id: str) -> str:
    return normalize_optional_run_id(action_run_id) or workspace_run_id


def session_file_references(
    files: list[dict[str, object]], max_files: int
) -> tuple[list[dict[str, object]], int, int, bool]:
    shown_files = files[:max_files]
    references: list[dict[str, object]] = []
    for file_entry in shown_files:
        path = str(file_entry.get("path") or "").strip()
        if not path:
            continue
        uses = [
            str(use).strip()
            for use in file_entry.get("uses", [])
            if isinstance(use, str) and use.strip()
        ]
        references.append({"path": path, "uses": uses})
    return references, len(files), len(shown_files), len(files) > len(shown_files)
