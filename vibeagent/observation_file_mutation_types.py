from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .action_read_types import WriteFileItem


@dataclass(frozen=True)
class WriteFileObservation:
    kind: Literal["write_file"]
    path: str
    ok: bool
    message: str
    content: str = ""


@dataclass(frozen=True)
class CheckWriteFileObservation:
    kind: Literal["check_write_file"]
    path: str
    ok: bool
    message: str
    diff: str
    content: str = ""


@dataclass(frozen=True)
class WriteFileResult:
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class CheckWriteFileResult:
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class WriteFilesObservation:
    kind: Literal["write_files"]
    files: list[WriteFileResult]
    ok: bool
    message: str
    inputs: list[WriteFileItem] | None = None


@dataclass(frozen=True)
class CheckWriteFilesObservation:
    kind: Literal["check_write_files"]
    files: list[CheckWriteFileResult]
    ok: bool
    message: str
    inputs: list[WriteFileItem] | None = None


@dataclass(frozen=True)
class JsonSetObservation:
    kind: Literal["json_set"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckJsonSetObservation:
    kind: Literal["check_json_set"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class JsonRemoveObservation:
    kind: Literal["json_remove"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckJsonRemoveObservation:
    kind: Literal["check_json_remove"]
    path: str
    pointer: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class JsonPatchObservation:
    kind: Literal["json_patch"]
    path: str
    operation_count: int
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class CheckJsonPatchObservation:
    kind: Literal["check_json_patch"]
    path: str
    operation_count: int
    ok: bool
    message: str
    diff: str
