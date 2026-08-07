from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_nonnegative_int,
    parse_optional_positive_int,
)
from .action_parsing_code_intel_fields import parse_dependency_limits, parse_optional_path
from .action_parsing_code_queries import CODE_QUERY_ACTION_TYPES, parse_code_query_action
from .action_parsing_code_rename import (
    parse_code_rename_action,
    parse_python_rename_action,
    parse_replace_python_definition_action,
)
from .types import (
    PythonCallGraphAction,
    PythonCallsAction,
    PythonDefinitionsAction,
    PythonDependenciesAction,
    PythonReferenceContextsAction,
    PythonReferencesAction,
)


CODE_INTEL_ACTION_TYPES = CODE_QUERY_ACTION_TYPES | {
    "python_dependencies",
    "code_rename_preview",
    "code_rename",
    "python_definitions",
    "python_calls",
    "check_replace_python_definition",
    "replace_python_definition",
    "python_call_graph",
    "python_references",
    "python_reference_contexts",
    "python_rename_preview",
    "python_rename",
}


def parse_code_intel_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in CODE_INTEL_ACTION_TYPES:
        return None

    rename_action = parse_code_rename_action(action_type, value, raw)
    if rename_action is not None:
        return rename_action
    replace_definition_action = parse_replace_python_definition_action(action_type, value, raw)
    if replace_definition_action is not None:
        return replace_definition_action
    python_rename_action = parse_python_rename_action(action_type, value, raw)
    if python_rename_action is not None:
        return python_rename_action

    code_query_action = parse_code_query_action(action_type, value, raw)
    if code_query_action is not None:
        return code_query_action

    if action_type == "python_dependencies":
        path = parse_optional_path(value.get("path"), raw, "python_dependencies")
        max_files, max_imports = parse_dependency_limits(value, raw)
        return PythonDependenciesAction(
            type="python_dependencies",
            path=path,
            max_files=max_files,
            max_imports=max_imports,
        )

    if action_type == "python_definitions":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        max_lines = value.get("max_lines", 120)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_definitions action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_definitions action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=200) or 50
        max_lines = parse_optional_positive_int(max_lines, "max_lines", raw, maximum=1000) or 120
        return PythonDefinitionsAction(
            type="python_definitions",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )

    if action_type == "python_calls":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 200)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_calls action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_calls action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return PythonCallsAction(
            type="python_calls",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
        )

    if action_type == "python_call_graph":
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_edges = value.get("max_edges", 500)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_call_graph action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_edges = parse_optional_positive_int(max_edges, "max_edges", raw, maximum=2000) or 500
        return PythonCallGraphAction(
            type="python_call_graph",
            path=path,
            max_files=max_files,
            max_edges=max_edges,
        )

    if action_type == "python_references":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 200)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_references action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_references action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return PythonReferencesAction(type="python_references", symbol=symbol.strip(), path=path, max_matches=max_matches)

    if action_type == "python_reference_contexts":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        context_lines = value.get("context_lines", 3)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_reference_contexts action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_reference_contexts action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=100) or 50
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200_000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return PythonReferenceContextsAction(
            type="python_reference_contexts",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    raise AssertionError(f"Unhandled code intelligence action type: {action_type!r}")
