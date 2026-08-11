from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


CoreCommandType: TypeAlias = Literal[
    "exit",
    "help",
    "model",
    "config",
    "custom_commands",
    "plugin",
    "mcp",
    "reload_plugins",
    "agents",
    "skills",
    "tools",
    "tool",
    "tool_search",
    "permissions",
    "sandbox",
    "checks",
    "check_suggested_checks",
    "run_suggested_checks",
    "commands",
    "related_tests",
    "focused_test_commands",
    "check_focused_test_commands",
    "run_focused_test_commands",
    "manifests",
    "instructions",
    "hooks",
    "todos",
    "command",
    "chat",
    "btw",
    "code",
    "goal",
    "workflows",
    "list_agents_local",
    "peer_inbox",
]

RuntimeCommandType: TypeAlias = Literal[
    "run",
    "run_sequence",
    "check_run_sequence",
    "check_start",
    "start",
    "port",
    "http",
    "http_fetch",
]

InspectionCommandType: TypeAlias = Literal[
    "overview",
    "repo_map",
    "search",
    "search_contexts",
    "find_files",
    "glob",
    "tree",
    "symbols",
    "file_info",
    "image_info",
    "read",
    "around",
    "around_many",
    "output_contexts",
    "output_diagnostics",
    "python_traceback",
    "tail",
    "read_files",
    "read_ranges",
]

PythonCommandType: TypeAlias = Literal[
    "python_check",
    "python_deps",
    "python_defs",
    "python_refs",
    "python_ref_contexts",
    "python_calls",
    "python_call_graph",
    "python_rename_preview",
    "python_rename",
    "check_replace_python_definition",
    "replace_python_definition",
]

JsonCommandType: TypeAlias = Literal[
    "config_check",
    "check_json_set",
    "json_set",
    "check_json_remove",
    "json_remove",
    "check_json_patch",
    "json_patch",
]

FileEditCommandType: TypeAlias = Literal[
    "check_replace_lines",
    "replace_lines",
    "check_insert_lines",
    "insert_lines",
    "check_append_file",
    "append_file",
    "check_write_file",
    "write_file",
    "check_write_files",
    "write_files",
    "check_edit_file",
    "edit_file",
    "check_multi_edit_file",
    "multi_edit_file",
    "check_delete_file",
    "delete_file",
    "check_delete_files",
    "delete_files",
    "check_move_file",
    "move_file",
    "check_move_files",
    "move_files",
    "check_copy_file",
    "copy_file",
    "check_copy_files",
    "copy_files",
    "check_move_dir",
    "move_dir",
    "check_move_dirs",
    "move_dirs",
    "check_copy_dir",
    "copy_dir",
    "check_copy_dirs",
    "copy_dirs",
    "check_create_dir",
    "create_dir",
    "check_create_dirs",
    "create_dirs",
    "check_delete_empty_dir",
    "delete_empty_dir",
    "check_delete_empty_dirs",
    "delete_empty_dirs",
    "check_set_executable",
    "set_executable",
    "check_patch",
    "patch_file",
    "check_patches",
    "patch_files",
    "check_regex_replace",
    "regex_replace",
]

CodeIntelCommandType: TypeAlias = Literal[
    "code_deps",
    "code_refs",
    "code_ref_contexts",
    "code_defs",
    "code_rename_preview",
    "code_rename",
]

GitCommandType: TypeAlias = Literal[
    "git_status",
    "git_conflicts",
    "git_info",
    "branches",
    "log",
    "show",
    "blame",
    "stashes",
    "check_fetch",
    "fetch",
    "check_pull",
    "pull",
    "check_push",
    "push",
    "check_stash",
    "stash",
    "check_stash_apply",
    "stash_apply",
    "check_stash_drop",
    "stash_drop",
    "check_stage",
    "stage",
    "check_unstage",
    "unstage",
    "check_commit",
    "commit",
    "check_restore",
    "restore",
    "check_switch",
    "switch",
]

ProcessCommandType: TypeAlias = Literal[
    "env",
    "processes",
    "process",
    "process_output_contexts",
    "process_output_diagnostics",
    "wait_process",
    "check_write_process",
    "write_process",
    "check_stop_process",
    "stop_process",
    "check_stop_all_processes",
    "stop_all_processes",
]

ReviewCommandType: TypeAlias = Literal[
    "status",
    "context",
    "init",
    "doctor",
    "review",
    "handoff",
    "changes",
    "diff",
    "diff_hunks",
    "diff_contexts",
    "clear",
    "usage",
    "cost",
    "approval",
    "system_prompt",
    "append_system_prompt",
    "add_dir",
    "branch",
]

SessionCommandType: TypeAlias = Literal[
    "rename",
    "export",
    "sessions",
    "session",
    "last",
    "plan",
    "transcript",
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
    "resume",
    "compact",
]

CheckpointCommandType: TypeAlias = Literal[
    "rewind",
    "checkpoint",
    "checkpoints",
    "checkpoint_show",
    "checkpoint_diff",
    "checkpoint_status",
    "check_checkpoint_restore",
    "checkpoint_restore",
    "check_checkpoint_delete",
    "checkpoint_delete",
    "check_checkpoint_prune",
    "checkpoint_prune",
]

LocalCommandType: TypeAlias = (
    CoreCommandType
    | RuntimeCommandType
    | InspectionCommandType
    | PythonCommandType
    | JsonCommandType
    | FileEditCommandType
    | CodeIntelCommandType
    | GitCommandType
    | ProcessCommandType
    | ReviewCommandType
    | SessionCommandType
    | CheckpointCommandType
)


@dataclass(frozen=True)
class LocalCommand:
    type: LocalCommandType
    argument: str | None = None


def make_local_command(command_type: str, argument: str | None = None) -> LocalCommand:
    return LocalCommand(type=command_type, argument=argument)  # type: ignore[arg-type]
