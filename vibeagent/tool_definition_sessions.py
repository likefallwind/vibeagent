from __future__ import annotations

from typing import Any

from .tool_definition_checkpoints import CHECKPOINT_TOOL_DEFINITIONS
from .tool_definition_session_reports import SESSION_REPORT_TOOL_DEFINITIONS
from .tool_definition_session_verification import SESSION_VERIFICATION_TOOL_DEFINITIONS


SESSION_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    SESSION_REPORT_TOOL_DEFINITIONS
    + SESSION_VERIFICATION_TOOL_DEFINITIONS
    + CHECKPOINT_TOOL_DEFINITIONS
)
