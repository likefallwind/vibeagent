from __future__ import annotations

from typing import Any

from .action_parsing_file_edit_fields import parse_string_field
from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .types import CheckNotebookEditAction, NotebookEditAction


FILE_NOTEBOOK_ACTION_TYPES = {
    "check_notebook_edit",
    "notebook_edit",
}


def parse_file_notebook_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in FILE_NOTEBOOK_ACTION_TYPES:
        return None

    path = parse_string_field(value.get("path"), raw, f"{action_type} action requires a string path.")
    new_source = parse_string_field(value.get("new_source"), raw, f"{action_type} action requires string new_source.")
    cell_id = value.get("cell_id")
    cell_number = value.get("cell_number")
    cell_type = value.get("cell_type")
    if cell_id is not None and not isinstance(cell_id, str):
        raise ActionParseError(f"{action_type} action cell_id must be a string when provided.", raw)
    parsed_cell_number = parse_optional_positive_int(cell_number, "cell_number", raw, maximum=1_000_000)
    if cell_id is None and parsed_cell_number is None:
        raise ActionParseError(f"{action_type} action requires cell_id or cell_number.", raw)
    if cell_type is not None and not isinstance(cell_type, str):
        raise ActionParseError(f"{action_type} action cell_type must be a string when provided.", raw)
    action_cls = CheckNotebookEditAction if action_type == "check_notebook_edit" else NotebookEditAction
    return action_cls(
        type=action_type,
        path=path,
        new_source=new_source,
        cell_id=cell_id,
        cell_number=parsed_cell_number,
        cell_type=cell_type,
    )
