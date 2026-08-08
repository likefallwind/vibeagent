from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .action_parsing_code_queries import CODE_QUERY_ACTION_TYPES, parse_code_query_action
from .action_parsing_code_rename import (
    parse_code_rename_action,
    parse_python_rename_action,
    parse_replace_python_definition_action,
)
from .action_parsing_python_queries import PYTHON_QUERY_ACTION_TYPES, parse_python_query_action
from .types import LspQueryAction


CODE_INTEL_ACTION_TYPES = CODE_QUERY_ACTION_TYPES | PYTHON_QUERY_ACTION_TYPES | {
    "code_rename_preview",
    "code_rename",
    "check_replace_python_definition",
    "replace_python_definition",
    "python_rename_preview",
    "python_rename",
    "lsp_query",
}

LSP_OPERATIONS = {
    "goToDefinition",
    "goToImplementation",
    "findReferences",
    "hover",
    "documentSymbol",
    "workspaceSymbol",
}


def parse_code_intel_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in CODE_INTEL_ACTION_TYPES:
        return None

    if action_type == "lsp_query":
        operation = value.get("operation")
        if operation not in LSP_OPERATIONS:
            raise ActionParseError(f"LSP operation must be one of {sorted(LSP_OPERATIONS)}.", raw)
        path = value.get("path")
        if path is not None and (not isinstance(path, str) or not path.strip()):
            raise ActionParseError("LSP path must be a non-empty string.", raw)
        line = value.get("line")
        character = value.get("character")
        if line is not None and (not isinstance(line, int) or isinstance(line, bool) or line < 0):
            raise ActionParseError("LSP line must be a non-negative integer.", raw)
        if character is not None and (not isinstance(character, int) or isinstance(character, bool) or character < 0):
            raise ActionParseError("LSP character must be a non-negative integer.", raw)
        symbol = value.get("symbol")
        if symbol is not None and (not isinstance(symbol, str) or not symbol.strip()):
            raise ActionParseError("LSP symbol must be a non-empty string.", raw)
        if operation == "documentSymbol" and path is None:
            raise ActionParseError("LSP documentSymbol requires path.", raw)
        if operation != "documentSymbol" and symbol is None and (path is None or line is None or character is None):
            raise ActionParseError("LSP query requires symbol or path, line, and character.", raw)
        maximum = parse_optional_positive_int(value.get("max_results", 50), "max_results", raw, maximum=200) or 50
        return LspQueryAction(
            type="lsp_query",
            operation=operation,
            path=path.strip() if isinstance(path, str) else None,
            line=line,
            character=character,
            symbol=symbol.strip() if isinstance(symbol, str) else None,
            max_results=maximum,
        )

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

    python_query_action = parse_python_query_action(action_type, value, raw)
    if python_query_action is not None:
        return python_query_action

    raise AssertionError(f"Unhandled code intelligence action type: {action_type!r}")
