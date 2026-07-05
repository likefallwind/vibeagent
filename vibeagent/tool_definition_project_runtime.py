from __future__ import annotations

from typing import Any

from .tool_definition_command_runtime import COMMAND_RUNTIME_TOOL_DEFINITIONS
from .tool_definition_git_reading import GIT_READING_TOOL_DEFINITIONS
from .tool_definition_project_context import PROJECT_CONTEXT_TOOL_DEFINITIONS


PROJECT_RUNTIME_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    PROJECT_CONTEXT_TOOL_DEFINITIONS
    + COMMAND_RUNTIME_TOOL_DEFINITIONS
    + GIT_READING_TOOL_DEFINITIONS
)
