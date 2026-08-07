from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


__all__ = [
    "CodeReference",
    "CodeReferenceContextsObservation",
    "CodeReferencesObservation",
    "PythonReference",
    "PythonReferenceContextsObservation",
    "PythonReferencesObservation",
    "ReferenceContextResult",
]
