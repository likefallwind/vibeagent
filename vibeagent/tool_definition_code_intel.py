from __future__ import annotations

from typing import Any

from .tool_definition_code_dependencies import CODE_DEPENDENCY_TOOL_DEFINITIONS
from .tool_definition_generic_code import GENERIC_CODE_TOOL_DEFINITIONS
from .tool_definition_lsp import LSP_TOOL_DEFINITIONS
from .tool_definition_python_code import PYTHON_CODE_TOOL_DEFINITIONS
from .tool_definition_search import SEARCH_TOOL_DEFINITIONS


CODE_INTEL_TOOL_DEFINITIONS: list[dict[str, Any]] = (
    CODE_DEPENDENCY_TOOL_DEFINITIONS
    + LSP_TOOL_DEFINITIONS
    + GENERIC_CODE_TOOL_DEFINITIONS
    + PYTHON_CODE_TOOL_DEFINITIONS
    + SEARCH_TOOL_DEFINITIONS
)
