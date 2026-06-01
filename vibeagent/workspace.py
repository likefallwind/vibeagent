from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RunWorkspace:
    root: Path
    run_id: str
    session_dir: Path


def create_run_workspace(base_dir: str | Path | None = None, run_id: str | None = None) -> RunWorkspace:
    # Project mode: work in the caller's directory and store task logs under .vibeagent/sessions/.
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    project_root = base.resolve()
    current_run_id = run_id or make_run_id()
    session_dir = (project_root / ".vibeagent" / "sessions" / current_run_id).resolve()
    session_dir.mkdir(parents=True, exist_ok=True)
    return RunWorkspace(root=project_root, run_id=current_run_id, session_dir=session_dir)


def resolve_inside_run(root: str | Path, relative_path: str) -> Path:
    # Enforce relative paths to prevent reads/writes outside the active project directory.
    if not relative_path or not relative_path.strip():
        raise ValueError("Path must not be empty.")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {relative_path}")

    resolved_root = Path(root).resolve()
    resolved_path = (resolved_root / candidate).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"Path escapes the project directory: {relative_path}")
    if is_protected_project_path(resolved_root, resolved_path):
        raise ValueError(f"Path is protected: {relative_path}")

    return resolved_path


def write_run_file(workspace: RunWorkspace, relative_path: str, content: str) -> Path:
    # Resolve, mkdir for parent directories, then write UTF-8 text into the project folder.
    target = resolve_inside_run(workspace.root, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def read_workspace_snapshot(workspace: RunWorkspace, max_bytes: int = 12_000) -> str:
    # Build a bounded project file listing so prompts remain informative but not oversized.
    files = list_files(workspace.root)
    if not files:
        return "No project files found."

    used = 0
    chunks: list[str] = []
    for file in files[:120]:
        content = file
        remaining = max_bytes - used
        if remaining <= 0:
            chunks.append("\n[workspace snapshot truncated]")
            break

        shown = content[:remaining]
        used += len(shown)
        chunks.append(shown)

    return "\n\n".join(chunks)


def list_files(root: str | Path) -> list[str]:
    # Enumerate all files in deterministic order so prompt diffs stay stable.
    root_path = Path(root).resolve()
    files = [
        path.relative_to(root_path).as_posix()
        for path in root_path.rglob("*")
        if path.is_file() and not should_ignore_path(root_path, path)
    ]
    return sorted(files)


def read_project_file(workspace: RunWorkspace, relative_path: str, max_bytes: int = 20_000) -> str:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = target.read_text(encoding="utf-8")
    if len(content) <= max_bytes:
        return content
    return f"{content[:max_bytes]}\n[file truncated]"


def edit_project_file(workspace: RunWorkspace, relative_path: str, old: str, new: str) -> tuple[Path, str]:
    target = resolve_inside_run(workspace.root, relative_path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {relative_path}")
    content = target.read_text(encoding="utf-8")
    if old not in content:
        raise ValueError(f"Old text was not found in {relative_path}")
    updated = content.replace(old, new, 1)
    target.write_text(updated, encoding="utf-8")
    return target, build_simple_diff(relative_path, content, updated)


def search_project(workspace: RunWorkspace, query: str, max_matches: int = 80) -> list[str]:
    if not query.strip():
        raise ValueError("Search query must not be empty.")

    matches: list[str] = []
    for relative in list_files(workspace.root):
        path = resolve_inside_run(workspace.root, relative)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if query in line:
                matches.append(f"{relative}:{line_number}: {line.strip()}")
                if len(matches) >= max_matches:
                    return matches
    return matches


def list_project_files(workspace: RunWorkspace, relative_path: str | None = None, max_files: int = 200) -> tuple[list[str], int]:
    base = resolve_inside_run(workspace.root, relative_path or ".")
    if not base.exists():
        raise ValueError(f"Path does not exist: {relative_path or '.'}")
    if base.is_file():
        return [base.relative_to(workspace.root).as_posix()], 1
    files = [
        path.relative_to(workspace.root).as_posix()
        for path in sorted(base.rglob("*"))
        if path.is_file() and not should_ignore_path(workspace.root, path)
    ]
    return files[:max_files], len(files)


def should_ignore_path(root: Path, path: Path) -> bool:
    relative_parts = path.resolve().relative_to(root).parts
    ignored = {".git", ".vibeagent", ".venv", "__pycache__", "node_modules", "dist", "build"}
    return any(part in ignored for part in relative_parts)


def is_protected_project_path(root: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return bool(parts and parts[0] in {".git", ".vibeagent"})


def build_simple_diff(path: str, before: str, after: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def make_run_id() -> str:
    # Timestamp+uuid-based ID keeps IDs unique without shared state.
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
    return f"{safe_timestamp}-{uuid4().hex[:8]}"
