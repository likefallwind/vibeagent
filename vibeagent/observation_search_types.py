from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SearchObservation:
    kind: Literal["search"]
    ok: bool
    query: str
    matches: list[str]
    total: int
    truncated: bool
    message: str
    path: str | None = None
    file_glob: str | None = None
    output_mode: Literal["lines", "content", "files_with_matches"] = "lines"
    regex: bool = False
    case_sensitive: bool = True
    context_lines: int = 0


@dataclass(frozen=True)
class SearchContextResult:
    path: str
    line: int
    matched_line: str
    content: str
    context_lines: int
    start_line: int
    end_line: int
    line_count: int
    total_lines: int | None
    truncated: bool
    max_bytes: int


@dataclass(frozen=True)
class SearchContextsObservation:
    kind: Literal["search_contexts"]
    ok: bool
    query: str
    contexts: list[SearchContextResult]
    total: int
    truncated: bool
    message: str
    path: str | None = None
    file_glob: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class FindFilesObservation:
    kind: Literal["find_files"]
    ok: bool
    query: str
    matches: list[str]
    total: int
    truncated: bool
    message: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = False
    include_dirs: bool = False


@dataclass(frozen=True)
class GlobObservation:
    kind: Literal["glob"]
    pattern: str
    matches: list[str]
    total: int
    truncated: bool
    ok: bool
    message: str
