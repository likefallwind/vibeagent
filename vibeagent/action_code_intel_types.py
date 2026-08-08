from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LspQueryAction:
    type: Literal["lsp_query"]
    operation: Literal["goToDefinition", "goToImplementation", "findReferences", "hover", "documentSymbol", "workspaceSymbol"]
    path: str | None = None
    line: int | None = None
    character: int | None = None
    symbol: str | None = None
    max_results: int = 50


@dataclass(frozen=True)
class PythonSymbolsAction:
    type: Literal["python_symbols"]
    paths: list[str]


@dataclass(frozen=True)
class CodeOutlineAction:
    type: Literal["code_outline"]
    paths: list[str]
    max_symbols: int = 200


@dataclass(frozen=True)
class PythonCheckAction:
    type: Literal["python_check"]
    path: str | None = None
    max_files: int = 200


@dataclass(frozen=True)
class ConfigCheckAction:
    type: Literal["config_check"]
    path: str | None = None
    max_files: int = 200


@dataclass(frozen=True)
class PythonDependenciesAction:
    type: Literal["python_dependencies"]
    path: str | None = None
    max_files: int = 100
    max_imports: int = 500


@dataclass(frozen=True)
class CodeDependenciesAction:
    type: Literal["code_dependencies"]
    path: str | None = None
    max_files: int = 100
    max_imports: int = 500


@dataclass(frozen=True)
class CodeReferencesAction:
    type: Literal["code_references"]
    symbol: str
    path: str | None = None
    max_matches: int = 200


@dataclass(frozen=True)
class CodeReferenceContextsAction:
    type: Literal["code_reference_contexts"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class CodeDefinitionsAction:
    type: Literal["code_definitions"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    max_lines: int = 80


@dataclass(frozen=True)
class CodeRenamePreviewAction:
    type: Literal["code_rename_preview"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 500


@dataclass(frozen=True)
class CodeRenameAction:
    type: Literal["code_rename"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 2000


@dataclass(frozen=True)
class PythonDefinitionsAction:
    type: Literal["python_definitions"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    max_lines: int = 120


@dataclass(frozen=True)
class ReplacePythonDefinitionAction:
    type: Literal["replace_python_definition"]
    symbol: str
    content: str
    path: str | None = None


@dataclass(frozen=True)
class CheckReplacePythonDefinitionAction:
    type: Literal["check_replace_python_definition"]
    symbol: str
    content: str
    path: str | None = None


@dataclass(frozen=True)
class PythonCallsAction:
    type: Literal["python_calls"]
    symbol: str
    path: str | None = None
    max_matches: int = 200


@dataclass(frozen=True)
class PythonCallGraphAction:
    type: Literal["python_call_graph"]
    path: str | None = None
    max_files: int = 100
    max_edges: int = 500


@dataclass(frozen=True)
class PythonReferencesAction:
    type: Literal["python_references"]
    symbol: str
    path: str | None = None
    max_matches: int = 200


@dataclass(frozen=True)
class PythonReferenceContextsAction:
    type: Literal["python_reference_contexts"]
    symbol: str
    path: str | None = None
    max_matches: int = 50
    context_lines: int = 3
    max_bytes_per_context: int = 20_000


@dataclass(frozen=True)
class PythonRenamePreviewAction:
    type: Literal["python_rename_preview"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 500


@dataclass(frozen=True)
class PythonRenameAction:
    type: Literal["python_rename"]
    symbol: str
    new_name: str
    path: str | None = None
    max_files: int = 100
    max_replacements: int = 2000
