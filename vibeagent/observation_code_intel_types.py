from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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
from .observation_read_types import CodeOutlineResult, PythonSymbol


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


@dataclass(frozen=True)
class CodeReference:
    path: str
    language: str
    line: int
    column: int
    symbol: str
    context: str


@dataclass(frozen=True)
class CodeReferencesObservation:
    kind: Literal["code_references"]
    symbol: str
    path: str | None
    references: list[CodeReference]
    total: int
    truncated: bool
    ok: bool
    message: str


@dataclass(frozen=True)
class ReferenceContextResult:
    path: str
    line: int
    column: int
    symbol: str
    kind: str
    content: str
    context_lines: int
    start_line: int
    end_line: int
    line_count: int
    total_lines: int | None
    truncated: bool
    max_bytes: int
    language: str | None = None
    matched_line: str = ""


@dataclass(frozen=True)
class CodeReferenceContextsObservation:
    kind: Literal["code_reference_contexts"]
    symbol: str
    path: str | None
    contexts: list[ReferenceContextResult]
    total: int
    truncated: bool
    ok: bool
    message: str
    context_lines: int = 3
    max_bytes_per_context: int = 20_000

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


@dataclass(frozen=True)
class PythonReference:
    path: str
    line: int
    column: int
    kind: Literal["definition", "import", "reference"]
    context: str


@dataclass(frozen=True)
class PythonReferencesObservation:
    kind: Literal["python_references"]
    symbol: str
    path: str | None
    references: list[PythonReference]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str


@dataclass(frozen=True)
class PythonReferenceContextsObservation:
    kind: Literal["python_reference_contexts"]
    symbol: str
    path: str | None
    contexts: list[ReferenceContextResult]
    total: int
    truncated: bool
    ok: bool
    errors: list[str]
    message: str
    context_lines: int = 3
    max_bytes_per_context: int = 20_000
