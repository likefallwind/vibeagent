from __future__ import annotations

from .agent_parallel_safety import PARALLEL_SAFE_TOOL_NAMES


DELEGATE_TOOL_NAMES = frozenset(
    name
    for name in PARALLEL_SAFE_TOOL_NAMES
    if not name.startswith("check_") and name not in {"final_review"}
)
READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES = frozenset({"Glob", "Grep", "LS", "NotebookRead", "Read", "TodoRead"})
CODE_DELEGATE_EXCLUDED_TOOL_NAMES = frozenset(
    {
        "EnterWorktree",
        "ExitWorktree",
        "SendMessage",
        "ask_user",
        "enter_worktree",
        "exit_worktree",
        "todo_write",
        "update_plan",
    }
)

NESTED_DELEGATE_TOOL_NAMES = frozenset(
    {"Agent", "ListAgents", "Task", "TaskOutput", "TaskStop", "delegate_task"}
)
