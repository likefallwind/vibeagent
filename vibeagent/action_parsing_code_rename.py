from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_code_rename_input, parse_optional_positive_int
from .types import (
    CheckReplacePythonDefinitionAction,
    CodeRenameAction,
    CodeRenamePreviewAction,
    PythonRenameAction,
    PythonRenamePreviewAction,
    ReplacePythonDefinitionAction,
)


def parse_code_rename_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
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

    return None


def parse_replace_python_definition_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in {"check_replace_python_definition", "replace_python_definition"}:
        return None

    symbol = value.get("symbol")
    content = value.get("content")
    path = value.get("path")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty symbol.", raw)
    if not isinstance(content, str) or not content.strip():
        raise ActionParseError(f"{action_type} action requires non-empty string content.", raw)
    if path is not None and not isinstance(path, str):
        raise ActionParseError(f"{action_type} action path must be a string when provided.", raw)

    if action_type == "check_replace_python_definition":
        return CheckReplacePythonDefinitionAction(
            type="check_replace_python_definition",
            symbol=symbol.strip(),
            content=content,
            path=path,
        )
    return ReplacePythonDefinitionAction(
        type="replace_python_definition",
        symbol=symbol.strip(),
        content=content,
        path=path,
    )


def parse_python_rename_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in {"python_rename_preview", "python_rename"}:
        return None

    symbol = value.get("symbol")
    new_name = value.get("new_name")
    path = value.get("path")
    max_files = value.get("max_files", 100)
    default_max_replacements = 500 if action_type == "python_rename_preview" else 2000
    max_replacements = value.get("max_replacements", default_max_replacements)
    if not isinstance(symbol, str) or not symbol.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty symbol.", raw)
    if not isinstance(new_name, str) or not new_name.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty new_name.", raw)
    if path is not None and not isinstance(path, str):
        raise ActionParseError(f"{action_type} action path must be a string when provided.", raw)
    max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
    max_replacements = (
        parse_optional_positive_int(max_replacements, "max_replacements", raw, maximum=2000)
        or default_max_replacements
    )

    if action_type == "python_rename_preview":
        return PythonRenamePreviewAction(
            type="python_rename_preview",
            symbol=symbol.strip(),
            new_name=new_name.strip(),
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )
    return PythonRenameAction(
        type="python_rename",
        symbol=symbol.strip(),
        new_name=new_name.strip(),
        path=path,
        max_files=max_files,
        max_replacements=max_replacements,
    )
