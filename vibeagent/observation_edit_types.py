from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .action_types import DirectoryTransfer, EditOperation, MoveFileTransfer


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


@dataclass(frozen=True)
class CheckReplaceLinesObservation:
    kind: Literal["check_replace_lines"]
    path: str
    start_line: int
    end_line: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class InsertLinesObservation:
    kind: Literal["insert_lines"]
    path: str
    line: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckInsertLinesObservation:
    kind: Literal["check_insert_lines"]
    path: str
    line: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class AppendFileObservation:
    kind: Literal["append_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckAppendFileObservation:
    kind: Literal["check_append_file"]
    path: str
    ok: bool
    message: str
    diff: str


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


@dataclass(frozen=True)
class CheckPatchObservation:
    kind: Literal["check_patch"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckPatchesObservation:
    kind: Literal["check_patches"]
    files: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class PatchFileObservation:
    kind: Literal["patch_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class PatchFilesObservation:
    kind: Literal["patch_files"]
    files: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class DeleteFileObservation:
    kind: Literal["delete_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckDeleteFileObservation:
    kind: Literal["check_delete_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class DeleteFilesObservation:
    kind: Literal["delete_files"]
    paths: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckDeleteFilesObservation:
    kind: Literal["check_delete_files"]
    paths: list[str]
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class MoveFileObservation:
    kind: Literal["move_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveFileObservation:
    kind: Literal["check_move_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class MoveFilesObservation:
    kind: Literal["move_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveFilesObservation:
    kind: Literal["check_move_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyFileObservation:
    kind: Literal["copy_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyFileObservation:
    kind: Literal["check_copy_file"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyFilesObservation:
    kind: Literal["copy_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyFilesObservation:
    kind: Literal["check_copy_files"]
    transfers: list[MoveFileTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class MoveDirectoryObservation:
    kind: Literal["move_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveDirectoryObservation:
    kind: Literal["check_move_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class MoveDirectoriesObservation:
    kind: Literal["move_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckMoveDirectoriesObservation:
    kind: Literal["check_move_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyDirectoryObservation:
    kind: Literal["copy_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyDirectoryObservation:
    kind: Literal["check_copy_dir"]
    source: str
    destination: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CopyDirectoriesObservation:
    kind: Literal["copy_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCopyDirectoriesObservation:
    kind: Literal["check_copy_dirs"]
    transfers: list[DirectoryTransfer]
    ok: bool
    message: str


@dataclass(frozen=True)
class CreateDirectoryObservation:
    kind: Literal["create_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCreateDirectoryObservation:
    kind: Literal["check_create_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CreateDirectoriesObservation:
    kind: Literal["create_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckCreateDirectoriesObservation:
    kind: Literal["check_create_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class DeleteEmptyDirectoryObservation:
    kind: Literal["delete_empty_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoryObservation:
    kind: Literal["check_delete_empty_dir"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class DeleteEmptyDirectoriesObservation:
    kind: Literal["delete_empty_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoriesObservation:
    kind: Literal["check_delete_empty_dirs"]
    paths: list[str]
    ok: bool
    message: str


@dataclass(frozen=True)
class SetExecutableObservation:
    kind: Literal["set_executable"]
    path: str
    executable: bool
    ok: bool
    mode_before: str
    mode_after: str
    message: str


@dataclass(frozen=True)
class CheckSetExecutableObservation:
    kind: Literal["check_set_executable"]
    path: str
    executable: bool
    ok: bool
    mode_before: str
    mode_after: str
    message: str
