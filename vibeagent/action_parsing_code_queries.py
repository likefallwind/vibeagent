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
    CodeDefinitionsAction,
    CodeDependenciesAction,
    CodeReferenceContextsAction,
    CodeReferencesAction,
)


CODE_QUERY_ACTION_TYPES = {
    "code_dependencies",
    "code_references",
    "code_reference_contexts",
    "code_definitions",
}


def parse_code_query_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type == "code_dependencies":
        path = parse_optional_path(value.get("path"), raw, "code_dependencies")
        max_files, max_imports = parse_dependency_limits(value, raw)
        return CodeDependenciesAction(
            type="code_dependencies",
            path=path,
            max_files=max_files,
            max_imports=max_imports,
        )

    if action_type == "code_references":
        symbol = parse_required_symbol(value.get("symbol"), raw, "code_references")
        path = parse_optional_path(value.get("path"), raw, "code_references")
        max_matches = parse_optional_positive_int(value.get("max_matches", 200), "max_matches", raw, maximum=500) or 200
        return CodeReferencesAction(
            type="code_references",
            symbol=symbol,
            path=path,
            max_matches=max_matches,
        )

    if action_type == "code_reference_contexts":
        symbol = parse_required_symbol(value.get("symbol"), raw, "code_reference_contexts")
        path = parse_optional_path(value.get("path"), raw, "code_reference_contexts")
        max_matches, context_lines, max_bytes_per_context = parse_reference_context_limits(value, raw)
        return CodeReferenceContextsAction(
            type="code_reference_contexts",
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "code_definitions":
        symbol = parse_required_symbol(value.get("symbol"), raw, "code_definitions")
        path = parse_optional_path(value.get("path"), raw, "code_definitions")
        max_matches = parse_optional_positive_int(value.get("max_matches", 50), "max_matches", raw, maximum=200) or 50
        max_lines = parse_optional_positive_int(value.get("max_lines", 80), "max_lines", raw, maximum=500) or 80
        return CodeDefinitionsAction(
            type="code_definitions",
            symbol=symbol,
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )

    return None
