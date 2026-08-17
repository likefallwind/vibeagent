from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .workspace_git_utils import combine_git_output, run_readonly_git
from .worktree_include_paths import (
    MAX_WORKTREE_INCLUDE_LIST_CHARS,
    MAX_WORKTREE_INCLUDE_PATH_CHARS,
    select_worktree_include_paths,
    validate_worktree_include_path,
)


MAX_WORKTREE_INCLUDE_BYTES = 64 * 1024
MAX_WORKTREE_INCLUDE_FILES = 1_000
MAX_WORKTREE_INCLUDE_FILE_BYTES = 16 * 1024 * 1024
MAX_WORKTREE_INCLUDE_TOTAL_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class WorktreeIncludeReport:
    source_top: Path
    target_top: Path
    copied_paths: tuple[str, ...] = ()
    copied_bytes: int = 0


def copy_worktree_includes(
    source_project_root: str | Path,
    target_project_root: str | Path,
) -> WorktreeIncludeReport:
    source_top = _git_top(source_project_root, "source")
    target_top = _git_top(target_project_root, "target")
    if _git_common_dir(source_top, "source") != _git_common_dir(target_top, "target"):
        raise ValueError("Source and target do not belong to the same git repository.")
    include_file = source_top / ".worktreeinclude"
    if not include_file.exists() and not include_file.is_symlink():
        return WorktreeIncludeReport(source_top, target_top)
    if include_file.is_symlink() or not include_file.is_file():
        raise ValueError(".worktreeinclude must be a regular non-symlink file.")
    try:
        include_size = include_file.stat().st_size
    except OSError as error:
        raise ValueError(f"Could not inspect .worktreeinclude: {error}") from error
    if include_size > MAX_WORKTREE_INCLUDE_BYTES:
        raise ValueError(
            f".worktreeinclude exceeds {MAX_WORKTREE_INCLUDE_BYTES} bytes."
        )
    try:
        include_text = include_file.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(".worktreeinclude must be valid UTF-8.") from error
    except OSError as error:
        raise ValueError(f"Could not read .worktreeinclude: {error}") from error
    if "\x00" in include_text:
        raise ValueError(".worktreeinclude must not contain NUL bytes.")

    selected, matched_count = select_worktree_include_paths(
        source_top,
        max_files=MAX_WORKTREE_INCLUDE_FILES,
    )
    if matched_count > MAX_WORKTREE_INCLUDE_FILES:
        raise ValueError(
            f".worktreeinclude matches {matched_count} files; limit is "
            f"{MAX_WORKTREE_INCLUDE_FILES}."
        )

    copies: list[tuple[str, Path, Path]] = []
    total_bytes = 0
    for relative in selected:
        source = _validated_file(source_top, relative, label="source")
        target = _validated_target(target_top, relative)
        try:
            size = source.stat().st_size
        except OSError as error:
            raise ValueError(
                f"Could not inspect .worktreeinclude source {relative}: {error}"
            ) from error
        if size > MAX_WORKTREE_INCLUDE_FILE_BYTES:
            raise ValueError(
                f".worktreeinclude source {relative} exceeds "
                f"{MAX_WORKTREE_INCLUDE_FILE_BYTES} bytes."
            )
        total_bytes += size
        if total_bytes > MAX_WORKTREE_INCLUDE_TOTAL_BYTES:
            raise ValueError(
                ".worktreeinclude matched files exceed the total copy limit of "
                f"{MAX_WORKTREE_INCLUDE_TOTAL_BYTES} bytes."
            )
        copies.append((relative, source, target))

    copied: list[str] = []
    for relative, source, target in copies:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)
        except OSError as error:
            raise ValueError(
                f"Could not copy .worktreeinclude source {relative}: {error}"
            ) from error
        copied.append(relative)
    return WorktreeIncludeReport(
        source_top,
        target_top,
        tuple(copied),
        total_bytes,
    )


def _git_top(root: str | Path, label: str) -> Path:
    result = run_readonly_git(root, ["rev-parse", "--show-toplevel"])
    if not result.ok or not result.stdout.strip():
        detail = combine_git_output(result)
        suffix = f": {detail}" if detail else "."
        raise ValueError(f"Could not resolve {label} git worktree{suffix}")
    top = Path(result.stdout.strip())
    if top.is_symlink() or not top.is_dir():
        raise ValueError(f"The {label} git worktree is not a safe directory: {top}")
    return top.resolve()


def _git_common_dir(root: Path, label: str) -> Path:
    result = run_readonly_git(
        root,
        ["rev-parse", "--path-format=absolute", "--git-common-dir"],
    )
    if not result.ok or not result.stdout.strip():
        detail = combine_git_output(result)
        suffix = f": {detail}" if detail else "."
        raise ValueError(f"Could not resolve {label} git common directory{suffix}")
    common = Path(result.stdout.strip())
    if common.is_symlink() or not common.is_dir():
        raise ValueError(
            f"The {label} git common directory is not safe: {common}"
        )
    return common.resolve()


def _validated_file(root: Path, relative: str, *, label: str) -> Path:
    validate_worktree_include_path(relative)
    candidate = root / relative
    _reject_symlink_components(root, candidate, label=label)
    if not candidate.is_file():
        raise ValueError(
            f".worktreeinclude {label} is not a regular file: {relative}"
        )
    return candidate


def _validated_target(root: Path, relative: str) -> Path:
    validate_worktree_include_path(relative)
    candidate = root / relative
    _reject_symlink_components(root, candidate.parent, label="target")
    if candidate.exists() or candidate.is_symlink():
        raise ValueError(
            f".worktreeinclude refuses to overwrite target path: {relative}"
        )
    return candidate


def _reject_symlink_components(root: Path, candidate: Path, *, label: str) -> None:
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(
            f".worktreeinclude {label} path is outside its worktree: {candidate}"
        ) from error
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(
                f".worktreeinclude {label} path contains a symbolic link: "
                f"{relative.as_posix()}"
            )


__all__ = [
    "MAX_WORKTREE_INCLUDE_BYTES",
    "MAX_WORKTREE_INCLUDE_FILES",
    "MAX_WORKTREE_INCLUDE_FILE_BYTES",
    "MAX_WORKTREE_INCLUDE_LIST_CHARS",
    "MAX_WORKTREE_INCLUDE_PATH_CHARS",
    "MAX_WORKTREE_INCLUDE_TOTAL_BYTES",
    "WorktreeIncludeReport",
    "copy_worktree_includes",
]
