from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .action_types import EditOperation
from .observation_edit_path_types import (
    CheckCopyDirectoriesObservation,
    CheckCopyDirectoryObservation,
    CheckCopyFileObservation,
    CheckCopyFilesObservation,
    CheckCreateDirectoriesObservation,
    CheckCreateDirectoryObservation,
    CheckDeleteEmptyDirectoriesObservation,
    CheckDeleteEmptyDirectoryObservation,
    CheckDeleteFileObservation,
    CheckDeleteFilesObservation,
    CheckMoveDirectoriesObservation,
    CheckMoveDirectoryObservation,
    CheckMoveFileObservation,
    CheckMoveFilesObservation,
    CheckSetExecutableObservation,
    CopyDirectoriesObservation,
    CopyDirectoryObservation,
    CopyFileObservation,
    CopyFilesObservation,
    CreateDirectoriesObservation,
    CreateDirectoryObservation,
    DeleteEmptyDirectoriesObservation,
    DeleteEmptyDirectoryObservation,
    DeleteFileObservation,
    DeleteFilesObservation,
    MoveDirectoriesObservation,
    MoveDirectoryObservation,
    MoveFileObservation,
    MoveFilesObservation,
    SetExecutableObservation,
)


@dataclass(frozen=True)
class EditFileObservation:
    kind: Literal["edit_file"]
    path: str
    ok: bool
    message: str
    diff: str
    old: str = ""
    new: str = ""


@dataclass(frozen=True)
class CheckEditFileObservation:
    kind: Literal["check_edit_file"]
    path: str
    ok: bool
    message: str
    diff: str
    old: str = ""
    new: str = ""


@dataclass(frozen=True)
class MultiEditObservation:
    kind: Literal["multi_edit_file"]
    path: str
    ok: bool
    message: str
    diff: str
    edits: list[EditOperation] | None = None


@dataclass(frozen=True)
class CheckMultiEditObservation:
    kind: Literal["check_multi_edit_file"]
    path: str
    ok: bool
    message: str
    diff: str
    edits: list[EditOperation] | None = None


@dataclass(frozen=True)
class ReplacePythonDefinitionObservation:
    kind: Literal["replace_python_definition"]
    symbol: str
    path: str | None
    definition_path: str | None
    qualified_name: str | None
    start_line: int | None
    end_line: int | None
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckReplacePythonDefinitionObservation:
    kind: Literal["check_replace_python_definition"]
    symbol: str
    path: str | None
    definition_path: str | None
    qualified_name: str | None
    start_line: int | None
    end_line: int | None
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class ReplaceLinesObservation:
    kind: Literal["replace_lines"]
    path: str
    start_line: int
    end_line: int
    ok: bool
    message: str
    diff: str
    content: str = ""


@dataclass(frozen=True)
class CheckReplaceLinesObservation:
    kind: Literal["check_replace_lines"]
    path: str
    start_line: int
    end_line: int
    ok: bool
    message: str
    diff: str
    content: str = ""


@dataclass(frozen=True)
class InsertLinesObservation:
    kind: Literal["insert_lines"]
    path: str
    line: int
    ok: bool
    message: str
    diff: str
    content: str = ""


@dataclass(frozen=True)
class CheckInsertLinesObservation:
    kind: Literal["check_insert_lines"]
    path: str
    line: int
    ok: bool
    message: str
    diff: str
    content: str = ""


@dataclass(frozen=True)
class AppendFileObservation:
    kind: Literal["append_file"]
    path: str
    ok: bool
    message: str
    diff: str
    content: str = ""


@dataclass(frozen=True)
class CheckAppendFileObservation:
    kind: Literal["check_append_file"]
    path: str
    ok: bool
    message: str
    diff: str
    content: str = ""


@dataclass(frozen=True)
class RegexReplaceObservation:
    kind: Literal["regex_replace"]
    path: str
    pattern: str
    count: int
    replacements: int
    ok: bool
    message: str
    diff: str
    replacement: str = ""
    case_sensitive: bool = True
    multiline: bool = False
    max_replacements: int = 100


@dataclass(frozen=True)
class CheckRegexReplaceObservation:
    kind: Literal["check_regex_replace"]
    path: str
    pattern: str
    count: int
    replacements: int
    ok: bool
    message: str
    diff: str
    replacement: str = ""
    case_sensitive: bool = True
    multiline: bool = False
    max_replacements: int = 100


@dataclass(frozen=True)
class CheckPatchObservation:
    kind: Literal["check_patch"]
    path: str
    ok: bool
    message: str
    diff: str
    patch: str = ""


@dataclass(frozen=True)
class CheckPatchesObservation:
    kind: Literal["check_patches"]
    files: list[str]
    ok: bool
    message: str
    diff: str
    patch: str = ""


@dataclass(frozen=True)
class PatchFileObservation:
    kind: Literal["patch_file"]
    path: str
    ok: bool
    message: str
    diff: str
    patch: str = ""


@dataclass(frozen=True)
class PatchFilesObservation:
    kind: Literal["patch_files"]
    files: list[str]
    ok: bool
    message: str
    diff: str
    patch: str = ""
