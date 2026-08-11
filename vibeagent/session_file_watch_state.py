from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


FILE_WATCH_STATE = "file-watch.json"
MAX_WATCH_PATHS = 100
MAX_WATCH_PATH_CHARS = 4_096
MAX_WATCH_STATE_BYTES = 512_000


def read_dynamic_watch_paths(workspace: RunWorkspace) -> tuple[Path, ...]:
    path = workspace.session_dir / FILE_WATCH_STATE
    try:
        if path.is_symlink() or not path.is_file():
            return ()
        payload = json.loads(
            read_regular_file_bytes(
                path,
                max_bytes=MAX_WATCH_STATE_BYTES,
                label="File watch state",
            ).decode("utf-8")
        )
        values = payload.get("paths") if isinstance(payload, dict) else None
        if not isinstance(values, list):
            return ()
        return normalize_dynamic_watch_paths(workspace, values)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return ()


def write_dynamic_watch_paths(
    workspace: RunWorkspace,
    values: tuple[str, ...],
) -> tuple[Path, ...]:
    paths = normalize_dynamic_watch_paths(workspace, values)
    target = workspace.session_dir / FILE_WATCH_STATE
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError(f"File watch state path is not a regular file: {target}")
    encoded = json.dumps(
        {"paths": [str(path) for path in paths]},
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > MAX_WATCH_STATE_BYTES:
        raise ValueError("File watch state exceeds its storage limit.")
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return paths


def normalize_dynamic_watch_paths(
    workspace: RunWorkspace,
    values: list[object] | tuple[str, ...],
) -> tuple[Path, ...]:
    if len(values) > MAX_WATCH_PATHS:
        raise ValueError(f"watchPaths exceeds {MAX_WATCH_PATHS} entries.")
    roots = (workspace.root.resolve(), *(root.resolve() for root in workspace.additional_roots))
    normalized: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > MAX_WATCH_PATH_CHARS
            or "\x00" in value
        ):
            raise ValueError("watchPaths entries must be bounded non-empty strings.")
        candidate = Path(value)
        if not candidate.is_absolute():
            raise ValueError("watchPaths entries must be absolute paths.")
        lexical = Path(os.path.abspath(candidate))
        lexical_root = _containing_root(roots, lexical)
        if lexical_root is None:
            raise ValueError(f"Watch path escapes the active workspace: {value}")
        if has_symlink_component(lexical_root, lexical):
            raise ValueError(f"Watch path uses a symbolic link: {value}")
        resolved = lexical.resolve(strict=False)
        if _containing_root(roots, resolved) != lexical_root:
            raise ValueError(f"Watch path resolves outside its workspace root: {value}")
        relative = lexical.relative_to(lexical_root)
        if relative.parts[:1] and relative.parts[0] in {".git", ".vibeagent"}:
            raise ValueError(f"Watch path is protected: {value}")
        if lexical not in seen:
            seen.add(lexical)
            normalized.append(lexical)
    return tuple(normalized)


def _containing_root(roots: tuple[Path, ...], path: Path) -> Path | None:
    matches = [root for root in roots if path == root or root in path.parents]
    return max(matches, key=lambda root: len(root.parts), default=None)


__all__ = [
    "FILE_WATCH_STATE",
    "MAX_WATCH_PATHS",
    "normalize_dynamic_watch_paths",
    "read_dynamic_watch_paths",
    "write_dynamic_watch_paths",
]
