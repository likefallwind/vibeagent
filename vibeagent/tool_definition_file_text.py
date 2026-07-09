from __future__ import annotations

from typing import Any

from .tool_definition_file_exact_edit import FILE_EXACT_EDIT_TOOL_DEFINITIONS
from .tool_definition_file_line_edit import FILE_LINE_EDIT_TOOL_DEFINITIONS
from .tool_definition_file_patch_edit import FILE_PATCH_EDIT_TOOL_DEFINITIONS
from .tool_definition_file_write import FILE_WRITE_TOOL_DEFINITIONS


FILE_TEXT_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    FILE_EXACT_EDIT_TOOL_DEFINITIONS
    + FILE_LINE_EDIT_TOOL_DEFINITIONS
    + FILE_PATCH_EDIT_TOOL_DEFINITIONS
    + FILE_WRITE_TOOL_DEFINITIONS
)
