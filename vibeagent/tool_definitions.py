from __future__ import annotations

from typing import Any

from .tool_definition_code_intel import CODE_INTEL_TOOL_DEFINITIONS
from .tool_definition_delegation import DELEGATION_TOOL_DEFINITIONS
from .tool_definition_file_editing import FILE_EDITING_TOOL_DEFINITIONS
from .tool_definition_git import GIT_TOOL_DEFINITIONS
from .tool_definition_json_editing import JSON_EDITING_TOOL_DEFINITIONS
from .tool_definition_process_control import PROCESS_CONTROL_TOOL_DEFINITIONS
from .tool_definition_project_runtime import PROJECT_RUNTIME_TOOL_DEFINITIONS
from .tool_definition_reading import READING_TOOL_DEFINITIONS
from .tool_definition_sessions import SESSION_TOOL_DEFINITIONS


AGENT_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    READING_TOOL_DEFINITIONS
    + JSON_EDITING_TOOL_DEFINITIONS
    + CODE_INTEL_TOOL_DEFINITIONS
    + GIT_TOOL_DEFINITIONS
    + PROJECT_RUNTIME_TOOL_DEFINITIONS
    + DELEGATION_TOOL_DEFINITIONS
    + SESSION_TOOL_DEFINITIONS
    + FILE_EDITING_TOOL_DEFINITIONS
    + PROCESS_CONTROL_TOOL_DEFINITIONS
)
