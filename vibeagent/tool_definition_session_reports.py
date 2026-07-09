from __future__ import annotations

from typing import Any

from .tool_definition_session_activity_reports import SESSION_ACTIVITY_REPORT_TOOL_DEFINITIONS
from .tool_definition_session_output_reports import SESSION_OUTPUT_REPORT_TOOL_DEFINITIONS
from .tool_definition_session_timeline import SESSION_TIMELINE_TOOL_DEFINITIONS


SESSION_REPORT_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    SESSION_TIMELINE_TOOL_DEFINITIONS
    + SESSION_OUTPUT_REPORT_TOOL_DEFINITIONS
    + SESSION_ACTIVITY_REPORT_TOOL_DEFINITIONS
)
