from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RunWorkspace:
    root: Path
    run_id: str


def create_run_workspace(base_dir: str | Path | None = None, run_id: str | None = None) -> RunWorkspace:
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    current_run_id = run_id or make_run_id()
    root = (base / ".vibeagent" / "runs" / current_run_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return RunWorkspace(root=root, run_id=current_run_id)


def resolve_inside_run(root: str | Path, relative_path: str) -> Path:
    if not relative_path or not relative_path.strip():
        raise ValueError("Path must not be empty.")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {relative_path}")

    resolved_root = Path(root).resolve()
    resolved_path = (resolved_root / candidate).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"Path escapes the run directory: {relative_path}")

    return resolved_path


def write_run_file(workspace: RunWorkspace, relative_path: str, content: str) -> Path:
    target = resolve_inside_run(workspace.root, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def read_workspace_snapshot(workspace: RunWorkspace, max_bytes: int = 12_000) -> str:
    files = list_files(workspace.root)
    if not files:
        return "No files have been written yet."

    used = 0
    chunks: list[str] = []
    for file in files[:30]:
        absolute_path = resolve_inside_run(workspace.root, file)
        content = absolute_path.read_text(encoding="utf-8")
        remaining = max_bytes - used
        if remaining <= 0:
            chunks.append("\n[workspace snapshot truncated]")
            break

        shown = content[:remaining]
        used += len(shown)
        chunks.append(f"--- {file} ---\n{shown}")
        if len(shown) < len(content):
            chunks.append("[file truncated]")
            break

    return "\n\n".join(chunks)


def list_files(root: str | Path) -> list[str]:
    root_path = Path(root)
    files = [
        path.relative_to(root_path).as_posix()
        for path in root_path.rglob("*")
        if path.is_file()
    ]
    return sorted(files)


def make_run_id() -> str:
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
    return f"{safe_timestamp}-{uuid4().hex[:8]}"
