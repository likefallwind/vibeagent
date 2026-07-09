from __future__ import annotations

from typing import Any

from .tool_definition_session_readiness import SESSION_READINESS_TOOL_DEFINITIONS
from .tool_definition_session_verification_checks import SESSION_VERIFICATION_CHECK_TOOL_DEFINITIONS


SESSION_VERIFICATION_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    SESSION_VERIFICATION_CHECK_TOOL_DEFINITIONS
    + SESSION_READINESS_TOOL_DEFINITIONS
)
