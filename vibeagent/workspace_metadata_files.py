from __future__ import annotations

import os
import stat
from pathlib import Path


def has_symlink_component(root: Path, path: Path) -> bool:
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def read_regular_file_bytes(path: Path, *, max_bytes: int, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"{label} must be a regular file.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(max_bytes + 1)
    finally:
        os.close(descriptor)
    if len(raw) > max_bytes:
        raise ValueError(f"{label} exceeds {max_bytes} bytes.")
    return raw


def parse_scalar_frontmatter(content: str, allowed_keys: frozenset[str]) -> tuple[dict[str, str], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content
    metadata: dict[str, str] = {}
    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        if stripped == "---":
            closing_index = index
            break
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key not in allowed_keys:
            continue
        metadata[key] = unquote_scalar(value.strip())
    if closing_index is None:
        return {}, content
    return metadata, "\n".join(lines[closing_index + 1 :])


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
