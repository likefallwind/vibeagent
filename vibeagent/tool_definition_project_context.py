from __future__ import annotations

from typing import Any

from .tool_definition_project_commands import PROJECT_COMMAND_TOOL_DEFINITIONS
from .tool_definition_project_metadata import PROJECT_METADATA_TOOL_DEFINITIONS
from .tool_definition_project_tests import PROJECT_TEST_TOOL_DEFINITIONS
from .tool_definition_project_tools import PROJECT_TOOL_CATALOG_TOOL_DEFINITIONS


PROJECT_CONTEXT_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    PROJECT_COMMAND_TOOL_DEFINITIONS
    + PROJECT_TOOL_CATALOG_TOOL_DEFINITIONS
    + PROJECT_TEST_TOOL_DEFINITIONS
    + PROJECT_METADATA_TOOL_DEFINITIONS
)
