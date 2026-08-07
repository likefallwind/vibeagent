from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PythonImportRef:
    line: int
    kind: Literal["import", "from_import"]
    module: str
    name: str | None
    alias: str | None
    target: str
    local: bool


@dataclass(frozen=True)
class PythonDependenciesResult:
    path: str
    ok: bool
    module: str
    imports: list[PythonImportRef]
    local_modules: list[str]
    external_modules: list[str]
    message: str


@dataclass(frozen=True)
class PythonDependenciesObservation:
    kind: Literal["python_dependencies"]
    path: str | None
    files: list[PythonDependenciesResult]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class CodeImportRef:
    line: int
    kind: str
    source: str
    raw: str


@dataclass(frozen=True)
class CodeDependenciesResult:
    path: str
    ok: bool
    language: str
    imports: list[CodeImportRef]
    dependencies: list[str]
    message: str


@dataclass(frozen=True)
class CodeDependenciesObservation:
    kind: Literal["code_dependencies"]
    path: str | None
    files: list[CodeDependenciesResult]
    total: int
    truncated: bool
    ok: bool
    message: str


__all__ = [
    "CodeDependenciesObservation",
    "CodeDependenciesResult",
    "CodeImportRef",
    "PythonDependenciesObservation",
    "PythonDependenciesResult",
    "PythonImportRef",
]
