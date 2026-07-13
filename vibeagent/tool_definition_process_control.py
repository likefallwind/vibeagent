from __future__ import annotations

from typing import Any

from .tool_definition_claude_process import CLAUDE_PROCESS_TOOL_DEFINITIONS
from .tool_definition_process_io import PROCESS_IO_TOOL_DEFINITIONS
from .tool_definition_process_output import PROCESS_OUTPUT_TOOL_DEFINITIONS
from .tool_definition_process_run import PROCESS_RUN_TOOL_DEFINITIONS
from .tool_definition_process_stop import PROCESS_STOP_TOOL_DEFINITIONS
from .tool_definition_task_control import TASK_CONTROL_TOOL_DEFINITIONS


PROCESS_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    PROCESS_RUN_TOOL_DEFINITIONS
    + PROCESS_OUTPUT_TOOL_DEFINITIONS
    + PROCESS_IO_TOOL_DEFINITIONS
    + PROCESS_STOP_TOOL_DEFINITIONS
    + TASK_CONTROL_TOOL_DEFINITIONS
    + CLAUDE_PROCESS_TOOL_DEFINITIONS
)
