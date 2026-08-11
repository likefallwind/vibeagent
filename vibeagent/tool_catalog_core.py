from __future__ import annotations

from .action_tool_aliases import profile_tool_names
from .tool_categories import TOOL_CATEGORIES
from .tool_definitions import AGENT_TOOL_DEFINITIONS


APPROVAL_REQUIRED_TOOL_NAMES = {
    "ExitPlanMode",
    "browser_act",
    "browser_close",
    "browser_open",
    "browser_read",
    "browser_screenshot",
    "browser_snapshot",
    "append_file",
    "checkpoint_delete",
    "checkpoint_prune",
    "checkpoint_restore",
    "code_rename",
    "copy_dir",
    "copy_dirs",
    "copy_file",
    "copy_files",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "delete_file",
    "delete_files",
    "edit_file",
    "enter_worktree",
    "notebook_edit",
    "git_commit",
    "git_fetch",
    "git_pull",
    "git_push",
    "github_issue_context",
    "github_issue_comment",
    "github_pr_create",
    "github_pr_context",
    "github_pr_ci_logs",
    "github_pr_comment",
    "git_restore",
    "git_stage",
    "git_stash",
    "git_stash_apply",
    "git_stash_drop",
    "git_switch",
    "git_unstage",
    "insert_lines",
    "json_patch",
    "json_remove",
    "json_set",
    "move_dir",
    "move_dirs",
    "move_file",
    "move_files",
    "multi_edit_file",
    "patch_file",
    "patch_files",
    "PowerShell",
    "powershell",
    "python_rename",
    "regex_replace",
    "replace_lines",
    "replace_python_definition",
    "run_command",
    "run_commands",
    "run_focused_test_commands",
    "run_session_verification",
    "run_suggested_checks",
    "set_executable",
    "start_command",
    "monitor",
    "stop_all_processes",
    "stop_process",
    "write_file",
    "write_files",
    "write_process",
    "web_fetch",
    "web_search",
    "mcp_tools",
    "mcp_call",
    "mcp_resources",
    "mcp_read_resource",
    "memory_write",
}


def categorize_tools() -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {category: [] for category in TOOL_CATEGORIES}
    for tool in AGENT_TOOL_DEFINITIONS:
        name = str(tool["name"])
        categories[tool_category(name)].append(name)
    return categories


def tool_category(name: str) -> str:
    if name.startswith("mcp__"):
        return "project"
    if name in {
        "browser_act",
        "browser_close",
        "browser_open",
        "browser_read",
        "browser_screenshot",
        "browser_snapshot",
        "delegate_task",
        "mcp_call",
        "mcp_read_resource",
        "mcp_resources",
        "mcp_servers",
        "mcp_tools",
        "web_fetch",
        "web_search",
    }:
        return "project"
    if name in {
        "Agent",
        "ListAgents",
        "ListMcpResourcesTool",
        "Task",
        "TaskOutput",
        "TaskStop",
        "ReadMcpResourceTool",
        "Skill",
        "ToolSearch",
        "WebFetch",
        "WebSearch",
        "LSP",
    }:
        return "project"
    if name in {
        "AskUserQuestion",
        "ask_user",
        "EnterPlanMode",
        "ExitPlanMode",
        "todo_read",
        "TodoRead",
        "todo_write",
        "TodoWrite",
        "update_plan",
        "finish",
        "CronCreate",
        "CronDelete",
        "CronList",
        "TaskCreate",
        "TaskGet",
        "TaskList",
        "TaskUpdate",
        "TeamCreate",
        "TeamDelete",
        "memory_list",
        "memory_read",
        "session_summary",
        "session_plan",
        "session_transcript",
        "session_search",
        "session_commands",
        "session_output_contexts",
        "session_output_diagnostics",
        "session_files",
        "session_failures",
        "session_verification",
        "run_session_verification",
        "session_audit",
        "session_handoff",
    }:
        return "session"
    if name == "memory_write":
        return "edit"
    if name == "check_memory_write":
        return "edit"
    if name.startswith("checkpoint_") or name.startswith("check_checkpoint_"):
        return "checkpoint"
    if name.startswith("git_") or name.startswith("check_git_") or name in {
        "github_issue_context",
        "github_issue_comment",
        "check_github_issue_comment",
        "github_pr_create",
        "check_github_pr_create",
        "github_pr_context",
        "github_pr_ci_logs",
        "github_pr_comment",
        "check_github_pr_comment",
    }:
        return "git"
    if name in {"EnterWorktree", "ExitWorktree"}:
        return "git"
    if name in {
        "Bash",
        "BashOutput",
        "KillBash",
        "Monitor",
        "PowerShell",
        "powershell",
        "command_check",
        "check_run_commands",
        "check_suggested_checks",
        "run_focused_test_commands",
        "check_focused_test_commands",
        "run_commands",
        "run_suggested_checks",
        "run_command",
        "check_start_command",
        "start_command",
        "monitor",
        "list_processes",
        "read_process",
        "process_output_contexts",
        "process_output_diagnostics",
        "wait_process",
        "check_write_process",
        "write_process",
        "check_stop_process",
        "stop_process",
        "check_stop_all_processes",
        "stop_all_processes",
        "port_check",
        "http_check",
        "http_fetch",
    }:
        return "command"
    if name in {
        "Glob",
        "Grep",
        "LS",
        "NotebookRead",
        "notebook_read",
        "Read",
        "list_files",
        "list_tree",
        "repo_map",
        "read_file",
        "read_file_context",
        "read_file_contexts",
        "output_contexts",
        "output_diagnostics",
        "tail_file",
        "read_files",
        "read_file_ranges",
        "file_info",
        "image_info",
        "view_image",
        "find_files",
        "glob",
        "search",
        "search_contexts",
        "code_reference_contexts",
        "python_reference_contexts",
        "tool_search",
        "project_overview",
        "project_commands",
        "related_tests",
        "focused_test_commands",
        "project_manifests",
        "project_instructions",
        "project_skills",
        "project_agents",
        "skill",
        "project_todos",
        "environment_info",
        "suggest_checks",
        "review_changes",
        "deep_review",
        "final_review",
    }:
        return "project"
    edit_keywords = (
        "Edit",
        "MultiEdit",
        "notebook_edit",
        "NotebookEdit",
        "Write",
        "append",
        "copy",
        "create",
        "delete",
        "edit",
        "insert",
        "json_",
        "move",
        "multi_edit",
        "patch",
        "regex_replace",
        "replace",
        "set_executable",
        "write_file",
        "write_files",
    )
    if name.startswith("check_") and any(keyword in name for keyword in edit_keywords):
        return "edit"
    if name.startswith(("json_", "python_rename", "code_rename")) or any(name.startswith(prefix) for prefix in edit_keywords):
        return "edit"
    if name.startswith(("python_", "code_", "config_check")):
        return "code"
    return "other"


def tool_name_requires_approval(name: str) -> bool:
    if name.startswith("mcp__"):
        return True
    if name in APPROVAL_REQUIRED_TOOL_NAMES:
        return True
    return bool(profile_tool_names(name) & APPROVAL_REQUIRED_TOOL_NAMES)


def tool_requires_approval(name: str, description: str) -> bool:
    if tool_name_requires_approval(name):
        return True
    lowered = description.lower()
    return "requires approval" in lowered or "after approval" in lowered


def suggest_tool_names(name: str, limit: int = 5) -> list[str]:
    if not name:
        return []
    names = [str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS]
    exact_prefix = [tool_name for tool_name in names if tool_name.startswith(name)]
    contains = [tool_name for tool_name in names if name in tool_name and tool_name not in exact_prefix]
    return (exact_prefix + contains)[:limit]
