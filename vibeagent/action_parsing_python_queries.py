from __future__ import annotations

from typing import Any

from .action_parsing_code_intel_fields import (
    parse_dependency_limits,
    parse_optional_path,
    parse_reference_context_limits,
    parse_required_symbol,
)
from .action_parsing_helpers import parse_optional_positive_int
from .types import (
    PythonCallGraphAction,
    PythonCallsAction,
    PythonDefinitionsAction,
    PythonDependenciesAction,
    PythonReferenceContextsAction,
    PythonReferencesAction,
)


PYTHON_QUERY_ACTION_TYPES = {
    "python_dependencies",
    "python_definitions",
    "python_calls",
    "python_call_graph",
    "python_references",
    "python_reference_contexts",
}


def parse_python_query_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
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
        symbol = parse_required_symbol(value.get("symbol"), raw, "python_definitions")
        path = parse_optional_path(value.get("path"), raw, "python_definitions")
        max_matches = parse_optional_positive_int(value.get("max_matches", 50), "max_matches", raw, maximum=200) or 50
        max_lines = parse_optional_positive_int(value.get("max_lines", 120), "max_lines", raw, maximum=1000) or 120
        return PythonDefinitionsAction(
            type="python_definitions",
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )

    if action_type == "python_calls":
        symbol = parse_required_symbol(value.get("symbol"), raw, "python_calls")
        path = parse_optional_path(value.get("path"), raw, "python_calls")
        max_matches = parse_optional_positive_int(value.get("max_matches", 200), "max_matches", raw, maximum=500) or 200
        return PythonCallsAction(
            type="python_calls",
            symbol=symbol,
            path=path,
            max_matches=max_matches,
        )

    if action_type == "python_call_graph":
        path = parse_optional_path(value.get("path"), raw, "python_call_graph")
        max_files = parse_optional_positive_int(value.get("max_files", 100), "max_files", raw, maximum=500) or 100
        max_edges = parse_optional_positive_int(value.get("max_edges", 500), "max_edges", raw, maximum=2000) or 500
        return PythonCallGraphAction(
            type="python_call_graph",
            path=path,
            max_files=max_files,
            max_edges=max_edges,
        )

    if action_type == "python_references":
        symbol = parse_required_symbol(value.get("symbol"), raw, "python_references")
        path = parse_optional_path(value.get("path"), raw, "python_references")
        max_matches = parse_optional_positive_int(value.get("max_matches", 200), "max_matches", raw, maximum=500) or 200
        return PythonReferencesAction(type="python_references", symbol=symbol, path=path, max_matches=max_matches)

    if action_type == "python_reference_contexts":
        symbol = parse_required_symbol(value.get("symbol"), raw, "python_reference_contexts")
        path = parse_optional_path(value.get("path"), raw, "python_reference_contexts")
        max_matches, context_lines, max_bytes_per_context = parse_reference_context_limits(value, raw)
        return PythonReferenceContextsAction(
            type="python_reference_contexts",
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    return None
