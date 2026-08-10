from __future__ import annotations


CORE_SESSION_TOOL_NAMES = frozenset(
    {
        "ask_user",
        "AskUserQuestion",
        "finish",
        "CronCreate",
        "TaskCreate",
        "TaskGet",
        "TaskList",
        "TaskUpdate",
        "memory_read",
        "ExitPlanMode",
    }
)

CORE_READ_TOOL_NAMES = frozenset(
    {
        "file_info",
        "find_files",
        "glob",
        "Glob",
        "Grep",
        "list_files",
        "list_tree",
        "LS",
        "project_instructions",
        "project_overview",
        "read_file",
        "read_file_context",
        "read_files",
        "Read",
        "repo_map",
        "search",
        "search_contexts",
    }
)

CORE_EDIT_TOOL_NAMES = frozenset(
    {
        "check_edit_file",
        "check_patch",
        "check_write_file",
        "edit_file",
        "Edit",
        "MultiEdit",
        "patch_file",
        "write_file",
        "Write",
    }
)

CORE_COMMAND_TOOL_NAMES = frozenset(
    {
        "Bash",
        "BashOutput",
        "command_check",
        "KillBash",
        "run_command",
    }
)

CORE_PROJECT_TOOL_NAMES = frozenset(
    {
        "delegate_task",
        "Agent",
        "EnterWorktree",
        "focused_test_commands",
        "final_review",
        "git_changes",
        "git_diff",
        "git_status",
        "mcp_servers",
        "ListAgents",
        "related_tests",
        "SendMessage",
        "suggest_checks",
        "Task",
        "tool_search",
        "ToolSearch",
        "WebFetch",
        "web_fetch",
        "WebSearch",
    }
)

CORE_AGENT_TOOL_NAMES = (
    CORE_SESSION_TOOL_NAMES
    | CORE_READ_TOOL_NAMES
    | CORE_EDIT_TOOL_NAMES
    | CORE_COMMAND_TOOL_NAMES
    | CORE_PROJECT_TOOL_NAMES
)
