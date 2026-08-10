from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .session_names import resolve_session_reference
from .session_transcript_commands import get_transcript_text
from .workspace_resolve import resolve_mutation_path


EXPORT_MAX_EVENTS = 500
EXPORT_MAX_TEXT = 5_000


@dataclass(frozen=True)
class SessionExport:
    run_id: str
    text: str
    path: Path | None = None

    @property
    def message(self) -> str:
        if self.path is None:
            return self.text
        return f"Exported safe session transcript: {self.path}"


def export_session(project_root: Path, run_id: str, path: str | None = None) -> SessionExport:
    root = project_root.resolve()
    selected = resolve_session_reference(root, run_id)
    text = get_transcript_text(root, selected, max_events=EXPORT_MAX_EVENTS, max_text=EXPORT_MAX_TEXT)
    if text.startswith("Session not found:"):
        raise ValueError(text)
    if path is None:
        return SessionExport(selected, text)
    target = resolve_mutation_path(root, path)
    if not target.parent.is_dir():
        raise ValueError(f"Export parent directory does not exist: {target.parent}")
    if target.exists() and not target.is_file():
        raise ValueError(f"Export path is not a regular file: {path}")
    _atomic_write_text(target, text + "\n")
    return SessionExport(selected, text, target)


def _atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.vibeagent-{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


__all__ = ["EXPORT_MAX_EVENTS", "EXPORT_MAX_TEXT", "SessionExport", "export_session"]
