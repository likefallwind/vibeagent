from __future__ import annotations

from typing import Any

from .action_parsing_code_queries import CODE_QUERY_ACTION_TYPES, parse_code_query_action
from .action_parsing_code_rename import (
    parse_code_rename_action,
    parse_python_rename_action,
    parse_replace_python_definition_action,
)
from .action_parsing_python_queries import PYTHON_QUERY_ACTION_TYPES, parse_python_query_action


CODE_INTEL_ACTION_TYPES = CODE_QUERY_ACTION_TYPES | PYTHON_QUERY_ACTION_TYPES | {
    "code_rename_preview",
    "code_rename",
    "check_replace_python_definition",
    "replace_python_definition",
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

    python_query_action = parse_python_query_action(action_type, value, raw)
    if python_query_action is not None:
        return python_query_action

    raise AssertionError(f"Unhandled code intelligence action type: {action_type!r}")
