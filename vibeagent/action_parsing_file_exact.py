from __future__ import annotations

from typing import Any

from .action_parsing_file_edit_fields import parse_string_field
from .action_parsing_helpers import parse_edit_operations
from .types import CheckEditFileAction, CheckMultiEditAction, EditFileAction, MultiEditAction


FILE_EXACT_ACTION_TYPES = {
    "check_edit_file",
    "edit_file",
    "check_multi_edit_file",
    "multi_edit_file",
}


def parse_file_exact_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_EXACT_ACTION_TYPES:
        return None

    if action_type == "check_edit_file":
        path = parse_string_field(value.get("path"), raw, "check_edit_file action requires a string path.")
        old = parse_string_field(value.get("old"), raw, "check_edit_file action requires string old.")
        new = parse_string_field(value.get("new"), raw, "check_edit_file action requires string new.")
        return CheckEditFileAction(type="check_edit_file", path=path, old=old, new=new)

    if action_type == "edit_file":
        path = parse_string_field(value.get("path"), raw, "edit_file action requires a string path.")
        old = parse_string_field(value.get("old"), raw, "edit_file action requires string old.")
        new = parse_string_field(value.get("new"), raw, "edit_file action requires string new.")
        return EditFileAction(type="edit_file", path=path, old=old, new=new)

    if action_type == "check_multi_edit_file":
        path = parse_string_field(value.get("path"), raw, "check_multi_edit_file action requires a string path.")
        return CheckMultiEditAction(
            type="check_multi_edit_file",
            path=path,
            edits=parse_edit_operations(value.get("edits"), raw, action_type="check_multi_edit_file"),
        )

    if action_type == "multi_edit_file":
        path = parse_string_field(value.get("path"), raw, "multi_edit_file action requires a string path.")
        return MultiEditAction(type="multi_edit_file", path=path, edits=parse_edit_operations(value.get("edits"), raw))

    raise AssertionError(f"Unhandled file exact action type: {action_type!r}")
