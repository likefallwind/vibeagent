from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlparse

from .actions import AGENT_TOOL_DEFINITIONS, build_command_check_observation, execute_action, get_blocked_command_reason
from .command_parsing import LocalCommand, parse_local_command, parse_local_path_args, parse_optional_single_path_argument
from .check_commands import (
    format_check_suggested_checks_report_text,
    format_checks_report_text,
    format_run_suggested_checks_report_text,
    format_structured_command_checks,
    get_check_suggested_checks_report,
    get_check_suggested_checks_text,
    get_checks_report,
    get_checks_text,
    get_run_suggested_checks_report,
    get_run_suggested_checks_text,
    parse_suggested_checks_limit,
    serialize_focused_test_command,
    serialize_suggested_check,
)
from .config_commands import (
    build_config_report_env,
    format_config_report_text,
    format_model_report_text,
    get_config_report,
    get_config_text,
    get_model_report,
    get_model_text,
)
from .help_commands import get_help_text
from .project_context_commands import (
    format_check_focused_test_commands_report_text,
    format_commands_report_text,
    format_focused_test_commands_report_text,
    format_instructions_report_text,
    format_manifest_summary,
    format_manifests_report_text,
    format_project_command,
    format_related_tests_report_text,
    format_run_focused_test_commands_report_text,
    format_todos_report_text,
    get_check_focused_test_commands_report,
    get_check_focused_test_commands_text,
    get_commands_report,
    get_commands_text,
    get_focused_test_commands_report,
    get_focused_test_commands_text,
    get_instructions_report,
    get_instructions_text,
    get_manifests_report,
    get_manifests_text,
    get_related_tests_report,
    get_related_tests_text,
    get_run_focused_test_commands_report,
    get_run_focused_test_commands_text,
    get_todos_report,
    get_todos_text,
    parse_related_tests_argument,
)
from .read_command_parsing import parse_read_request
from .read_commands import format_around_many_report_text, format_around_report_text, format_read_files_report_text, format_read_ranges_report_text, format_read_report_text, format_tail_report_text, get_around_many_report, get_around_many_text, get_around_report, get_around_text, get_read_files_report, get_read_files_text, get_read_ranges_report, get_read_ranges_text, get_read_report, get_read_text, get_tail_report, get_tail_text
from .session import build_cost_report, build_session_audit_report, build_session_commands_report, build_session_failures_report, build_session_files_report, build_session_handoff_report, build_session_plan_report, build_session_resume_context, build_session_search_report, build_session_summary_report, build_session_transcript_report, build_session_verification_report, build_sessions_report, build_usage_report, get_last_session_id, list_sessions, session_dir, summarize_session
from .tool_commands import (
    APPROVAL_REQUIRED_TOOL_NAMES,
    categorize_tools,
    format_permissions_report_text,
    format_tool_property,
    format_tool_report_text,
    format_tools_report_text,
    get_permissions_report,
    get_permissions_text,
    get_tool_report,
    get_tool_text,
    get_tools_report,
    get_tools_text,
    suggest_tool_names,
    tool_category,
    tool_requires_approval,
    wrap_tool_names,
)
from .types import AppendFileAction, CheckAppendFileAction, CheckCopyDirectoriesAction, CheckCopyDirectoryAction, CheckCopyFileAction, CheckCopyFilesAction, CheckCreateDirectoriesAction, CheckCreateDirectoryAction, CheckDeleteEmptyDirectoriesAction, CheckDeleteEmptyDirectoryAction, CheckDeleteFileAction, CheckDeleteFilesAction, CheckEditFileAction, CheckFocusedTestCommandsAction, CheckGitCommitAction, CheckGitFetchAction, CheckGitPullAction, CheckGitPushAction, CheckGitRestoreAction, CheckGitStageAction, CheckGitStashAction, CheckGitStashApplyAction, CheckGitStashDropAction, CheckGitSwitchAction, CheckGitUnstageAction, CheckInsertLinesAction, CheckJsonPatchAction, CheckJsonRemoveAction, CheckJsonSetAction, CheckMoveDirectoriesAction, CheckMoveDirectoryAction, CheckMoveFileAction, CheckMoveFilesAction, CheckMultiEditAction, CheckPatchAction, CheckPatchesAction, CheckRegexReplaceAction, CheckReplaceLinesAction, CheckReplacePythonDefinitionAction, CheckRunCommandsAction, CheckSetExecutableAction, CheckSuggestedChecksAction, CheckWriteFileAction, CheckWriteFilesAction, CodeDefinitionsAction, CodeDependenciesAction, CodeOutlineAction, CodeReferenceContextsAction, CodeReferencesAction, CodeRenameAction, CodeRenamePreviewAction, ConfigCheckAction, CopyDirectoriesAction, CopyDirectoryAction, CopyFileAction, CopyFilesAction, CreateDirectoriesAction, CreateDirectoryAction, DeleteEmptyDirectoriesAction, DeleteEmptyDirectoryAction, DeleteFileAction, DeleteFilesAction, DirectoryTransfer, EditFileAction, EditOperation, EnvironmentInfoAction, FileInfoAction, FinalReviewAction, FindFilesAction, FocusedTestCommandsAction, GitBlameAction, GitBranchesAction, GitCommitAction, GitConflictsAction, GitDiffAction, GitDiffContextsAction, GitDiffHunksAction, GitFetchAction, GitInfoAction, GitLogAction, GitPullAction, GitPushAction, GitRestoreAction, GitShowAction, GitStageAction, GitStashAction, GitStashApplyAction, GitStashDropAction, GitStashesAction, GitStatusAction, GitSwitchAction, GitUnstageAction, GlobAction, HttpCheckAction, HttpFetchAction, ImageInfoAction, InsertLinesAction, JsonPatchAction, JsonPatchOperation, JsonRemoveAction, JsonSetAction, ListProcessesAction, ListTreeAction, MoveDirectoriesAction, MoveDirectoryAction, MoveFileAction, MoveFilesAction, MoveFileTransfer, MultiEditAction, OutputContextsAction, OutputDiagnosticsAction, PatchFileAction, PatchFilesAction, PortCheckAction, ProcessInfo, ProcessOutputContextsAction, ProcessOutputDiagnosticsAction, ProjectCommand, ProjectOverviewAction, PythonCallGraphAction, PythonCallsAction, PythonCheckAction, PythonDefinitionsAction, PythonDependenciesAction, PythonReferenceContextsAction, PythonReferencesAction, PythonRenameAction, PythonRenamePreviewAction, ReadProcessAction, RegexReplaceAction, ReplaceLinesAction, ReplacePythonDefinitionAction, RelatedTestsAction, RepoMapAction, RunCommandAction, RunCommandItem, RunCommandsAction, RunFocusedTestCommandsAction, RunSuggestedChecksAction, SearchAction, SearchContextsAction, SessionOutputContextsAction, SessionOutputDiagnosticsAction, SetExecutableAction, StartCommandAction, StopAllProcessesAction, StopProcessAction, WaitProcessAction, WriteFileAction, WriteFileItem, WriteFilesAction, WriteProcessAction
from .types import CheckCheckpointPruneAction, CheckCheckpointRestoreAction, CheckpointDeleteAction, CheckpointInfo, CheckpointPruneAction, CheckpointRestoreAction, CheckStartCommandAction, CheckStopAllProcessesAction, CheckStopProcessAction, CheckWriteProcessAction
from .types import CheckCheckpointDeleteAction
from .workspace_core import RunWorkspace
from .workspace import list_files, make_run_id, read_git_changes, read_git_diff, read_git_status, read_project_command_hints, read_project_commands, read_project_instruction_sources, read_project_instructions, read_project_manifests, read_project_todos, read_workspace_snapshot, suggest_project_checks


CHECKPOINT_UNTRACKED_SHOW_LIMIT = 50


def _plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    return value


def _field_value(value: object, name: str, default: object = None) -> object:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def is_exit_command(value: str) -> bool:
    # Helper for tests and callers that only care whether input is an exit command.
    command = parse_local_command(value)
    return command is not None and command.type == "exit"


from .local_runtime_commands import (
    empty_command_output_analysis,
    format_check_run_sequence_report_text,
    format_check_start_report_text,
    format_command_check_report_text,
    format_command_output_context_lines,
    format_command_output_diagnostic_lines,
    format_http_fetch_report_text,
    format_http_report_text,
    format_port_report_text,
    format_run_report_text,
    format_run_sequence_report_text,
    format_start_report_text,
    get_check_run_sequence_report,
    get_check_run_sequence_text,
    get_check_start_report,
    get_check_start_text,
    get_command_check_report,
    get_command_check_text,
    get_http_fetch_report,
    get_http_fetch_text,
    get_http_report,
    get_http_text,
    get_port_report,
    get_port_text,
    get_run_report,
    get_run_sequence_report,
    get_run_sequence_text,
    get_run_text,
    get_start_report,
    get_start_text,
    parse_http_fetch_request,
    parse_http_request,
    parse_port_request,
    parse_run_sequence_request,
    serialize_command_check,
    serialize_command_result,
    serialize_http_report,
    validate_run_output_context_options,
)


from .project_commands import (
    file_type_text,
    format_file_info_report_text,
    format_find_files_report_text,
    format_glob_report_text,
    format_image_info_report_text,
    format_output_contexts_report_text,
    format_output_diagnostics_report_text,
    format_overview_report_text,
    format_python_traceback_report_text,
    format_repo_map_symbols,
    format_repo_map_report_text,
    format_search_contexts_report_text,
    format_search_report_text,
    format_serialized_symbol_file,
    format_symbol_file,
    format_symbols_report_text,
    format_tree_report_text,
    get_file_info_report,
    get_file_info_text,
    get_find_files_report,
    get_find_files_text,
    get_glob_report,
    get_glob_text,
    get_image_info_report,
    get_image_info_text,
    get_output_contexts_report,
    get_output_contexts_text,
    get_output_diagnostics_report,
    get_output_diagnostics_text,
    get_overview_report,
    get_overview_text,
    get_python_traceback_report,
    get_python_traceback_text,
    get_repo_map_report,
    get_repo_map_text,
    get_search_contexts_report,
    get_search_contexts_text,
    get_search_report,
    get_search_text,
    get_symbols_report,
    get_symbols_text,
    get_tree_report,
    get_tree_text,
    parse_symbols_paths,
    serialize_file_info_result,
    serialize_image_info_result,
    serialize_output_context_result,
    serialize_output_diagnostic,
    serialize_symbol,
    serialize_symbol_file,
    yes_no_unknown,
)


from .smart_code_commands import (
    get_python_check_report,
    format_python_check_report_text,
    get_python_deps_report,
    format_python_deps_report_text,
    get_python_defs_report,
    format_python_defs_report_text,
    get_python_refs_report,
    format_python_refs_report_text,
    get_python_ref_contexts_report,
    format_python_ref_contexts_report_text,
    get_python_calls_report,
    format_python_calls_report_text,
    get_python_call_graph_report,
    format_python_call_graph_report_text,
    get_python_check_text,
    get_python_deps_text,
    get_python_defs_text,
    get_python_refs_text,
    get_python_ref_contexts_text,
    get_python_calls_text,
    get_python_call_graph_text,
    get_python_rename_preview_text,
    get_python_rename_preview_report,
    get_python_rename_text,
    get_python_rename_report,
    get_check_replace_python_definition_text,
    get_check_replace_python_definition_report,
    get_replace_python_definition_text,
    get_replace_python_definition_report,
    format_replace_python_definition_report_text,
    format_replace_python_definition_observation,
    format_python_rename_report_text,
    format_python_rename_observation,
    get_code_deps_report,
    format_code_deps_report_text,
    get_code_refs_report,
    format_code_refs_report_text,
    get_code_ref_contexts_report,
    format_code_ref_contexts_report_text,
    get_code_defs_report,
    format_code_defs_report_text,
    get_code_deps_text,
    get_code_refs_text,
    get_code_ref_contexts_text,
    get_code_defs_text,
    get_code_rename_preview_text,
    get_code_rename_preview_report,
    get_code_rename_text,
    get_code_rename_report,
    format_code_rename_report_text,
    format_code_rename_observation,
    parse_symbol_path_argument,
    parse_rename_argument,
    parse_replace_python_definition_argument,
)

from .edit_commands import (
    get_config_check_text,
    get_config_check_report,
    format_config_check_report_text,
    get_check_json_set_text,
    get_check_json_set_report,
    get_json_set_text,
    get_json_set_report,
    get_check_json_remove_text,
    get_check_json_remove_report,
    get_json_remove_text,
    get_json_remove_report,
    get_check_json_patch_text,
    get_check_json_patch_report,
    get_json_patch_text,
    get_json_patch_report,
    format_json_pointer_observation,
    serialize_json_pointer_report,
    format_json_pointer_report_text,
    format_json_patch_observation,
    serialize_json_patch_report,
    format_json_patch_report_text,
    get_check_replace_lines_text,
    get_check_replace_lines_report,
    get_replace_lines_text,
    get_replace_lines_report,
    get_check_insert_lines_text,
    get_check_insert_lines_report,
    get_insert_lines_text,
    get_insert_lines_report,
    get_check_append_file_text,
    get_check_append_file_report,
    get_append_file_text,
    get_append_file_report,
    get_check_write_file_text,
    get_check_write_file_report,
    get_write_file_text,
    get_write_file_report,
    get_check_write_files_text,
    get_check_write_files_report,
    get_write_files_text,
    get_write_files_report,
    get_check_edit_file_text,
    get_check_edit_file_report,
    get_edit_file_text,
    get_edit_file_report,
    get_check_multi_edit_file_text,
    get_check_multi_edit_file_report,
    get_multi_edit_file_text,
    get_multi_edit_file_report,
    get_check_delete_file_text,
    get_check_delete_file_report,
    get_delete_file_text,
    get_delete_file_report,
    get_check_delete_files_text,
    get_check_delete_files_report,
    get_delete_files_text,
    get_delete_files_report,
    get_check_move_file_text,
    get_check_move_file_report,
    get_move_file_text,
    get_move_file_report,
    get_check_move_files_text,
    get_check_move_files_report,
    get_move_files_text,
    get_move_files_report,
    get_check_copy_file_text,
    get_check_copy_file_report,
    get_copy_file_text,
    get_copy_file_report,
    get_check_copy_files_text,
    get_check_copy_files_report,
    get_copy_files_text,
    get_copy_files_report,
    get_check_move_dir_text,
    get_check_move_dir_report,
    get_move_dir_text,
    get_move_dir_report,
    get_check_move_dirs_text,
    get_check_move_dirs_report,
    get_move_dirs_text,
    get_move_dirs_report,
    get_check_copy_dir_text,
    get_check_copy_dir_report,
    get_copy_dir_text,
    get_copy_dir_report,
    get_check_copy_dirs_text,
    get_check_copy_dirs_report,
    get_copy_dirs_text,
    get_copy_dirs_report,
    get_check_create_dir_text,
    get_check_create_dir_report,
    get_create_dir_text,
    get_create_dir_report,
    get_check_create_dirs_text,
    get_check_create_dirs_report,
    get_create_dirs_text,
    get_create_dirs_report,
    get_check_delete_empty_dir_text,
    get_check_delete_empty_dir_report,
    get_delete_empty_dir_text,
    get_delete_empty_dir_report,
    get_check_delete_empty_dirs_text,
    get_check_delete_empty_dirs_report,
    get_delete_empty_dirs_text,
    get_delete_empty_dirs_report,
    get_check_set_executable_text,
    get_check_set_executable_report,
    get_set_executable_text,
    get_set_executable_report,
    get_check_patch_text,
    get_check_patch_report,
    get_patch_text,
    get_patch_report,
    get_check_patches_text,
    get_check_patches_report,
    get_patches_text,
    get_patches_report,
    format_executable_observation,
    serialize_executable_report,
    format_executable_report_text,
    format_patch_observation,
    serialize_patch_report,
    format_patch_report_text,
    format_patches_observation,
    serialize_patches_report,
    format_patches_report_text,
    format_path_action_observation,
    serialize_path_action_report,
    format_path_action_report_text,
    format_path_list_observation,
    serialize_path_list_report,
    format_path_list_report_text,
    format_file_transfer_observation,
    serialize_file_transfer_report,
    format_file_transfer_report_text,
    format_file_transfer_list_observation,
    serialize_file_transfer_list_report,
    format_file_transfer_list_report_text,
    format_write_files_observation,
    serialize_write_files_report,
    format_write_files_report_text,
    format_line_edit_observation,
    serialize_line_edit_report,
    format_line_edit_report_text,
    parse_required_single_path_argument,
    parse_required_path_list_argument,
    parse_source_destination_argument,
    parse_file_transfer_list_argument,
    parse_directory_transfer_list_argument,
    parse_executable_argument,
    parse_optional_bool,
    parse_patch_argument,
    parse_patches_argument,
    read_patch_argument_value,
    parse_write_file_argument,
    parse_write_file_list_argument,
    parse_edit_file_argument,
    parse_multi_edit_file_argument,
    get_check_regex_replace_text,
    get_check_regex_replace_report,
    get_regex_replace_text,
    get_regex_replace_report,
    format_regex_replace_observation,
    serialize_regex_replace_report,
    format_regex_replace_report_text,
    parse_json_set_argument,
    parse_json_remove_argument,
    parse_json_patch_argument,
    parse_json_patch_operations,
    parse_replace_lines_argument,
    parse_insert_lines_argument,
    parse_append_file_argument,
    parse_regex_replace_argument,
    parse_line_number,
    validate_line_number,
    validate_line_range,
    validate_nonnegative_int,
    validate_positive_int,
    format_check_location,
)

from .git_commands import format_blame_report_text, format_branches_report_text, format_git_commit_report_text, format_git_conflicts_report_text, format_git_fetch_report_text, format_git_info_report_text, format_git_index_report_text, format_git_pull_report_text, format_git_push_report_text, format_git_restore_report_text, format_git_stash_apply_report_text, format_git_stash_drop_report_text, format_git_stash_report_text, format_git_status_report_text, format_git_switch_report_text, format_git_sync_preview_report_text, format_log_report_text, format_show_report_text, format_stashes_report_text, get_blame_report, get_blame_text, get_branches_report, get_branches_text, get_check_commit_report, get_check_commit_text, get_check_fetch_report, get_check_fetch_text, get_check_pull_report, get_check_pull_text, get_check_push_report, get_check_push_text, get_check_restore_report, get_check_restore_text, get_check_stage_report, get_check_stage_text, get_check_stash_apply_report, get_check_stash_apply_text, get_check_stash_drop_report, get_check_stash_drop_text, get_check_stash_report, get_check_stash_text, get_check_switch_report, get_check_switch_text, get_check_unstage_report, get_check_unstage_text, get_commit_report, get_commit_text, get_fetch_report, get_fetch_text, get_git_conflicts_report, get_git_conflicts_text, get_git_info_report, get_git_info_text, get_git_status_report, get_git_status_text, get_log_report, get_log_text, get_pull_report, get_pull_text, get_push_report, get_push_text, get_restore_report, get_restore_text, get_show_report, get_show_text, get_stage_report, get_stage_text, get_stash_apply_report, get_stash_apply_text, get_stash_drop_report, get_stash_drop_text, get_stash_report, get_stash_text, get_stashes_report, get_stashes_text, get_switch_report, get_switch_text, get_unstage_report, get_unstage_text, parse_log_request, parse_optional_remote_argument, parse_show_request, parse_stash_argument, parse_stashes_request, parse_switch_argument
from .process_commands import decode_stdin_escapes, format_check_stop_all_processes_report_text, format_check_stop_process_report_text, format_check_write_process_report_text, format_env_report_text, format_process_output_contexts_report_text, format_process_output_diagnostics_report_text, format_process_report_text, format_processes_report_text, format_stop_all_processes_report_text, format_stop_process_report_text, format_structured_command_output_analysis_lines, format_wait_process_report_text, format_write_process_report_text, get_check_stop_all_processes_report, get_check_stop_all_processes_text, get_check_stop_process_report, get_check_stop_process_text, get_check_write_process_report, get_check_write_process_text, get_env_report, get_env_text, get_process_output_contexts_report, get_process_output_contexts_text, get_process_output_diagnostics_report, get_process_output_diagnostics_text, get_process_report, get_process_text, get_processes_report, get_processes_text, get_stop_all_processes_report, get_stop_all_processes_text, get_stop_process_report, get_stop_process_text, get_wait_process_report, get_wait_process_text, get_write_process_report, get_write_process_text, parse_process_request, parse_wait_process_request, parse_write_process_request, process_status_text, serialize_command_output_analysis, serialize_process_info, serialize_stopped_process_info, serialize_write_process_report


from .workflow_commands import (
    blocked_command_examples,
    build_checkpoint_create_report,
    build_project_instructions_template,
    checkpoint_root,
    checkpoint_status_error_report,
    clip_local_checkpoint_untracked_paths,
    clip_with_flag,
    count_status_kinds,
    create_local_checkpoint_metadata,
    display_checkpoint_file,
    filter_handoff_status,
    final_review_common_report,
    final_review_status_checks,
    format_changes_report_text,
    format_check_checkpoint_delete_report_text,
    format_check_checkpoint_prune_report_text,
    format_check_checkpoint_restore_report_text,
    format_check_location,
    format_checkpoint_create_report_text,
    format_checkpoint_created,
    format_checkpoint_delete_report_text,
    format_checkpoint_diff_report_text,
    format_checkpoint_prune_report_text,
    format_checkpoint_restore_report_text,
    format_checkpoint_restore_report_text_with_title,
    format_checkpoint_show_report_text,
    format_checkpoint_status_report_text,
    format_checkpoints_report_text,
    format_context_report_text,
    format_diff_contexts_report_text,
    format_diff_hunk_lines,
    format_diff_hunks_report_text,
    format_diff_report_text,
    format_doctor_report_text,
    format_handoff_report_text,
    format_init_report_text,
    format_review_check,
    format_review_file,
    format_review_process,
    format_review_report_text,
    format_review_syntax_check,
    format_status_report_text,
    get_changes_report,
    get_changes_text,
    get_check_checkpoint_delete_report,
    get_check_checkpoint_delete_text,
    get_check_checkpoint_prune_report,
    get_check_checkpoint_prune_text,
    get_check_checkpoint_restore_report,
    get_check_checkpoint_restore_text,
    get_checkpoint_delete_report,
    get_checkpoint_delete_text,
    get_checkpoint_diff_report,
    get_checkpoint_diff_text,
    get_checkpoint_prune_report,
    get_checkpoint_prune_text,
    get_checkpoint_report,
    get_checkpoint_restore_report,
    get_checkpoint_restore_text,
    get_checkpoint_show_report,
    get_checkpoint_show_text,
    get_checkpoint_status_report,
    get_checkpoint_status_text,
    get_checkpoint_text,
    get_checkpoints_report,
    get_checkpoints_text,
    get_command_hard_block_report,
    get_context_report,
    get_context_text,
    get_diff_contexts_report,
    get_diff_contexts_text,
    get_diff_hunks_report,
    get_diff_hunks_text,
    get_diff_report,
    get_diff_text,
    get_doctor_report,
    get_doctor_text,
    get_handoff_plan_text,
    get_handoff_report,
    get_handoff_text,
    get_init_report,
    get_review_report,
    get_review_text,
    get_status_report,
    get_status_text,
    init_project_instructions,
    is_runtime_checkpoint_path,
    is_runtime_status_path,
    is_safe_checkpoint_relative_path,
    local_checkpoint_untracked_files_match,
    local_checkpoint_untracked_paths,
    local_final_review_workspace,
    normalize_checkpoint_label,
    normalize_project_instructions_file_name,
    parse_checkpoint_keep_last,
    parse_diff_argument,
    read_checkpoint_patch,
    read_checkpoints,
    read_git_head,
    read_local_checkpoint_metadata,
    read_local_checkpoint_untracked_manifest,
    resolve_checkpoint_dir,
    restore_local_checkpoint_untracked_files,
    run_git_checkpoint_command,
    save_local_checkpoint_untracked_files,
    serialize_checkpoint_info,
    serialize_checkpoint_metadata,
    serialize_diff_hunk,
    serialize_file_context_result,
    short_head,
    validate_diff_contexts_limits,
    validate_diff_hunks_limits,
)


from .session_commands import format_cost_report_text, format_run_session_verification_report_text, format_session_audit_report_text, format_session_commands_report_text, format_session_failures_report_text, format_session_files_report_text, format_session_handoff_report_text, format_session_output_contexts_report_text, format_session_output_diagnostics_report_text, format_session_plan_report_text, format_session_search_report_text, format_session_summary_report_text, format_session_transcript_report_text, format_session_verification_report_text, format_sessions_report_text, format_usage_report_text, get_compact_context, get_cost_report, get_cost_text, get_last_session_report, get_last_session_text, get_plan_report, get_plan_text, get_resume_context, get_run_session_verification_report, get_run_session_verification_text, get_session_audit_report, get_session_audit_text, get_session_commands_report, get_session_commands_text, get_session_failures_report, get_session_failures_text, get_session_files_report, get_session_files_text, get_session_handoff_report, get_session_handoff_text, get_session_output_contexts_observation, get_session_output_contexts_report, get_session_output_contexts_text, get_session_output_diagnostics_observation, get_session_output_diagnostics_report, get_session_output_diagnostics_text, get_session_report, get_session_search_report, get_session_search_text, get_session_text, get_session_verification_report, get_session_verification_text, get_sessions_report, get_sessions_text, get_transcript_report, get_transcript_text, get_usage_report, get_usage_text
def _clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    return f"{compacted[:max_length]}\n[context output truncated]"


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def _exists_text(path: Path) -> str:
    return "yes" if path.exists() else "no"


def _top_level_entries(project_root: Path) -> list[str]:
    try:
        files = list_files(project_root)
    except OSError:
        return []
    seen: list[str] = []
    for relative in files:
        name = relative.split("/", 1)[0]
        if name not in seen:
            seen.append(name)
        if len(seen) >= 12:
            break
    return [f"- `{name}`" for name in seen]


def _extract_command_lines(command_hints: str) -> list[str]:
    lines: list[str] = []
    current_cwd = "."
    for raw_line in command_hints.splitlines():
        line = raw_line.strip()
        if line.startswith("Cwd: "):
            current_cwd = line[5:] or "."
        elif line.startswith("- "):
            lines.append(f"- `{line[2:]}` from `{current_cwd}`")
        if len(lines) >= 8:
            break
    return lines
