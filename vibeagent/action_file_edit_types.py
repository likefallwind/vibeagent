from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


@dataclass(frozen=True)
class DeleteFileAction:
    type: Literal["delete_file"]
    path: str


@dataclass(frozen=True)
class CheckDeleteFileAction:
    type: Literal["check_delete_file"]
    path: str


@dataclass(frozen=True)
class DeleteFilesAction:
    type: Literal["delete_files"]
    paths: list[str]


@dataclass(frozen=True)
class CheckDeleteFilesAction:
    type: Literal["check_delete_files"]
    paths: list[str]


@dataclass(frozen=True)
class MoveFileTransfer:
    source: str
    destination: str


@dataclass(frozen=True)
class MoveFileAction:
    type: Literal["move_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckMoveFileAction:
    type: Literal["check_move_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class MoveFilesAction:
    type: Literal["move_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class CheckMoveFilesAction:
    type: Literal["check_move_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class CopyFileAction:
    type: Literal["copy_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckCopyFileAction:
    type: Literal["check_copy_file"]
    source: str
    destination: str


@dataclass(frozen=True)
class CopyFilesAction:
    type: Literal["copy_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class CheckCopyFilesAction:
    type: Literal["check_copy_files"]
    transfers: list[MoveFileTransfer]


@dataclass(frozen=True)
class MoveDirectoryAction:
    type: Literal["move_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckMoveDirectoryAction:
    type: Literal["check_move_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class DirectoryTransfer:
    source: str
    destination: str


@dataclass(frozen=True)
class MoveDirectoriesAction:
    type: Literal["move_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CheckMoveDirectoriesAction:
    type: Literal["check_move_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CopyDirectoryAction:
    type: Literal["copy_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class CheckCopyDirectoryAction:
    type: Literal["check_copy_dir"]
    source: str
    destination: str


@dataclass(frozen=True)
class CopyDirectoriesAction:
    type: Literal["copy_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CheckCopyDirectoriesAction:
    type: Literal["check_copy_dirs"]
    transfers: list[DirectoryTransfer]


@dataclass(frozen=True)
class CreateDirectoryAction:
    type: Literal["create_dir"]
    path: str


@dataclass(frozen=True)
class CheckCreateDirectoryAction:
    type: Literal["check_create_dir"]
    path: str


@dataclass(frozen=True)
class CreateDirectoriesAction:
    type: Literal["create_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class CheckCreateDirectoriesAction:
    type: Literal["check_create_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class DeleteEmptyDirectoryAction:
    type: Literal["delete_empty_dir"]
    path: str


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoryAction:
    type: Literal["check_delete_empty_dir"]
    path: str


@dataclass(frozen=True)
class DeleteEmptyDirectoriesAction:
    type: Literal["delete_empty_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class CheckDeleteEmptyDirectoriesAction:
    type: Literal["check_delete_empty_dirs"]
    paths: list[str]


@dataclass(frozen=True)
class SetExecutableAction:
    type: Literal["set_executable"]
    path: str
    executable: bool = True


@dataclass(frozen=True)
class CheckSetExecutableAction:
    type: Literal["check_set_executable"]
    path: str
    executable: bool = True
