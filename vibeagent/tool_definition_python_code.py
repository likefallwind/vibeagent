from __future__ import annotations

from typing import Any

from .tool_definition_python_calls import PYTHON_CALL_TOOL_DEFINITIONS
from .tool_definition_python_definitions import PYTHON_DEFINITION_TOOL_DEFINITIONS
from .tool_definition_python_references import PYTHON_REFERENCE_TOOL_DEFINITIONS
from .tool_definition_python_rename import PYTHON_RENAME_TOOL_DEFINITIONS


PYTHON_CODE_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    PYTHON_DEFINITION_TOOL_DEFINITIONS
    + PYTHON_CALL_TOOL_DEFINITIONS
    + PYTHON_REFERENCE_TOOL_DEFINITIONS
    + PYTHON_RENAME_TOOL_DEFINITIONS
)
