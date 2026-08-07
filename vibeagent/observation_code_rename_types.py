from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CodeRenameReplacement:
    path: str
    line: int
    column: int
    end_column: int
    language: str
    old: str
    new: str
    context: str


@dataclass(frozen=True)
class CodeRenamePreviewFile:
    path: str
    language: str
    replacements: list[CodeRenameReplacement]
    diff: str
    truncated: bool


@dataclass(frozen=True)
class CodeRenamePreviewObservation:
    kind: Literal["code_rename_preview"]
    symbol: str
    new_name: str
    path: str | None
    files: list[CodeRenamePreviewFile]
    total_replacements: int
    total_files: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class CodeRenameObservation:
    kind: Literal["code_rename"]
    symbol: str
    new_name: str
    path: str | None
    files: list[CodeRenamePreviewFile]
    total_replacements: int
    total_files: int
    ok: bool
    errors: list[str]
    message: str
    diff: str


@dataclass(frozen=True)
class PythonRenameReplacement:
    path: str
    line: int
    column: int
    end_column: int
    kind: str
    old: str
    new: str
    context: str


@dataclass(frozen=True)
class PythonRenamePreviewFile:
    path: str
    replacements: list[PythonRenameReplacement]
    diff: str
    truncated: bool


@dataclass(frozen=True)
class PythonRenamePreviewObservation:
    kind: Literal["python_rename_preview"]
    symbol: str
    new_name: str
    path: str | None
    files: list[PythonRenamePreviewFile]
    total_replacements: int
    total_files: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonRenameObservation:
    kind: Literal["python_rename"]
    symbol: str
    new_name: str
    path: str | None
    files: list[PythonRenamePreviewFile]
    total_replacements: int
    total_files: int
    ok: bool
    errors: list[str]
    message: str
    diff: str


__all__ = [
    "CodeRenameObservation",
    "CodeRenamePreviewFile",
    "CodeRenamePreviewObservation",
    "CodeRenameReplacement",
    "PythonRenameObservation",
    "PythonRenamePreviewFile",
    "PythonRenamePreviewObservation",
    "PythonRenameReplacement",
]
