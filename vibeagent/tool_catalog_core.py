from __future__ import annotations

from .action_tool_aliases import profile_tool_names
from .tool_categories import TOOL_CATEGORIES
from .tool_definitions import AGENT_TOOL_DEFINITIONS


APPROVAL_REQUIRED_TOOL_NAMES = {
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
    "git_commit",
    "git_fetch",
    "git_pull",
    "git_push",
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
    "stop_all_processes",
    "stop_process",
    "write_file",
    "write_files",
    "write_process",
    "web_fetch",
    "mcp_tools",
    "mcp_call",
}


def categorize_tools() -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {category: [] for category in TOOL_CATEGORIES}
    for tool in AGENT_TOOL_DEFINITIONS:
        name = str(tool["name"])
        categories[tool_category(name)].append(name)
    return categories


def tool_category(name: str) -> str:
    if name in {"delegate_task", "mcp_call", "mcp_servers", "mcp_tools", "web_fetch"}:
        return "project"
    if name in {"Agent", "Task", "WebFetch"}:
        return "project"
    if name in {
        "AskUserQuestion",
        "ask_user",
        "ExitPlanMode",
        "todo_read",
        "TodoRead",
        "todo_write",
        "TodoWrite",
        "update_plan",
        "finish",
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
    if name.startswith("checkpoint_") or name.startswith("check_checkpoint_"):
        return "checkpoint"
    if name.startswith("git_") or name.startswith("check_git_"):
        return "git"
    if name in {
        "Bash",
        "BashOutput",
        "KillBash",
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
        "final_review",
    }:
        return "project"
    edit_keywords = (
        "Edit",
        "MultiEdit",
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
