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
from .observation_code_definition_types import (
    CodeDefinition,
    CodeDefinitionsObservation,
    PythonDefinition,
    PythonDefinitionsObservation,
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
