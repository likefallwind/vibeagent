from __future__ import annotations

from . import types as t
from .agent_action_targets import build_action_target


def log_action(logger: t.AgentLogger | None, action: object) -> None:
    if not logger:
        return
    action_type = getattr(action, "type", None)
    if action_type == "list_files":
        logger("listing files", getattr(action, "path", None) or ".")
    elif action_type == "list_tree":
        logger("listing tree", getattr(action, "path", None) or ".")
    elif action_type == "repo_map":
        logger("mapping repo", build_action_target(action))
    elif action_type == "read_file":
        logger("reading file", getattr(action, "path"))
    elif action_type == "read_file_context":
        logger("reading file context", build_action_target(action))
    elif action_type == "read_file_contexts":
        logger("reading file contexts", build_action_target(action))
    elif action_type == "output_contexts":
        logger("reading output contexts", build_action_target(action))
    elif action_type == "tail_file":
        logger("tailing file", getattr(action, "path"))
    elif action_type == "read_files":
        logger("reading files", build_action_target(action))
    elif action_type == "read_file_ranges":
        logger("reading file ranges", build_action_target(action))
    elif action_type == "file_info":
        logger("reading file info", build_action_target(action))
    elif action_type == "image_info":
        logger("reading image info", build_action_target(action))
    elif action_type == "python_symbols":
        logger("reading python symbols", build_action_target(action))
    elif action_type == "code_outline":
        logger("reading code outline", build_action_target(action))
    elif action_type == "python_check":
        logger("checking python", build_action_target(action))
    elif action_type == "config_check":
        logger("checking config", build_action_target(action))
    elif action_type == "python_dependencies":
        logger("reading python dependencies", build_action_target(action))
    elif action_type == "code_dependencies":
        logger("reading code dependencies", build_action_target(action))
    elif action_type == "code_references":
        logger("reading code references", build_action_target(action))
    elif action_type == "code_reference_contexts":
        logger("reading code reference contexts", build_action_target(action))
    elif action_type == "code_definitions":
        logger("reading code definitions", build_action_target(action))
    elif action_type == "code_rename_preview":
        logger("previewing code rename", build_action_target(action))
    elif action_type == "code_rename":
        logger("renaming code symbol", build_action_target(action))
    elif action_type == "python_definitions":
        logger("reading python definitions", build_action_target(action))
    elif action_type == "python_calls":
        logger("reading python calls", build_action_target(action))
    elif action_type == "python_call_graph":
        logger("reading python call graph", build_action_target(action))
    elif action_type == "python_references":
        logger("reading python references", build_action_target(action))
    elif action_type == "python_reference_contexts":
        logger("reading python reference contexts", build_action_target(action))
    elif action_type == "python_rename_preview":
        logger("previewing python rename", build_action_target(action))
    elif action_type == "python_rename":
        logger("renaming python symbol", build_action_target(action))
    elif action_type == "search":
        logger("searching", getattr(action, "query"))
    elif action_type == "search_contexts":
        logger("searching contexts", build_action_target(action))
    elif action_type == "find_files":
        logger("finding files", build_action_target(action))
    elif action_type == "glob":
        logger("globbing", getattr(action, "pattern"))
    elif action_type == "git_status":
        logger("checking git status", None)
    elif action_type == "git_conflicts":
        logger("scanning git conflicts", getattr(action, "path", None) or ".")
    elif action_type == "git_diff_contexts":
        logger("reading git diff contexts", getattr(action, "path", None) or ".")
    elif action_type == "git_info":
        logger("reading git info", None)
    elif action_type == "git_changes":
        logger("reading git changes", None)
    elif action_type == "git_branches":
        logger("reading git branches", None)
    elif action_type == "check_git_fetch":
        logger("checking git fetch", build_action_target(action))
    elif action_type == "git_fetch":
        logger("fetching git remote", build_action_target(action))
    elif action_type == "check_git_pull":
        logger("checking git pull", build_action_target(action))
    elif action_type == "git_pull":
        logger("pulling git upstream", build_action_target(action))
    elif action_type == "check_git_push":
        logger("checking git push", build_action_target(action))
    elif action_type == "git_push":
        logger("pushing git upstream", build_action_target(action))
    elif action_type == "check_git_restore":
        logger("checking git restore", build_action_target(action))
    elif action_type == "git_restore":
        logger("restoring git paths", build_action_target(action))
    elif action_type == "git_stashes":
        logger("reading git stashes", build_action_target(action))
    elif action_type == "check_git_stash":
        logger("checking git stash", build_action_target(action))
    elif action_type == "git_stash":
        logger("stashing git changes", build_action_target(action))
    elif action_type == "check_git_stash_apply":
        logger("checking git stash apply", build_action_target(action))
    elif action_type == "git_stash_apply":
        logger("applying git stash", build_action_target(action))
    elif action_type == "check_git_stash_drop":
        logger("checking git stash drop", build_action_target(action))
    elif action_type == "git_stash_drop":
        logger("dropping git stash", build_action_target(action))
    elif action_type == "check_git_switch":
        logger("checking git switch", build_action_target(action))
    elif action_type == "git_switch":
        logger("switching git branch", build_action_target(action))
    elif action_type == "check_git_stage":
        logger("checking git stage", build_action_target(action))
    elif action_type == "git_stage":
        logger("staging git paths", build_action_target(action))
    elif action_type == "check_git_unstage":
        logger("checking git unstage", build_action_target(action))
    elif action_type == "git_unstage":
        logger("unstaging git paths", build_action_target(action))
    elif action_type == "check_git_commit":
        logger("checking git commit", build_action_target(action))
    elif action_type == "git_commit":
        logger("committing staged changes", build_action_target(action))
    elif action_type == "review_changes":
        logger("reviewing changes", None)
    elif action_type == "final_review":
        logger("final reviewing changes", None)
    elif action_type == "suggest_checks":
        logger("suggesting checks", None)
    elif action_type == "check_suggested_checks":
        logger("checking suggested checks", build_action_target(action))
    elif action_type == "run_suggested_checks":
        logger("running suggested checks", build_action_target(action))
    elif action_type == "project_commands":
        logger("reading project commands", None)
    elif action_type == "tool_search":
        logger("searching tool catalog", build_action_target(action))
    elif action_type == "related_tests":
        logger("finding related tests", build_action_target(action))
    elif action_type == "focused_test_commands":
        logger("suggesting focused test commands", build_action_target(action))
    elif action_type == "check_focused_test_commands":
        logger("checking focused test commands", build_action_target(action))
    elif action_type == "run_focused_test_commands":
        logger("running focused test commands", build_action_target(action))
    elif action_type == "project_manifests":
        logger("reading project manifests", None)
    elif action_type == "project_instructions":
        logger("reading project instructions", None)
    elif action_type == "project_skills":
        logger("listing project skills", None)
    elif action_type == "skill":
        logger("loading project skill", build_action_target(action))
    elif action_type == "project_overview":
        logger("reading project overview", None)
    elif action_type == "command_check":
        logger("checking command", build_action_target(action))
    elif action_type == "check_run_commands":
        logger("checking commands", build_action_target(action))
    elif action_type == "environment_info":
        logger("reading environment info", None)
    elif action_type == "git_diff":
        logger("reading git diff", build_action_target(action))
    elif action_type == "git_diff_hunks":
        logger("reading git diff hunks", build_action_target(action))
    elif action_type == "git_log":
        logger("reading git log", build_action_target(action))
    elif action_type == "git_show":
        logger("reading git show", build_action_target(action))
    elif action_type == "git_blame":
        logger("reading git blame", build_action_target(action))
    elif action_type == "session_summary":
        logger("reading session summary", build_action_target(action))
    elif action_type == "session_plan":
        logger("reading session plan", build_action_target(action))
    elif action_type == "session_transcript":
        logger("reading session transcript", build_action_target(action))
    elif action_type == "session_search":
        logger("searching session", build_action_target(action))
    elif action_type == "session_commands":
        logger("reading session commands", build_action_target(action))
    elif action_type == "session_output_contexts":
        logger("reading session output contexts", build_action_target(action))
    elif action_type == "session_output_diagnostics":
        logger("reading session output diagnostics", build_action_target(action))
    elif action_type == "session_files":
        logger("reading session files", build_action_target(action))
    elif action_type == "session_failures":
        logger("reading session failures", build_action_target(action))
    elif action_type == "session_verification":
        logger("reading session verification", build_action_target(action))
    elif action_type == "run_session_verification":
        logger("running session verification", build_action_target(action))
    elif action_type == "session_audit":
        logger("reading session audit", build_action_target(action))
    elif action_type == "session_handoff":
        logger("reading session handoff", build_action_target(action))
    elif action_type == "checkpoint_create":
        logger("creating checkpoint", build_action_target(action))
    elif action_type == "checkpoint_list":
        logger("listing checkpoints", build_action_target(action))
    elif action_type == "checkpoint_show":
        logger("reading checkpoint", build_action_target(action))
    elif action_type == "checkpoint_diff":
        logger("reading checkpoint diff", build_action_target(action))
    elif action_type == "checkpoint_status":
        logger("checking checkpoint status", build_action_target(action))
    elif action_type == "check_checkpoint_restore":
        logger("checking checkpoint restore", build_action_target(action))
    elif action_type == "checkpoint_restore":
        logger("restoring checkpoint", build_action_target(action))
    elif action_type == "check_checkpoint_delete":
        logger("checking checkpoint delete", build_action_target(action))
    elif action_type == "checkpoint_delete":
        logger("deleting checkpoint", build_action_target(action))
    elif action_type == "check_checkpoint_prune":
        logger("checking checkpoint prune", build_action_target(action))
    elif action_type == "checkpoint_prune":
        logger("pruning checkpoints", build_action_target(action))
    elif action_type == "check_edit_file":
        logger("checking file edit", build_action_target(action))
    elif action_type == "edit_file":
        logger("editing file", getattr(action, "path"))
    elif action_type == "check_multi_edit_file":
        logger("checking multi-edit", build_action_target(action))
    elif action_type == "multi_edit_file":
        logger("multi-editing file", getattr(action, "path"))
    elif action_type == "check_replace_python_definition":
        logger("checking python definition replacement", build_action_target(action))
    elif action_type == "replace_python_definition":
        logger("replacing python definition", build_action_target(action))
    elif action_type == "check_replace_lines":
        logger("checking replace lines", build_action_target(action))
    elif action_type == "replace_lines":
        logger("replacing lines", build_action_target(action))
    elif action_type == "check_insert_lines":
        logger("checking insert lines", build_action_target(action))
    elif action_type == "insert_lines":
        logger("inserting lines", build_action_target(action))
    elif action_type == "check_append_file":
        logger("checking append file", build_action_target(action))
    elif action_type == "append_file":
        logger("appending file", build_action_target(action))
    elif action_type == "regex_replace":
        logger("regex replacing", build_action_target(action))
    elif action_type == "check_regex_replace":
        logger("checking regex replace", build_action_target(action))
    elif action_type == "check_json_set":
        logger("checking json set", build_action_target(action))
    elif action_type == "json_set":
        logger("setting json", build_action_target(action))
    elif action_type == "check_json_remove":
        logger("checking json remove", build_action_target(action))
    elif action_type == "json_remove":
        logger("removing json", build_action_target(action))
    elif action_type == "check_json_patch":
        logger("checking json patch", build_action_target(action))
    elif action_type == "json_patch":
        logger("patching json", build_action_target(action))
    elif action_type == "check_patch":
        logger("checking patch", getattr(action, "path"))
    elif action_type == "check_patches":
        logger("checking patches", "multiple files")
    elif action_type == "patch_file":
        logger("patching file", getattr(action, "path"))
    elif action_type == "patch_files":
        logger("patching files", "multiple files")
    elif action_type == "check_delete_file":
        logger("checking delete file", build_action_target(action))
    elif action_type == "delete_file":
        logger("deleting file", getattr(action, "path"))
    elif action_type == "check_delete_files":
        logger("checking file deletes", build_action_target(action))
    elif action_type == "delete_files":
        logger("deleting files", build_action_target(action))
    elif action_type == "check_move_file":
        logger("checking move file", build_action_target(action))
    elif action_type == "move_file":
        logger("moving file", build_action_target(action))
    elif action_type == "check_move_files":
        logger("checking file moves", build_action_target(action))
    elif action_type == "move_files":
        logger("moving files", build_action_target(action))
    elif action_type == "check_copy_file":
        logger("checking copy file", build_action_target(action))
    elif action_type == "copy_file":
        logger("copying file", build_action_target(action))
    elif action_type == "check_copy_files":
        logger("checking file copies", build_action_target(action))
    elif action_type == "copy_files":
        logger("copying files", build_action_target(action))
    elif action_type == "check_move_dir":
        logger("checking move directory", build_action_target(action))
    elif action_type == "move_dir":
        logger("moving directory", build_action_target(action))
    elif action_type == "check_move_dirs":
        logger("checking directory moves", build_action_target(action))
    elif action_type == "move_dirs":
        logger("moving directories", build_action_target(action))
    elif action_type == "check_copy_dir":
        logger("checking copy directory", build_action_target(action))
    elif action_type == "copy_dir":
        logger("copying directory", build_action_target(action))
    elif action_type == "check_copy_dirs":
        logger("checking directory copies", build_action_target(action))
    elif action_type == "copy_dirs":
        logger("copying directories", build_action_target(action))
    elif action_type == "check_create_dir":
        logger("checking create directory", build_action_target(action))
    elif action_type == "create_dir":
        logger("creating directory", build_action_target(action))
    elif action_type == "check_create_dirs":
        logger("checking directory creates", build_action_target(action))
    elif action_type == "create_dirs":
        logger("creating directories", build_action_target(action))
    elif action_type == "check_delete_empty_dir":
        logger("checking delete empty directory", build_action_target(action))
    elif action_type == "delete_empty_dir":
        logger("deleting empty directory", build_action_target(action))
    elif action_type == "check_delete_empty_dirs":
        logger("checking empty directory deletes", build_action_target(action))
    elif action_type == "delete_empty_dirs":
        logger("deleting empty directories", build_action_target(action))
    elif action_type == "check_set_executable":
        logger("checking executable bit", build_action_target(action))
    elif action_type == "set_executable":
        logger("setting executable bit", build_action_target(action))
    elif action_type == "check_write_file":
        logger("checking file write", build_action_target(action))
    elif action_type == "write_file":
        logger("writing file", getattr(action, "path"))
    elif action_type == "check_write_files":
        logger("checking file writes", build_action_target(action))
    elif action_type == "write_files":
        logger("writing files", build_action_target(action))
    elif action_type == "run_command":
        logger("running command", build_action_target(action))
    elif action_type == "run_commands":
        logger("running commands", build_action_target(action))
    elif action_type == "check_start_command":
        logger("checking start command", build_action_target(action))
    elif action_type == "port_check":
        logger("checking port", build_action_target(action))
    elif action_type == "http_check":
        logger("checking http", build_action_target(action))
    elif action_type == "http_fetch":
        logger("fetching http", build_action_target(action))
    elif action_type == "web_fetch":
        logger("fetching public document", build_action_target(action))
    elif action_type == "start_command":
        logger("starting command", build_action_target(action))
    elif action_type == "read_process":
        logger("reading process", getattr(action, "process_id"))
    elif action_type == "wait_process":
        logger("waiting process", getattr(action, "process_id"))
    elif action_type == "check_write_process":
        logger("checking process write", build_action_target(action))
    elif action_type == "write_process":
        logger("writing process", build_action_target(action))
    elif action_type == "list_processes":
        logger("listing processes", None)
    elif action_type == "check_stop_all_processes":
        logger("checking stop all processes", None)
    elif action_type == "check_stop_process":
        logger("checking stop process", getattr(action, "process_id"))
    elif action_type == "stop_all_processes":
        logger("stopping all processes", None)
    elif action_type == "stop_process":
        logger("stopping process", getattr(action, "process_id"))
    elif action_type == "update_plan":
        logger("updating plan", build_action_target(action))
    elif action_type == "ask_user":
        logger("asking user", build_action_target(action))
    elif action_type == "delegate_task":
        logger("delegating task", build_action_target(action))
