from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


MAX_ADDITIONAL_DIRECTORIES = 20


def resolve_additional_directories(
    values: Sequence[str] | None,
    *,
    invocation_root: Path,
) -> tuple[Path, ...]:
    if not values:
        return ()
    if len(values) > MAX_ADDITIONAL_DIRECTORIES:
        raise ValueError(f"--add-dir supports at most {MAX_ADDITIONAL_DIRECTORIES} directories.")

    roots: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        if not value.strip():
            raise ValueError("--add-dir path cannot be empty.")
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = invocation_root / candidate
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as error:
            raise ValueError(f"Cannot resolve --add-dir '{value}': {error.strerror or error}") from error
        if not resolved.is_dir():
            raise ValueError(f"--add-dir must reference a directory: {value}")
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(resolved)
    return tuple(roots)


__all__ = ["MAX_ADDITIONAL_DIRECTORIES", "resolve_additional_directories"]
