from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ListFilesObservation:
    kind: Literal["list_files"]
    path: str
    files: list[str]
    total: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class ListTreeObservation:
    kind: Literal["list_tree"]
    path: str
    entries: list[str]
    total: int
    truncated: bool
    max_depth: int
    ok: bool
    message: str
    ignore: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReadFileObservation:
    kind: Literal["read_file"]
    path: str
    content: str
    message: str
    start_line: int | None = None
    line_count: int | None = None
    show_line_numbers: bool = False
    truncated: bool = False
    total_bytes: int | None = None
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextObservation:
    kind: Literal["read_file_context"]
    path: str
    ok: bool
    content: str
    message: str
    line: int
    context_lines: int = 20
    start_line: int = 1
    end_line: int = 0
    line_count: int = 0
    total_lines: int | None = None
    target_line_exists: bool = False
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextResult:
    path: str
    line: int
    context_lines: int
    ok: bool
    content: str
    message: str
    start_line: int = 1
    end_line: int = 0
    line_count: int = 0
    total_lines: int | None = None
    target_line_exists: bool = False
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileContextsObservation:
    kind: Literal["read_file_contexts"]
    contexts: list[ReadFileContextResult]
    message: str


@dataclass(frozen=True)
class OutputContextResult:
    path: str
    line: int
    column: int | None
    raw: str
    ok: bool
    content: str
    message: str
    context_lines: int = 5
    start_line: int = 1
    end_line: int = 0
    line_count: int = 0
    total_lines: int | None = None
    target_line_exists: bool = False
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class OutputContextsObservation:
    kind: Literal["output_contexts"]
    contexts: list[OutputContextResult]
    total_refs: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class OutputDiagnostic:
    severity: Literal["error", "warning", "failure", "info"]
    output_line: int
    text: str
    path: str | None = None
    line: int | None = None
    column: int | None = None
    raw: str | None = None


@dataclass(frozen=True)
class OutputDiagnosticsObservation:
    kind: Literal["output_diagnostics"]
    diagnostics: list[OutputDiagnostic]
    contexts: list[OutputContextResult]
    total_diagnostics: int
    total_refs: int
    diagnostics_truncated: bool
    contexts_truncated: bool
    message: str


@dataclass(frozen=True)
class TailFileObservation:
    kind: Literal["tail_file"]
    path: str
    ok: bool
    content: str
    message: str
    start_line: int = 1
    line_count: int = 0
    requested_line_count: int = 80
    total_lines: int | None = None
    truncated: bool = False
    max_bytes: int = 20_000


@dataclass(frozen=True)
class ReadFileResult:
    path: str
    ok: bool
    content: str
    message: str
    truncated: bool = False
    total_bytes: int | None = None
    max_bytes: int = 20_000
    show_line_numbers: bool = False


@dataclass(frozen=True)
class ReadFilesObservation:
    kind: Literal["read_files"]
    files: list[ReadFileResult]
    message: str


@dataclass(frozen=True)
class ReadFileRangeResult:
    path: str
    start_line: int
    line_count: int
    ok: bool
    content: str
    message: str
    truncated: bool
    total_bytes: int | None
    max_bytes: int


@dataclass(frozen=True)
class ReadFileRangesObservation:
    kind: Literal["read_file_ranges"]
    ranges: list[ReadFileRangeResult]
    message: str


@dataclass(frozen=True)
class FileInfoResult:
    path: str
    ok: bool
    exists: bool
    is_file: bool
    is_dir: bool
    size_bytes: int | None
    line_count: int | None
    is_binary: bool | None
    message: str


@dataclass(frozen=True)
class FileInfoObservation:
    kind: Literal["file_info"]
    files: list[FileInfoResult]
    message: str


@dataclass(frozen=True)
class ImageInfoResult:
    path: str
    ok: bool
    exists: bool
    is_file: bool
    size_bytes: int | None
    format: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    message: str


@dataclass(frozen=True)
class ImageInfoObservation:
    kind: Literal["image_info"]
    images: list[ImageInfoResult]
    message: str


@dataclass(frozen=True)
class ViewImageObservation:
    kind: Literal["view_image"]
    ok: bool
    path: str
    size_bytes: int | None
    format: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    max_bytes: int
    message: str


@dataclass(frozen=True)
class PythonSymbol:
    name: str
    kind: Literal["class", "function", "async_function", "type", "impl"]
    line: int
    end_line: int | None
    parent: str | None = None


@dataclass(frozen=True)
class PythonSymbolsResult:
    path: str
    ok: bool
    symbols: list[PythonSymbol]
    imports: list[str]
    message: str


@dataclass(frozen=True)
class PythonSymbolsObservation:
    kind: Literal["python_symbols"]
    files: list[PythonSymbolsResult]
    message: str


@dataclass(frozen=True)
class CodeOutlineResult:
    path: str
    ok: bool
    language: str | None
    symbols: list[PythonSymbol]
    imports: list[str]
    message: str


@dataclass(frozen=True)
class CodeOutlineObservation:
    kind: Literal["code_outline"]
    files: list[CodeOutlineResult]
    message: str


@dataclass(frozen=True)
class PythonCheckResult:
    path: str
    ok: bool
    line: int | None
    column: int | None
    message: str


@dataclass(frozen=True)
class PythonCheckObservation:
    kind: Literal["python_check"]
    path: str | None
    files: list[PythonCheckResult]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class ConfigCheckResult:
    path: str
    ok: bool
    format: str
    line: int | None
    column: int | None
    message: str


@dataclass(frozen=True)
class ConfigCheckObservation:
    kind: Literal["config_check"]
    path: str | None
    files: list[ConfigCheckResult]
    total: int
    truncated: bool
    ok: bool
    message: str
