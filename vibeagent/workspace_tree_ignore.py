from __future__ import annotations

import fnmatch
from pathlib import Path


def normalize_list_tree_ignore(ignore: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for pattern in ignore:
        item = pattern.strip().replace("\\", "/")
        if not item:
            raise ValueError("ignore patterns must not be empty.")
        normalized.append(item)
    return tuple(normalized)


def list_tree_entry_matches_ignore(relative_path: str, ignore_globs: tuple[str, ...]) -> bool:
    if not ignore_globs:
        return False
    normalized_path = relative_path.strip("/").replace("\\", "/")
    basename = Path(normalized_path).name
    for pattern in ignore_globs:
        normalized_pattern = pattern.strip("/").replace("\\", "/")
        if not normalized_pattern:
            continue
        if normalized_pattern.endswith("/**"):
            prefix = normalized_pattern[:-3].rstrip("/")
            if normalized_path == prefix or normalized_path.startswith(f"{prefix}/"):
                return True
        target = normalized_path if "/" in normalized_pattern else basename
        if fnmatch.fnmatchcase(target, normalized_pattern):
            return True
    return False
