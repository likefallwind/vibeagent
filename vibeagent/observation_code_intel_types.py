from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .observation_code_dependency_types import (
    CodeDependenciesObservation,
    CodeDependenciesResult,
    CodeImportRef,
    PythonDependenciesObservation,
    PythonDependenciesResult,
    PythonImportRef,
)
from .observation_code_rename_types import (
    CodeRenameObservation,
    CodeRenamePreviewFile,
    CodeRenamePreviewObservation,
    CodeRenameReplacement,
    PythonRenameObservation,
    PythonRenamePreviewFile,
    PythonRenamePreviewObservation,
    PythonRenameReplacement,
)
from .observation_code_reference_types import (
    CodeReference,
    CodeReferenceContextsObservation,
    CodeReferencesObservation,
    PythonReference,
    PythonReferenceContextsObservation,
    PythonReferencesObservation,
    ReferenceContextResult,
)
from .observation_read_types import CodeOutlineResult, PythonSymbol


@dataclass(frozen=True)
class CodeDefinition:
    path: str
    language: str
    name: str
    kind: str
    line: int
    end_line: int
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class CodeDefinitionsObservation:
    kind: Literal["code_definitions"]
    symbol: str
    path: str | None
    definitions: list[CodeDefinition]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonDefinition:
    path: str
    name: str
    qualified_name: str
    kind: Literal["class", "function", "async_function"]
    line: int
    end_line: int
    parent: str | None
    content: str
    truncated: bool
    message: str


@dataclass(frozen=True)
class PythonDefinitionsObservation:
    kind: Literal["python_definitions"]
    symbol: str
    path: str | None
    definitions: list[PythonDefinition]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonCall:
    path: str
    line: int
    column: int
    callee: str
    caller: str | None
    context: str


@dataclass(frozen=True)
class PythonCallsObservation:
    kind: Literal["python_calls"]
    symbol: str
    path: str | None
    calls: list[PythonCall]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonCallGraphObservation:
    kind: Literal["python_call_graph"]
    path: str | None
    edges: list[PythonCall]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class RepoMapPythonFile:
    path: str
    ok: bool
    imports: list[str]
    symbols: list[PythonSymbol]
    message: str


@dataclass(frozen=True)
class RepoMapObservation:
    kind: Literal["repo_map"]
    path: str
    tree: list[str]
    files: list[str]
    python_files: list[RepoMapPythonFile]
    code_files: list[CodeOutlineResult]
    total_tree_entries: int
    total_files: int
    truncated: bool
    ok: bool
    message: str
