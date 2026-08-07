from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .action_file_path_types import (
    CheckCopyDirectoriesAction,
    CheckCopyDirectoryAction,
    CheckCopyFileAction,
    CheckCopyFilesAction,
    CheckCreateDirectoriesAction,
    CheckCreateDirectoryAction,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteFileAction,
    CheckDeleteFilesAction,
    CheckMoveDirectoriesAction,
    CheckMoveDirectoryAction,
    CheckMoveFileAction,
    CheckMoveFilesAction,
    CheckSetExecutableAction,
    CopyDirectoriesAction,
    CopyDirectoryAction,
    CopyFileAction,
    CopyFilesAction,
    CreateDirectoriesAction,
    CreateDirectoryAction,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoryAction,
    DeleteFileAction,
    DeleteFilesAction,
    DirectoryTransfer,
    MoveDirectoriesAction,
    MoveDirectoryAction,
    MoveFileAction,
    MoveFileTransfer,
    MoveFilesAction,
    SetExecutableAction,
)


@dataclass(frozen=True)
class EditFileAction:
    type: Literal["edit_file"]
    path: str
    old: str
    new: str


@dataclass(frozen=True)
class CheckEditFileAction:
    type: Literal["check_edit_file"]
    path: str
    old: str
    new: str


@dataclass(frozen=True)
class EditOperation:
    old: str
    new: str
    replace_all: bool = False


@dataclass(frozen=True)
class MultiEditAction:
    type: Literal["multi_edit_file"]
    path: str
    edits: list[EditOperation]


@dataclass(frozen=True)
class CheckMultiEditAction:
    type: Literal["check_multi_edit_file"]
    path: str
    edits: list[EditOperation]


@dataclass(frozen=True)
class ReplaceLinesAction:
    type: Literal["replace_lines"]
    path: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class CheckReplaceLinesAction:
    type: Literal["check_replace_lines"]
    path: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class InsertLinesAction:
    type: Literal["insert_lines"]
    path: str
    line: int
    content: str


@dataclass(frozen=True)
class CheckInsertLinesAction:
    type: Literal["check_insert_lines"]
    path: str
    line: int
    content: str


@dataclass(frozen=True)
class AppendFileAction:
    type: Literal["append_file"]
    path: str
    content: str


@dataclass(frozen=True)
class CheckAppendFileAction:
    type: Literal["check_append_file"]
    path: str
    content: str


@dataclass(frozen=True)
class RegexReplaceAction:
    type: Literal["regex_replace"]
    path: str
    pattern: str
    replacement: str
    count: int = 0
    case_sensitive: bool = True
    multiline: bool = False
    max_replacements: int = 100


@dataclass(frozen=True)
class CheckRegexReplaceAction:
    type: Literal["check_regex_replace"]
    path: str
    pattern: str
    replacement: str
    count: int = 0
    case_sensitive: bool = True
    multiline: bool = False
    max_replacements: int = 100


@dataclass(frozen=True)
class CheckPatchAction:
    type: Literal["check_patch"]
    path: str
    patch: str


@dataclass(frozen=True)
class CheckPatchesAction:
    type: Literal["check_patches"]
    patch: str


@dataclass(frozen=True)
class PatchFileAction:
    type: Literal["patch_file"]
    path: str
    patch: str


@dataclass(frozen=True)
class PatchFilesAction:
    type: Literal["patch_files"]
    patch: str
