from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class JsonSetAction:
    type: Literal["json_set"]
    path: str
    pointer: str
    value: Any
    create_missing: bool = False


@dataclass(frozen=True)
class CheckJsonSetAction:
    type: Literal["check_json_set"]
    path: str
    pointer: str
    value: Any
    create_missing: bool = False


@dataclass(frozen=True)
class JsonRemoveAction:
    type: Literal["json_remove"]
    path: str
    pointer: str


@dataclass(frozen=True)
class CheckJsonRemoveAction:
    type: Literal["check_json_remove"]
    path: str
    pointer: str


@dataclass(frozen=True)
class JsonPatchOperation:
    op: Literal["add", "replace", "remove"]
    path: str
    value: Any = None


@dataclass(frozen=True)
class JsonPatchAction:
    type: Literal["json_patch"]
    path: str
    operations: list[JsonPatchOperation]


@dataclass(frozen=True)
class CheckJsonPatchAction:
    type: Literal["check_json_patch"]
    path: str
    operations: list[JsonPatchOperation]
