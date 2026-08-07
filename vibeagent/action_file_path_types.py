from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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
