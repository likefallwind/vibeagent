from __future__ import annotations

from typing import Any

from .tool_definition_file_directory_lifecycle import FILE_DIRECTORY_LIFECYCLE_TOOL_DEFINITIONS
from .tool_definition_file_directory_transfers import FILE_DIRECTORY_TRANSFER_TOOL_DEFINITIONS
from .tool_definition_file_executable import FILE_EXECUTABLE_TOOL_DEFINITIONS


FILE_DIRECTORY_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    FILE_DIRECTORY_TRANSFER_TOOL_DEFINITIONS
    + FILE_DIRECTORY_LIFECYCLE_TOOL_DEFINITIONS
    + FILE_EXECUTABLE_TOOL_DEFINITIONS
)
