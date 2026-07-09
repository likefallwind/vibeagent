from __future__ import annotations

from typing import Any

from .tool_definition_file_copies import FILE_COPY_TOOL_DEFINITIONS
from .tool_definition_file_deletes import FILE_DELETE_TOOL_DEFINITIONS
from .tool_definition_file_moves import FILE_MOVE_TOOL_DEFINITIONS


FILE_PATH_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    FILE_DELETE_TOOL_DEFINITIONS
    + FILE_MOVE_TOOL_DEFINITIONS
    + FILE_COPY_TOOL_DEFINITIONS
)
