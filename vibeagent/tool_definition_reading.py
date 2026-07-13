from __future__ import annotations

from typing import Any

from .tool_definition_claude_file import CLAUDE_FILE_TOOL_DEFINITIONS
from .tool_definition_reading_batch import READING_BATCH_TOOL_DEFINITIONS
from .tool_definition_reading_context import READING_CONTEXT_TOOL_DEFINITIONS
from .tool_definition_reading_inspection import READING_INSPECTION_TOOL_DEFINITIONS
from .tool_definition_reading_output import READING_OUTPUT_TOOL_DEFINITIONS
from .tool_definition_reading_project import READING_PROJECT_TOOL_DEFINITIONS
from .tool_definition_reading_source import READING_SOURCE_TOOL_DEFINITIONS


READING_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    READING_PROJECT_TOOL_DEFINITIONS
    + READING_CONTEXT_TOOL_DEFINITIONS
    + READING_OUTPUT_TOOL_DEFINITIONS
    + READING_BATCH_TOOL_DEFINITIONS
    + READING_INSPECTION_TOOL_DEFINITIONS
    + READING_SOURCE_TOOL_DEFINITIONS
    + CLAUDE_FILE_TOOL_DEFINITIONS
)
