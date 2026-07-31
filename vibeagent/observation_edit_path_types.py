from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .action_types import DirectoryTransfer, MoveFileTransfer


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
