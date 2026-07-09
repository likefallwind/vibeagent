from __future__ import annotations

from typing import Any

from .tool_definition_command_sequences import COMMAND_SEQUENCE_TOOL_DEFINITIONS
from .tool_definition_environment_runtime import ENVIRONMENT_RUNTIME_TOOL_DEFINITIONS
from .tool_definition_runtime_network import RUNTIME_NETWORK_TOOL_DEFINITIONS


COMMAND_RUNTIME_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    COMMAND_SEQUENCE_TOOL_DEFINITIONS
    + RUNTIME_NETWORK_TOOL_DEFINITIONS
    + ENVIRONMENT_RUNTIME_TOOL_DEFINITIONS
)
