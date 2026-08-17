from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sqlite3

from .workspace_git_utils import combine_git_output, run_streaming_readonly_git


MAX_WORKTREE_INCLUDE_LIST_CHARS = 64 * 1024 * 1024
MAX_WORKTREE_INCLUDE_PATH_CHARS = 32_768


def select_worktree_include_paths(root: Path, *, max_files: int) -> tuple[list[str], int]:
    # Stream callbacks run on one collector thread and are joined before main-thread access.
    database = sqlite3.connect("", check_same_thread=False)
    try:
        database.execute("PRAGMA cache_size = -2048")
        database.execute("PRAGMA temp_store = FILE")
        database.execute(
            "CREATE TABLE ignored_paths (path TEXT PRIMARY KEY) WITHOUT ROWID"
        )
        database.execute(
            "CREATE TABLE selected_paths (path TEXT PRIMARY KEY) WITHOUT ROWID"
        )
        stream_ignored_paths(
            root,
            ("--exclude-standard",),
            lambda path: database.execute(
                "INSERT OR IGNORE INTO ignored_paths(path) VALUES (?)",
                (path,),
            ),
        )
        database.commit()

        selected: list[str] = []
        matched_count = 0

        def select(path: str) -> None:
            nonlocal matched_count
            if not copyable_worktree_include_path(path):
                return
            if database.execute(
                "SELECT 1 FROM ignored_paths WHERE path = ?",
                (path,),
            ).fetchone() is None:
                return
            inserted = database.execute(
                "INSERT OR IGNORE INTO selected_paths(path) VALUES (?)",
                (path,),
            )
            if inserted.rowcount == 0:
                return
            matched_count += 1
            if len(selected) < max_files:
                selected.append(path)

        stream_ignored_paths(
            root,
            ("--exclude-from=.worktreeinclude",),
            select,
        )
        return sorted(selected), matched_count
    except sqlite3.Error as error:
        raise ValueError(f"Could not index .worktreeinclude candidates: {error}") from error
    finally:
        database.close()


def stream_ignored_paths(
    root: Path,
    exclude_args: tuple[str, ...],
    consume: Callable[[str], None],
) -> None:
    parser = NulPathParser(consume)
    try:
        result = run_streaming_readonly_git(
            root,
            [
                "ls-files",
                "--others",
                "--ignored",
                *exclude_args,
                "-z",
                "--",
            ],
            parser.append,
        )
    except UnicodeDecodeError as error:
        raise ValueError(
            ".worktreeinclude matched a path that is not valid UTF-8."
        ) from error
    if not result.ok:
        if result.exit_code is None and "timed out" in result.stderr:
            raise ValueError(
                "git ls-files timed out while reading .worktreeinclude."
            )
        if result.exit_code is None and "not found" in result.stderr:
            raise ValueError("git executable was not found.")
        detail = combine_git_output(result)
        raise ValueError(
            "Could not evaluate .worktreeinclude"
            + (f": {detail}" if detail else ".")
        )
    parser.finish()


class NulPathParser:
    def __init__(self, consume: Callable[[str], None]) -> None:
        self._consume = consume
        self._pending = ""
        self._total_chars = 0

    def append(self, chunk: str) -> None:
        self._total_chars += len(chunk)
        if self._total_chars > MAX_WORKTREE_INCLUDE_LIST_CHARS:
            raise ValueError(
                ".worktreeinclude candidate paths exceed the "
                f"{MAX_WORKTREE_INCLUDE_LIST_CHARS}-character limit."
            )
        self._pending += chunk
        while "\0" in self._pending:
            path, self._pending = self._pending.split("\0", 1)
            if path:
                self._emit(path)
        self._check_path_size(self._pending)

    def finish(self) -> None:
        if self._pending:
            self._emit(self._pending)
            self._pending = ""

    def _emit(self, path: str) -> None:
        self._check_path_size(path)
        validate_worktree_include_path(path)
        self._consume(path)

    @staticmethod
    def _check_path_size(path: str) -> None:
        if len(path) > MAX_WORKTREE_INCLUDE_PATH_CHARS:
            raise ValueError(
                ".worktreeinclude returned a path exceeding "
                f"{MAX_WORKTREE_INCLUDE_PATH_CHARS} characters."
            )


def validate_worktree_include_path(value: str) -> None:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "\x00" in value
        or "\n" in value
        or "\r" in value
    ):
        raise ValueError(f".worktreeinclude returned an unsafe path: {value!r}")


def copyable_worktree_include_path(value: str) -> bool:
    parts = Path(value).parts
    if not parts or parts[0] in {".git", ".vibeagent"}:
        return False
    return parts[:2] != (".claude", "worktrees")


__all__ = [
    "MAX_WORKTREE_INCLUDE_LIST_CHARS",
    "MAX_WORKTREE_INCLUDE_PATH_CHARS",
    "NulPathParser",
    "select_worktree_include_paths",
    "stream_ignored_paths",
    "validate_worktree_include_path",
]
