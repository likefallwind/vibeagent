from __future__ import annotations

from .agent_parallel_safety import PARALLEL_SAFE_TOOL_NAMES


DELEGATE_TOOL_NAMES = frozenset(
    name
    for name in PARALLEL_SAFE_TOOL_NAMES
    if not name.startswith("check_") and name not in {"final_review"}
)
CODE_DELEGATE_EXCLUDED_TOOL_NAMES = frozenset({"ask_user", "delegate_task", "todo_write", "update_plan"})
