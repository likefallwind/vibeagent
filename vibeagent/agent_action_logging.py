from __future__ import annotations

from collections.abc import Callable

from . import types as t
from .agent_action_targets import build_action_target


ActionTargetBuilder = Callable[[object], object]


def _target_none(_action: object) -> None:
    return None


def _target_action(action: object) -> object:
    return build_action_target(action)


def _target_path(action: object) -> object:
    return getattr(action, "path")


def _target_optional_path(action: object) -> object:
    return getattr(action, "path", None) or "."


def _target_query(action: object) -> object:
    return getattr(action, "query")


def _target_pattern(action: object) -> object:
    return getattr(action, "pattern")


def _target_multiple_files(_action: object) -> str:
    return "multiple files"


def _target_process_id(action: object) -> object:
    return getattr(action, "process_id")


ACTION_LOG_SPECS: dict[str, tuple[str, ActionTargetBuilder]] = {
    "memory_list": ("listing memory", _target_none),
    "memory_read": ("reading memory", _target_action),
    "check_memory_write": ("checking memory write", _target_action),
    "memory_write": ("writing memory", _target_action),
    "task_create": ("creating task", _target_action),
    "task_get": ("reading task", _target_action),
    "task_list": ("listing tasks", _target_none),
    "task_update": ("updating task", _target_action),
    "enter_worktree": ("entering worktree", _target_action),
    "exit_worktree": ("exiting worktree", _target_action),
    "list_files": ("listing files", _target_optional_path),
    "list_tree": ("listing tree", _target_optional_path),
    "repo_map": ("mapping repo", _target_action),
    "read_file": ("reading file", _target_path),
    "read_file_context": ("reading file context", _target_action),
    "read_file_contexts": ("reading file contexts", _target_action),
    "output_contexts": ("reading output contexts", _target_action),
    "tail_file": ("tailing file", _target_path),
    "read_files": ("reading files", _target_action),
    "read_file_ranges": ("reading file ranges", _target_action),
    "file_info": ("reading file info", _target_action),
    "image_info": ("reading image info", _target_action),
    "view_image": ("viewing image", _target_action),
    "python_symbols": ("reading python symbols", _target_action),
    "code_outline": ("reading code outline", _target_action),
    "python_check": ("checking python", _target_action),
    "config_check": ("checking config", _target_action),
    "python_dependencies": ("reading python dependencies", _target_action),
    "code_dependencies": ("reading code dependencies", _target_action),
    "code_references": ("reading code references", _target_action),
    "code_reference_contexts": ("reading code reference contexts", _target_action),
    "code_definitions": ("reading code definitions", _target_action),
    "code_rename_preview": ("previewing code rename", _target_action),
    "code_rename": ("renaming code symbol", _target_action),
    "python_definitions": ("reading python definitions", _target_action),
    "python_calls": ("reading python calls", _target_action),
    "python_call_graph": ("reading python call graph", _target_action),
    "python_references": ("reading python references", _target_action),
    "python_reference_contexts": ("reading python reference contexts", _target_action),
    "python_rename_preview": ("previewing python rename", _target_action),
    "python_rename": ("renaming python symbol", _target_action),
    "search": ("searching", _target_query),
    "search_contexts": ("searching contexts", _target_action),
    "find_files": ("finding files", _target_action),
    "glob": ("globbing", _target_pattern),
    "git_status": ("checking git status", _target_none),
    "git_conflicts": ("scanning git conflicts", _target_optional_path),
    "git_diff_contexts": ("reading git diff contexts", _target_optional_path),
    "git_info": ("reading git info", _target_none),
    "git_changes": ("reading git changes", _target_none),
    "git_branches": ("reading git branches", _target_none),
    "check_git_fetch": ("checking git fetch", _target_action),
    "git_fetch": ("fetching git remote", _target_action),
    "check_git_pull": ("checking git pull", _target_action),
    "git_pull": ("pulling git upstream", _target_action),
    "check_git_push": ("checking git push", _target_action),
    "git_push": ("pushing git upstream", _target_action),
    "check_github_pr_create": ("checking GitHub pull request", _target_action),
    "github_pr_create": ("creating GitHub pull request", _target_action),
    "github_pr_context": ("reading GitHub pull request", _target_action),
    "github_pr_ci_logs": ("reading GitHub CI failures", _target_action),
    "check_git_restore": ("checking git restore", _target_action),
    "git_restore": ("restoring git paths", _target_action),
    "git_stashes": ("reading git stashes", _target_action),
    "check_git_stash": ("checking git stash", _target_action),
    "git_stash": ("stashing git changes", _target_action),
    "check_git_stash_apply": ("checking git stash apply", _target_action),
    "git_stash_apply": ("applying git stash", _target_action),
    "check_git_stash_drop": ("checking git stash drop", _target_action),
    "git_stash_drop": ("dropping git stash", _target_action),
    "check_git_switch": ("checking git switch", _target_action),
    "git_switch": ("switching git branch", _target_action),
    "check_git_stage": ("checking git stage", _target_action),
    "git_stage": ("staging git paths", _target_action),
    "check_git_unstage": ("checking git unstage", _target_action),
    "git_unstage": ("unstaging git paths", _target_action),
    "check_git_commit": ("checking git commit", _target_action),
    "git_commit": ("committing staged changes", _target_action),
    "review_changes": ("reviewing changes", _target_none),
    "final_review": ("final reviewing changes", _target_none),
    "suggest_checks": ("suggesting checks", _target_none),
    "check_suggested_checks": ("checking suggested checks", _target_action),
    "run_suggested_checks": ("running suggested checks", _target_action),
    "project_commands": ("reading project commands", _target_none),
    "tool_search": ("searching tool catalog", _target_action),
    "related_tests": ("finding related tests", _target_action),
    "focused_test_commands": ("suggesting focused test commands", _target_action),
    "check_focused_test_commands": ("checking focused test commands", _target_action),
    "run_focused_test_commands": ("running focused test commands", _target_action),
    "project_manifests": ("reading project manifests", _target_none),
    "project_instructions": ("reading project instructions", _target_none),
    "project_skills": ("listing project skills", _target_none),
    "project_agents": ("listing project agent profiles", _target_none),
    "skill": ("loading project skill", _target_action),
    "mcp_servers": ("listing MCP servers", _target_none),
    "mcp_tools": ("listing MCP tools", _target_action),
    "mcp_resources": ("listing MCP resources", _target_action),
    "mcp_read_resource": ("reading MCP resource", _target_action),
    "mcp_call": ("calling MCP tool", _target_action),
    "project_overview": ("reading project overview", _target_none),
    "command_check": ("checking command", _target_action),
    "check_run_commands": ("checking commands", _target_action),
    "environment_info": ("reading environment info", _target_none),
    "git_diff": ("reading git diff", _target_action),
    "git_diff_hunks": ("reading git diff hunks", _target_action),
    "git_log": ("reading git log", _target_action),
    "git_show": ("reading git show", _target_action),
    "git_blame": ("reading git blame", _target_action),
    "session_summary": ("reading session summary", _target_action),
    "session_plan": ("reading session plan", _target_action),
    "session_transcript": ("reading session transcript", _target_action),
    "session_search": ("searching session", _target_action),
    "session_commands": ("reading session commands", _target_action),
    "session_output_contexts": ("reading session output contexts", _target_action),
    "session_output_diagnostics": ("reading session output diagnostics", _target_action),
    "session_files": ("reading session files", _target_action),
    "session_failures": ("reading session failures", _target_action),
    "session_verification": ("reading session verification", _target_action),
    "run_session_verification": ("running session verification", _target_action),
    "session_audit": ("reading session audit", _target_action),
    "session_handoff": ("reading session handoff", _target_action),
    "checkpoint_create": ("creating checkpoint", _target_action),
    "checkpoint_list": ("listing checkpoints", _target_action),
    "checkpoint_show": ("reading checkpoint", _target_action),
    "checkpoint_diff": ("reading checkpoint diff", _target_action),
    "checkpoint_status": ("checking checkpoint status", _target_action),
    "check_checkpoint_restore": ("checking checkpoint restore", _target_action),
    "checkpoint_restore": ("restoring checkpoint", _target_action),
    "check_checkpoint_delete": ("checking checkpoint delete", _target_action),
    "checkpoint_delete": ("deleting checkpoint", _target_action),
    "check_checkpoint_prune": ("checking checkpoint prune", _target_action),
    "checkpoint_prune": ("pruning checkpoints", _target_action),
    "check_edit_file": ("checking file edit", _target_action),
    "edit_file": ("editing file", _target_path),
    "check_multi_edit_file": ("checking multi-edit", _target_action),
    "multi_edit_file": ("multi-editing file", _target_path),
    "check_replace_python_definition": ("checking python definition replacement", _target_action),
    "replace_python_definition": ("replacing python definition", _target_action),
    "check_replace_lines": ("checking replace lines", _target_action),
    "replace_lines": ("replacing lines", _target_action),
    "check_insert_lines": ("checking insert lines", _target_action),
    "insert_lines": ("inserting lines", _target_action),
    "check_append_file": ("checking append file", _target_action),
    "append_file": ("appending file", _target_action),
    "regex_replace": ("regex replacing", _target_action),
    "check_regex_replace": ("checking regex replace", _target_action),
    "check_json_set": ("checking json set", _target_action),
    "json_set": ("setting json", _target_action),
    "check_json_remove": ("checking json remove", _target_action),
    "json_remove": ("removing json", _target_action),
    "check_json_patch": ("checking json patch", _target_action),
    "json_patch": ("patching json", _target_action),
    "check_patch": ("checking patch", _target_path),
    "check_patches": ("checking patches", _target_multiple_files),
    "patch_file": ("patching file", _target_path),
    "patch_files": ("patching files", _target_multiple_files),
    "check_delete_file": ("checking delete file", _target_action),
    "delete_file": ("deleting file", _target_path),
    "check_delete_files": ("checking file deletes", _target_action),
    "delete_files": ("deleting files", _target_action),
    "check_move_file": ("checking move file", _target_action),
    "move_file": ("moving file", _target_action),
    "check_move_files": ("checking file moves", _target_action),
    "move_files": ("moving files", _target_action),
    "check_copy_file": ("checking copy file", _target_action),
    "copy_file": ("copying file", _target_action),
    "check_copy_files": ("checking file copies", _target_action),
    "copy_files": ("copying files", _target_action),
    "check_move_dir": ("checking move directory", _target_action),
    "move_dir": ("moving directory", _target_action),
    "check_move_dirs": ("checking directory moves", _target_action),
    "move_dirs": ("moving directories", _target_action),
    "check_copy_dir": ("checking copy directory", _target_action),
    "copy_dir": ("copying directory", _target_action),
    "check_copy_dirs": ("checking directory copies", _target_action),
    "copy_dirs": ("copying directories", _target_action),
    "check_create_dir": ("checking create directory", _target_action),
    "create_dir": ("creating directory", _target_action),
    "check_create_dirs": ("checking directory creates", _target_action),
    "create_dirs": ("creating directories", _target_action),
    "check_delete_empty_dir": ("checking delete empty directory", _target_action),
    "delete_empty_dir": ("deleting empty directory", _target_action),
    "check_delete_empty_dirs": ("checking empty directory deletes", _target_action),
    "delete_empty_dirs": ("deleting empty directories", _target_action),
    "check_set_executable": ("checking executable bit", _target_action),
    "set_executable": ("setting executable bit", _target_action),
    "check_write_file": ("checking file write", _target_action),
    "write_file": ("writing file", _target_path),
    "check_write_files": ("checking file writes", _target_action),
    "write_files": ("writing files", _target_action),
    "run_command": ("running command", _target_action),
    "run_commands": ("running commands", _target_action),
    "check_start_command": ("checking start command", _target_action),
    "port_check": ("checking port", _target_action),
    "http_check": ("checking http", _target_action),
    "http_fetch": ("fetching http", _target_action),
    "web_fetch": ("fetching public document", _target_action),
    "web_search": ("searching public web", _target_action),
    "start_command": ("starting command", _target_action),
    "monitor": ("starting monitor", _target_action),
    "read_process": ("reading process", _target_process_id),
    "wait_process": ("waiting process", _target_process_id),
    "check_write_process": ("checking process write", _target_action),
    "write_process": ("writing process", _target_action),
    "list_processes": ("listing processes", _target_none),
    "check_stop_all_processes": ("checking stop all processes", _target_none),
    "check_stop_process": ("checking stop process", _target_process_id),
    "stop_all_processes": ("stopping all processes", _target_none),
    "stop_process": ("stopping process", _target_process_id),
    "update_plan": ("updating plan", _target_action),
    "ask_user": ("asking user", _target_action),
    "task_output": ("reading background task", _target_action),
    "task_stop": ("stopping background task", _target_action),
    "send_message": ("sending agent message", _target_action),
    "list_agents": ("listing reachable agents", _target_none),
}


def log_action(logger: t.AgentLogger | None, action: object) -> None:
    if not logger:
        return
    action_type = getattr(action, "type", None)
    spec = ACTION_LOG_SPECS.get(str(action_type))
    if spec is not None:
        message, target_builder = spec
        logger(message, target_builder(action))
    elif action_type == "delegate_task":
        logger(f"delegating {getattr(action, 'mode', 'explore')} task", build_action_target(action))
