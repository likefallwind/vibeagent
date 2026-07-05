from __future__ import annotations

from typing import Any

from .tool_definition_file_directories import FILE_DIRECTORY_TOOL_DEFINITIONS
from .tool_definition_file_paths import FILE_PATH_TOOL_DEFINITIONS
from .tool_definition_file_text import FILE_TEXT_TOOL_DEFINITIONS


FILE_EDITING_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    FILE_TEXT_TOOL_DEFINITIONS
    + FILE_PATH_TOOL_DEFINITIONS
    + FILE_DIRECTORY_TOOL_DEFINITIONS
)
