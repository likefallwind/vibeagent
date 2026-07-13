from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class WriteFileAction:
    type: Literal["write_file"]
    path: str
    content: str


@dataclass(frozen=True)
class CheckWriteFileAction:
    type: Literal["check_write_file"]
    path: str
    content: str


@dataclass(frozen=True)
class WriteFileItem:
    path: str
    content: str


@dataclass(frozen=True)
class WriteFilesAction:
    type: Literal["write_files"]
    files: list[WriteFileItem]


@dataclass(frozen=True)
class CheckWriteFilesAction:
    type: Literal["check_write_files"]
    files: list[WriteFileItem]


@dataclass(frozen=True)
class ListFilesAction:
    type: Literal["list_files"]
    path: str | None = None


@dataclass(frozen=True)
class ListTreeAction:
    type: Literal["list_tree"]
    path: str | None = None
    max_depth: int = 3
    max_entries: int = 200
    ignore: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepoMapAction:
    type: Literal["repo_map"]
    path: str | None = None
    max_depth: int = 3
    max_files: int = 80
    max_symbols: int = 120


@dataclass(frozen=True)
class ReadFileAction:
    type: Literal["read_file"]
    path: str
    start_line: int | None = None
    line_count: int | None = None
    max_bytes: int = 20_000
    show_line_numbers: bool = False


@dataclass(frozen=True)
class ReadFileContextAction:
    type: Literal["read_file_context"]
    path: str
    line: int
    context_lines: int = 20
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextItem:
    path: str
    line: int
    context_lines: int = 20


@dataclass(frozen=True)
class ReadFileContextsAction:
    type: Literal["read_file_contexts"]
    contexts: list[ReadFileContextItem]
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class OutputContextsAction:
    type: Literal["output_contexts"]
    text: str
    context_lines: int = 5
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class OutputDiagnosticsAction:
    type: Literal["output_diagnostics"]
    text: str
    context_lines: int = 2
    max_diagnostics: int = 50
    max_contexts: int = 20
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class TailFileAction:
    type: Literal["tail_file"]
    path: str
    line_count: int = 80
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFilesAction:
    type: Literal["read_files"]
    paths: list[str]
    max_bytes_per_file: int = 20_000
    show_line_numbers: bool = False


@dataclass(frozen=True)
class ReadFileRangeItem:
    path: str
    start_line: int
    line_count: int = 120


@dataclass(frozen=True)
class ReadFileRangesAction:
    type: Literal["read_file_ranges"]
    ranges: list[ReadFileRangeItem]
    max_bytes_per_range: int = 20_000


@dataclass(frozen=True)
class FileInfoAction:
    type: Literal["file_info"]
    paths: list[str]


@dataclass(frozen=True)
class ImageInfoAction:
    type: Literal["image_info"]
    paths: list[str]


@dataclass(frozen=True)
class ViewImageAction:
    type: Literal["view_image"]
    path: str
    max_bytes: int = 5_000_000


@dataclass(frozen=True)
class SearchAction:
    type: Literal["search"]
    query: str
    path: str | None = None
    file_glob: str | None = None
    output_mode: Literal["lines", "content", "files_with_matches"] = "lines"
    regex: bool = False
    case_sensitive: bool = True
    max_matches: int = 80
    context_lines: int = 0


@dataclass(frozen=True)
class SearchContextsAction:
    type: Literal["search_contexts"]
    query: str
    path: str | None = None
    file_glob: str | None = None
    regex: bool = False
    case_sensitive: bool = True
    max_matches: int = 20
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class FindFilesAction:
    type: Literal["find_files"]
    query: str
    path: str | None = None
    regex: bool = False
    case_sensitive: bool = False
    include_dirs: bool = False
    max_matches: int = 100


@dataclass(frozen=True)
class GlobAction:
    type: Literal["glob"]
    pattern: str
    max_matches: int = 200
    include_dirs: bool = False
