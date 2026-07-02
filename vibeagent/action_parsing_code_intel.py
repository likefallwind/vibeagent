from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_code_rename_input,
    parse_nonnegative_int,
    parse_optional_positive_int,
)
from .types import (
    CheckReplacePythonDefinitionAction,
    CodeDefinitionsAction,
    CodeDependenciesAction,
    CodeReferenceContextsAction,
    CodeReferencesAction,
    CodeRenameAction,
    CodeRenamePreviewAction,
    PythonCallGraphAction,
    PythonCallsAction,
    PythonDefinitionsAction,
    PythonDependenciesAction,
    PythonReferenceContextsAction,
    PythonReferencesAction,
    PythonRenameAction,
    PythonRenamePreviewAction,
    ReplacePythonDefinitionAction,
)


CODE_INTEL_ACTION_TYPES = {
    "python_dependencies",
    "code_dependencies",
    "code_references",
    "code_reference_contexts",
    "code_definitions",
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

    if action_type == "python_dependencies":
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_imports = value.get("max_imports", 500)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_dependencies action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_imports = parse_optional_positive_int(max_imports, "max_imports", raw, maximum=2000) or 500
        return PythonDependenciesAction(
            type="python_dependencies",
            path=path,
            max_files=max_files,
            max_imports=max_imports,
        )

    if action_type == "code_dependencies":
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_imports = value.get("max_imports", 500)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_dependencies action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_imports = parse_optional_positive_int(max_imports, "max_imports", raw, maximum=2000) or 500
        return CodeDependenciesAction(
            type="code_dependencies",
            path=path,
            max_files=max_files,
            max_imports=max_imports,
        )

    if action_type == "code_references":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 200)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("code_references action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_references action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return CodeReferencesAction(
            type="code_references",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
        )

    if action_type == "code_reference_contexts":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        context_lines = value.get("context_lines", 3)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("code_reference_contexts action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_reference_contexts action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=100) or 50
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200_000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return CodeReferenceContextsAction(
            type="code_reference_contexts",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "code_definitions":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        max_lines = value.get("max_lines", 80)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("code_definitions action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_definitions action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=200) or 50
        max_lines = parse_optional_positive_int(max_lines, "max_lines", raw, maximum=500) or 80
        return CodeDefinitionsAction(
            type="code_definitions",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )

    if action_type == "code_rename_preview":
        symbol, new_name, path, max_files, max_replacements = parse_code_rename_input(
            value,
            raw,
            "code_rename_preview",
            default_max_replacements=500,
        )
        return CodeRenamePreviewAction(
            type="code_rename_preview",
            symbol=symbol,
            new_name=new_name,
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )

    if action_type == "code_rename":
        symbol, new_name, path, max_files, max_replacements = parse_code_rename_input(
            value,
            raw,
            "code_rename",
            default_max_replacements=2000,
        )
        return CodeRenameAction(
            type="code_rename",
            symbol=symbol,
            new_name=new_name,
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
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

    if action_type == "check_replace_python_definition":
        symbol = value.get("symbol")
        content = value.get("content")
        path = value.get("path")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("check_replace_python_definition action requires a non-empty symbol.", raw)
        if not isinstance(content, str) or not content.strip():
            raise ActionParseError("check_replace_python_definition action requires non-empty string content.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("check_replace_python_definition action path must be a string when provided.", raw)
        return CheckReplacePythonDefinitionAction(
            type="check_replace_python_definition",
            symbol=symbol.strip(),
            content=content,
            path=path,
        )

    if action_type == "replace_python_definition":
        symbol = value.get("symbol")
        content = value.get("content")
        path = value.get("path")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("replace_python_definition action requires a non-empty symbol.", raw)
        if not isinstance(content, str) or not content.strip():
            raise ActionParseError("replace_python_definition action requires non-empty string content.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("replace_python_definition action path must be a string when provided.", raw)
        return ReplacePythonDefinitionAction(
            type="replace_python_definition",
            symbol=symbol.strip(),
            content=content,
            path=path,
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

    if action_type == "python_rename_preview":
        symbol = value.get("symbol")
        new_name = value.get("new_name")
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_replacements = value.get("max_replacements", 500)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_rename_preview action requires a non-empty symbol.", raw)
        if not isinstance(new_name, str) or not new_name.strip():
            raise ActionParseError("python_rename_preview action requires a non-empty new_name.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_rename_preview action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_replacements = parse_optional_positive_int(max_replacements, "max_replacements", raw, maximum=2000) or 500
        return PythonRenamePreviewAction(
            type="python_rename_preview",
            symbol=symbol.strip(),
            new_name=new_name.strip(),
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )

    if action_type == "python_rename":
        symbol = value.get("symbol")
        new_name = value.get("new_name")
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_replacements = value.get("max_replacements", 2000)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_rename action requires a non-empty symbol.", raw)
        if not isinstance(new_name, str) or not new_name.strip():
            raise ActionParseError("python_rename action requires a non-empty new_name.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_rename action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_replacements = parse_optional_positive_int(max_replacements, "max_replacements", raw, maximum=2000) or 2000
        return PythonRenameAction(
            type="python_rename",
            symbol=symbol.strip(),
            new_name=new_name.strip(),
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )

    raise AssertionError(f"Unhandled code intelligence action type: {action_type!r}")
