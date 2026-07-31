from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_read_types import ReadFileContextResult


@dataclass(frozen=True)
class GitDiffHunk:
    file: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: int
    deleted: int
    context: int
    header: str
    lines: list[str]
    lines_truncated: bool


@dataclass(frozen=True)
class UntrackedFilePreview:
    path: str
    size_bytes: int
    is_binary: bool
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class GitDiffObservation:
    kind: Literal["git_diff"]
    ok: bool
    diff: str
    path: str | None
    staged: bool
    truncated: bool
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class GitDiffHunksObservation:
    kind: Literal["git_diff_hunks"]
    ok: bool
    hunks: list[GitDiffHunk]
    total_hunks: int
    truncated: bool
    path: str | None
    staged: bool
    message: str


@dataclass(frozen=True)
class GitDiffContext:
    hunk: GitDiffHunk
    context: ReadFileContextResult


@dataclass(frozen=True)
class GitDiffContextsObservation:
    kind: Literal["git_diff_contexts"]
    ok: bool
    contexts: list[GitDiffContext]
    total_hunks: int
    truncated: bool
    path: str | None
    staged: bool
    context_lines: int
    message: str


@dataclass(frozen=True)
class GitLogObservation:
    kind: Literal["git_log"]
    ok: bool
    log: str
    max_count: int
    path: str | None
    message: str


@dataclass(frozen=True)
class GitShowObservation:
    kind: Literal["git_show"]
    ok: bool
    output: str
    rev: str
    path: str | None
    truncated: bool
    max_output_chars: int
    message: str


@dataclass(frozen=True)
class GitBlameObservation:
    kind: Literal["git_blame"]
    ok: bool
    blame: str
    path: str
    start_line: int | None
    line_count: int | None
    truncated: bool
    max_output_chars: int
    message: str
