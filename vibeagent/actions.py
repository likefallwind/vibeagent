from __future__ import annotations

import ast
import json
import shlex
import signal
import socket
import time
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .checkpoint_actions import (
    check_checkpoint_delete_observation,
    check_checkpoint_prune_observation,
    check_checkpoint_restore_observation,
    checkpoint_delete_observation,
    checkpoint_diff_observation,
    checkpoint_prune_observation,
    checkpoint_restore_observation,
    checkpoint_show_observation,
    checkpoint_status_observation,
    checkpoint_untracked_files_match,
    create_checkpoint_observation,
    list_checkpoints_observation,
    read_checkpoint_git_head,
    restore_checkpoint_untracked_files,
    save_checkpoint_untracked_files,
)
from .final_review_actions import (
    FINAL_REVIEW_LARGE_FILE_BYTES,
    FINAL_REVIEW_SECRET_SCAN_BYTES,
    PROJECT_CHANGE_RESULT_KINDS,
    SECRET_LIKE_PATTERNS,
    final_review_scan_file_items,
    final_review_session_verification_issues,
    find_changed_gitlinks,
    find_hidden_tracked_git_changes,
    find_large_changed_files,
    find_nested_git_repositories,
    find_secret_like_changed_files,
    find_secret_like_git_diff_additions,
    find_unsafe_changed_symlinks,
    read_git_operation_state,
    secret_like_line_label,
)
from .file_action_executor import execute_file_action
from .git_action_executor import execute_git_action
from .project_context_action_executor import execute_project_context_action
from .read_action_executor import execute_read_action
from .session_action_executor import execute_session_action
from .action_parsing import ActionParseError, parse_tool_action, summarize_plan_update
from .action_results import (
    build_code_rename_preview_files,
    build_python_rename_preview_files,
    build_reference_context_results,
)
from .types import (
    AgentAction,
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckJsonRemoveAction,
    CheckJsonRemoveObservation,
    CheckJsonPatchAction,
    CheckJsonPatchObservation,
    CheckJsonSetAction,
    CheckJsonSetObservation,
    CheckReplacePythonDefinitionAction,
    CheckReplacePythonDefinitionObservation,
    CheckStartCommandAction,
    CheckStartCommandObservation,
    CheckStopAllProcessesAction,
    CheckStopProcessAction,
    CheckWriteProcessAction,
    CheckFocusedTestCommandsAction,
    CheckFocusedTestCommandsObservation,
    CheckpointCreateAction,
    CheckpointDiffAction,
    CheckpointListAction,
    CheckpointDeleteAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
    CheckpointShowAction,
    CheckpointStatusAction,
    CodeDependenciesAction,
    CodeDependenciesObservation,
    CodeDependenciesResult,
    CodeDefinition,
    CodeDefinitionsAction,
    CodeDefinitionsObservation,
    CodeImportRef,
    CodeReference,
    CodeReferenceContextsAction,
    CodeReferenceContextsObservation,
    CodeReferencesAction,
    CodeReferencesObservation,
    CodeRenameAction,
    CodeRenameObservation,
    CodeRenamePreviewAction,
    CodeRenamePreviewObservation,
    CommandCheckAction,
    CommandResult,
    CheckRunCommandsAction,
    CheckRunCommandsObservation,
    CodeOutlineAction,
    CodeOutlineObservation,
    CodeOutlineResult,
    ConfigCheckAction,
    ConfigCheckObservation,
    ConfigCheckResult,
    EnvironmentInfoAction,
    EnvironmentInfoObservation,
    FinalReviewAction,
    FinalReviewObservation,
    FinishObservation,
    FileInfoAction,
    FileInfoObservation,
    FileInfoResult,
    FindFilesAction,
    FindFilesObservation,
    ImageInfoAction,
    ImageInfoObservation,
    ImageInfoResult,
    GlobAction,
    GlobObservation,
    GitChangeFile,
    GitDiffHunk,
    HttpCheckAction,
    HttpFetchAction,
    JsonRemoveAction,
    JsonRemoveObservation,
    JsonPatchAction,
    JsonPatchObservation,
    JsonSetAction,
    JsonSetObservation,
    ListProcessesAction,
    ListFilesAction,
    ListFilesObservation,
    ListTreeAction,
    ListTreeObservation,
    Observation,
    OutputContextsAction,
    OutputContextsObservation,
    OutputDiagnosticsAction,
    OutputDiagnosticsObservation,
    PortCheckAction,
    ProcessOutputContextsAction,
    ProcessOutputDiagnosticsAction,
    PythonSymbol,
    PythonSymbolsAction,
    PythonSymbolsObservation,
    PythonSymbolsResult,
    PythonReference,
    PythonCheckAction,
    PythonCheckObservation,
    PythonCheckResult,
    PythonCall,
    PythonCallGraphAction,
    PythonCallGraphObservation,
    PythonCallsAction,
    PythonCallsObservation,
    PythonDependenciesAction,
    PythonDependenciesObservation,
    PythonDependenciesResult,
    PythonDefinition,
    PythonDefinitionsAction,
    PythonDefinitionsObservation,
    PythonImportRef,
    ReplacePythonDefinitionAction,
    ReplacePythonDefinitionObservation,
    PythonReferencesAction,
    PythonReferenceContextsAction,
    PythonReferenceContextsObservation,
    PythonReferencesObservation,
    PythonRenameAction,
    PythonRenameObservation,
    PythonRenamePreviewAction,
    PythonRenamePreviewObservation,
    ProjectCommand,
    ProjectCommandsAction,
    ProjectCommandsObservation,
    FocusedTestCommand,
    FocusedTestCommandsAction,
    FocusedTestCommandsObservation,
    RelatedTestCandidate,
    RelatedTestsAction,
    RelatedTestsObservation,
    ProjectInstructionSource,
    ProjectInstructionsAction,
    ProjectInstructionsObservation,
    ProjectOverviewAction,
    ProjectOverviewObservation,
    ProjectTodo,
    ProjectTodosAction,
    ProjectTodosObservation,
    ProjectManifest,
    ProjectManifestItem,
    ProjectManifestsAction,
    ProjectManifestsObservation,
    ReadFileAction,
    ReadFileContextAction,
    ReadFileContextObservation,
    ReadFileContextResult,
    ReadFileContextsAction,
    ReadFileContextsObservation,
    ReadFileObservation,
    ReadFileResult,
    ReadFilesAction,
    ReadFilesObservation,
    ReadFileRangeResult,
    ReadFileRangesAction,
    ReadFileRangesObservation,
    ReadProcessAction,
    ReviewChangesAction,
    ReviewChangesObservation,
    RepoMapAction,
    RepoMapObservation,
    RepoMapPythonFile,
    CheckSuggestedChecksAction,
    CheckSuggestedChecksObservation,
    RunCommandAction,
    RunCommandObservation,
    RunCommandItem,
    RunCommandsAction,
    RunCommandsObservation,
    RunFocusedTestCommandsAction,
    RunFocusedTestCommandsObservation,
    RunSuggestedChecksAction,
    RunSuggestedChecksObservation,
    RuntimeToolInfo,
    SearchAction,
    SearchContextsAction,
    SearchContextsObservation,
    SearchContextResult,
    SearchObservation,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    SuggestedCheck,
    SuggestChecksAction,
    SuggestChecksObservation,
    TailFileAction,
    TailFileObservation,
    UntrackedFilePreview,
    UpdatePlanAction,
    UpdatePlanObservation,
    WaitProcessAction,
    WriteProcessAction,
)
from .command_safety import (
    HIGH_RISK_COMMAND_BLOCK_REASON,
    RAW_DEVICE_WRITE_BLOCK_REASON,
    RECURSIVE_DELETE_BLOCK_REASON,
    RECURSIVE_PERMISSION_BLOCK_REASON,
    args_after_operand,
    command_contains_dangerous_git_clean,
    command_contains_dangerous_rm,
    command_executes_powershell_network_script,
    command_invokes_high_risk_executable,
    command_launches_gui_application,
    command_operands,
    command_path_arguments,
    command_pipes_network_script_to_shell,
    command_recursively_changes_broad_permissions,
    command_writes_to_device,
    container_orchestration_invocation_changes_external_state,
    docker_compose_invocation_changes_external_state,
    docker_compose_options_with_values,
    docker_invocation_changes_external_state,
    docker_options_with_values,
    firewall_invocation_changes_network_state,
    first_command_operand,
    first_systemctl_verb,
    fuser_invocation_kills_processes,
    get_blocked_command_reason,
    helm_invocation_changes_cluster_state,
    helm_options_with_values,
    invocation_has_raw_device_operand,
    ip_invocation_changes_network_state,
    iptables_invocation_changes_network_state,
    is_dangerous_recursive_delete_target,
    is_raw_device_write_target,
    javascript_skip_ws,
    javascript_string_array_literal,
    javascript_string_literal,
    kill_signal_token,
    kill_target_is_broad,
    kubectl_invocation_changes_cluster_state,
    kubectl_options_with_values,
    legacy_network_invocation_changes_state,
    losetup_invocation_changes_device_state,
    matching_kill_options_with_values,
    nft_invocation_changes_network_state,
    node_child_process_nested_command,
    node_destructured_binding_alias,
    node_import_default_aliases,
    node_import_named_aliases,
    node_one_liner_blocked_command_reason,
    node_require_assignment_aliases,
    node_require_destructured_aliases,
    node_script_blocked_command_reason,
    parse_kill_signal_and_targets,
    parse_matching_kill_signal,
    parted_invocation_changes_device_state,
    partition_editor_invocation_changes_device_state,
    partition_editor_options_with_values,
    permission_invocation_targets_broad_path_recursively,
    process_signal_is_zero,
    process_termination_invocation_is_broad,
    python_asyncio_subprocess_command,
    python_call_deletes_broad_path,
    python_call_is_compile,
    python_call_is_eval_or_exec,
    python_call_is_os_startfile,
    python_call_is_text_open,
    python_call_is_webbrowser_get,
    python_call_is_webbrowser_open,
    python_call_shell_command,
    python_call_string_argument,
    python_call_writes_raw_device,
    python_command_argument,
    python_dynamic_import_name,
    python_executable_command_from_args,
    python_expr_is_compile_reference,
    python_expr_is_eval_or_exec_reference,
    python_first_string_argument,
    python_getattr_attribute,
    python_literal_compile_script,
    python_literal_eval_exec_script,
    python_literal_source_text,
    python_one_liner_blocked_command_reason,
    python_open_call_writes_raw_device,
    python_os_exec_spawn_command,
    python_os_exec_spawn_function_name,
    python_os_open_call_writes_raw_device,
    python_os_open_flags_write,
    python_pathlib_call_path,
    python_pathlib_call_writes_raw_device,
    python_script_blocked_command_reason,
    python_static_getattr_target,
    python_string_constant,
    python_string_sequence,
    segment_invokes_network_fetch,
    segment_invokes_script_interpreter,
    service_invocation_changes_system_state,
    sgdisk_invocation_mutates_partition_table,
    shell_command_invocations,
    shell_command_segments,
    shell_pipeline_segments,
    shell_wrapped_blocked_command_reason,
    storage_invocation_changes_device_state,
    strip_env_command_prefix,
    sysctl_invocation_changes_kernel_state,
    systemctl_invocation_changes_system_state,
    unwrapped_shell_command_parts,
    unwrapped_shell_executable_name,
)
from .process_runtime import (
    BACKGROUND_PROCESSES,
    BackgroundProcess,
    PersistentProcessRecord,
    attach_output_analysis_to_command_result,
    attach_output_analysis_to_process_observation,
    check_stop_all_background_processes,
    check_stop_background_process,
    check_write_background_process,
    command_result_failed,
    execute_run_command_item,
    list_background_processes,
    match_process_output,
    output_context_results_from_dicts,
    output_diagnostics_from_dicts,
    parse_persistent_process_record,
    persistent_process_running,
    process_observation_failed,
    process_record_path,
    process_registry_dir,
    process_signal_name,
    read_background_process,
    read_background_process_output_contexts,
    read_background_process_output_diagnostics,
    read_persistent_process_exit_code,
    read_persistent_process_record,
    read_persistent_process_records,
    read_process_start_ticks,
    read_text_tail,
    relative_cwd,
    relative_process_log_path,
    remove_persistent_process_record,
    run_command,
    start_background_command,
    stop_all_background_processes,
    stop_background_process,
    terminate_persistent_process,
    truncate_command_output,
    wait_background_process,
    wait_background_process_output,
    wait_persistent_process,
    wrap_background_command,
    write_background_process,
    write_persistent_process_record,
)
from .runtime_checks import (
    build_command_check_observation,
    build_command_preflight,
    check_http_url,
    check_tcp_port,
    fetch_http_url,
)
from .tool_definitions import AGENT_TOOL_DEFINITIONS

from .workspace import (
    RunWorkspace,
    build_repo_map,
    list_project_files,
    list_project_tree,
    json_patch_project_file,
    json_remove_project_file,
    json_set_project_file,
    apply_code_rename,
    apply_python_rename,
    preview_code_rename,
    preview_python_rename,
    preview_json_patch_project_file,
    preview_json_remove_project_file,
    preview_json_set_project_file,
    read_git_conflicts,
    read_git_info,
    find_python_references,
    find_code_references,
    find_code_definitions,
    find_python_definitions,
    find_python_calls,
    inspect_python_call_graph,
    read_environment_info,
    read_project_file_info,
    read_project_image_info,
    read_project_file_context_result,
    read_project_file_result,
    read_project_file_tail_result,
    read_output_contexts_result,
    read_output_diagnostics_result,
    find_related_tests,
    suggest_focused_test_commands,
    read_project_commands,
    read_project_instruction_sources,
    read_project_manifests,
    read_project_todos,
    read_code_outline,
    read_python_symbol_outline,
    preview_replace_python_definition,
    review_project_changes,
    replace_python_definition,
    find_project_files_result,
    glob_project_files,
    inspect_code_dependencies,
    inspect_python_dependencies,
    search_project_contexts_result,
    search_project_result,
    check_config_syntax,
    check_python_syntax,
    suggest_project_checks,
)
from .workspace_resolve import resolve_mutation_path


def execute_action(workspace: RunWorkspace, action: AgentAction, command_timeout_ms: int = 30_000) -> Observation:
    # Dispatch one action at a time; all side effects stay within the given project workspace.
    read_observation = execute_read_action(workspace, action)
    if read_observation is not None:
        return read_observation

    if isinstance(action, PythonCheckAction):
        try:
            raw_results, total = check_python_syntax(workspace, action.path, max_files=action.max_files)
            files = [PythonCheckResult(**item) for item in raw_results]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            message = f"Checked {len(files)}/{total} Python file(s); {failed_count} failed."
            ok = failed_count == 0
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return PythonCheckObservation(
            kind="python_check",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, ConfigCheckAction):
        try:
            raw_results, total = check_config_syntax(workspace, action.path, max_files=action.max_files)
            files = [ConfigCheckResult(**item) for item in raw_results]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            message = f"Checked {len(files)}/{total} config file(s); {failed_count} failed."
            ok = failed_count == 0
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return ConfigCheckObservation(
            kind="config_check",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckJsonSetAction):
        try:
            _target, diff = preview_json_set_project_file(
                workspace,
                action.path,
                action.pointer,
                action.value,
                create_missing=action.create_missing,
            )
            ok = True
            message = f"JSON set can apply to {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return CheckJsonSetObservation(
            kind="check_json_set",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, JsonSetAction):
        try:
            _target, diff = json_set_project_file(
                workspace,
                action.path,
                action.pointer,
                action.value,
                create_missing=action.create_missing,
            )
            ok = True
            message = f"Set JSON value in {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return JsonSetObservation(
            kind="json_set",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckJsonRemoveAction):
        try:
            _target, diff = preview_json_remove_project_file(workspace, action.path, action.pointer)
            ok = True
            message = f"JSON remove can apply to {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return CheckJsonRemoveObservation(
            kind="check_json_remove",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, JsonRemoveAction):
        try:
            _target, diff = json_remove_project_file(workspace, action.path, action.pointer)
            ok = True
            message = f"Removed JSON value in {action.path} at {action.pointer}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return JsonRemoveObservation(
            kind="json_remove",
            path=action.path,
            pointer=action.pointer,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckJsonPatchAction):
        operations = [operation.__dict__ for operation in action.operations]
        try:
            _target, diff = preview_json_patch_project_file(workspace, action.path, operations)
            ok = True
            message = f"JSON patch can apply {len(action.operations)} operation(s) to {action.path}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return CheckJsonPatchObservation(
            kind="check_json_patch",
            path=action.path,
            operation_count=len(action.operations),
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, JsonPatchAction):
        operations = [operation.__dict__ for operation in action.operations]
        try:
            _target, diff = json_patch_project_file(workspace, action.path, operations)
            ok = True
            message = f"Applied {len(action.operations)} JSON patch operation(s) to {action.path}."
        except ValueError as error:
            ok = False
            diff = ""
            message = str(error)
        return JsonPatchObservation(
            kind="json_patch",
            path=action.path,
            operation_count=len(action.operations),
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, PythonDependenciesAction):
        try:
            raw_results, total = inspect_python_dependencies(
                workspace,
                action.path,
                max_files=action.max_files,
                max_imports=action.max_imports,
            )
            files = [
                PythonDependenciesResult(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    module=str(item["module"]),
                    imports=[PythonImportRef(**import_item) for import_item in item["imports"]],
                    local_modules=list(item["local_modules"]),
                    external_modules=list(item["external_modules"]),
                    message=str(item["message"]),
                )
                for item in raw_results
            ]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            ok = failed_count == 0
            message = f"Inspected dependencies for {len(files)}/{total} Python file(s); {failed_count} failed."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return PythonDependenciesObservation(
            kind="python_dependencies",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, CodeDependenciesAction):
        try:
            raw_results, total = inspect_code_dependencies(
                workspace,
                action.path,
                max_files=action.max_files,
                max_imports=action.max_imports,
            )
            files = [
                CodeDependenciesResult(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    language=str(item["language"]),
                    imports=[CodeImportRef(**import_item) for import_item in item["imports"]],
                    dependencies=list(item["dependencies"]),
                    message=str(item["message"]),
                )
                for item in raw_results
            ]
            failed_count = sum(1 for file in files if not file.ok)
            truncated = len(files) < total
            ok = failed_count == 0
            message = f"Inspected dependencies for {len(files)}/{total} source file(s); {failed_count} failed."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return CodeDependenciesObservation(
            kind="code_dependencies",
            path=action.path,
            files=files,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, CodeReferencesAction):
        try:
            raw_references, total = find_code_references(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            references = [CodeReference(**item) for item in raw_references]
            truncated = len(references) < total
            ok = True
            message = f"Found {total} code reference(s) for {action.symbol}."
        except ValueError as error:
            references = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return CodeReferencesObservation(
            kind="code_references",
            symbol=action.symbol,
            path=action.path,
            references=references,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    if isinstance(action, CodeReferenceContextsAction):
        try:
            raw_references, total = find_code_references(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            contexts = build_reference_context_results(
                workspace,
                raw_references,
                action.symbol,
                action.context_lines,
                action.max_bytes_per_context,
            )
            truncated = len(contexts) < total
            ok = True
            message = f"Found {total} code reference context(s) for {action.symbol}."
            if truncated:
                message += f" Showing first {len(contexts)}."
        except ValueError as error:
            contexts = []
            total = 0
            truncated = False
            ok = False
            message = str(error)
        return CodeReferenceContextsObservation(
            kind="code_reference_contexts",
            symbol=action.symbol,
            path=action.path,
            contexts=contexts,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
            context_lines=action.context_lines,
            max_bytes_per_context=action.max_bytes_per_context,
        )

    if isinstance(action, CodeDefinitionsAction):
        try:
            raw_definitions, total, errors = find_code_definitions(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
                max_lines=action.max_lines,
            )
            definitions = [CodeDefinition(**item) for item in raw_definitions]
            truncated = len(definitions) < total
            ok = not errors
            message = f"Found {total} code definition(s) for {action.symbol}."
        except ValueError as error:
            definitions = []
            total = 0
            errors = [str(error)]
            truncated = False
            ok = False
            message = str(error)
        return CodeDefinitionsObservation(
            kind="code_definitions",
            symbol=action.symbol,
            path=action.path,
            definitions=definitions,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, CodeRenamePreviewAction):
        try:
            preview = preview_code_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_code_rename_preview_files(preview)
            message = str(preview["message"])
            if bool(preview["truncated"]):
                message += f" Showing first {action.max_replacements} replacement(s)."
            errors = list(preview["errors"])
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            return CodeRenamePreviewObservation(
                kind="code_rename_preview",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=files,
                total_replacements=int(preview["total_replacements"]),
                total_files=int(preview["total_files"]),
                truncated=bool(preview["truncated"]),
                ok=True,
                errors=errors,
                message=message,
            )
        except ValueError as error:
            return CodeRenamePreviewObservation(
                kind="code_rename_preview",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=[],
                total_replacements=0,
                total_files=0,
                truncated=False,
                ok=False,
                errors=[],
                message=str(error),
            )

    if isinstance(action, CodeRenameAction):
        try:
            result = apply_code_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_code_rename_preview_files(result)
            return CodeRenameObservation(
                kind="code_rename",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=files,
                total_replacements=int(result["total_replacements"]),
                total_files=int(result["total_files"]),
                ok=True,
                errors=[],
                message=f"Renamed {action.symbol} to {action.new_name} in {len(files)} file(s).",
                diff=str(result["diff"]),
            )
        except ValueError as error:
            return CodeRenameObservation(
                kind="code_rename",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=[],
                total_replacements=0,
                total_files=0,
                ok=False,
                errors=[],
                message=str(error),
                diff="",
            )

    if isinstance(action, PythonDefinitionsAction):
        try:
            raw_definitions, total, errors = find_python_definitions(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
                max_lines=action.max_lines,
            )
            definitions = [PythonDefinition(**item) for item in raw_definitions]
            truncated = len(definitions) < total
            message = f"Found {total} Python definition(s)."
            if truncated:
                message += f" Showing first {len(definitions)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            definitions = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonDefinitionsObservation(
            kind="python_definitions",
            symbol=action.symbol,
            path=action.path,
            definitions=definitions,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, PythonCallsAction):
        try:
            raw_calls, total, errors = find_python_calls(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            calls = [PythonCall(**item) for item in raw_calls]
            truncated = len(calls) < total
            message = f"Found {total} Python call(s)."
            if truncated:
                message += f" Showing first {len(calls)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            calls = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonCallsObservation(
            kind="python_calls",
            symbol=action.symbol,
            path=action.path,
            calls=calls,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, CheckReplacePythonDefinitionAction):
        try:
            _, _after, diff, definition = preview_replace_python_definition(
                workspace,
                action.symbol,
                action.content,
                relative_path=action.path,
            )
            return CheckReplacePythonDefinitionObservation(
                kind="check_replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=str(definition["path"]),
                qualified_name=str(definition["qualified_name"]),
                start_line=int(definition["line"]),
                end_line=int(definition["end_line"]),
                ok=True,
                message=f"Python definition replacement can apply to {definition['qualified_name']} in {definition['path']}.",
                diff=diff,
            )
        except ValueError as error:
            return CheckReplacePythonDefinitionObservation(
                kind="check_replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=None,
                qualified_name=None,
                start_line=None,
                end_line=None,
                ok=False,
                message=str(error),
                diff="",
            )

    if isinstance(action, ReplacePythonDefinitionAction):
        try:
            _, diff, definition = replace_python_definition(
                workspace,
                action.symbol,
                action.content,
                relative_path=action.path,
            )
            return ReplacePythonDefinitionObservation(
                kind="replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=str(definition["path"]),
                qualified_name=str(definition["qualified_name"]),
                start_line=int(definition["line"]),
                end_line=int(definition["end_line"]),
                ok=True,
                message=f"Replaced Python definition {definition['qualified_name']} in {definition['path']}.",
                diff=diff,
            )
        except ValueError as error:
            return ReplacePythonDefinitionObservation(
                kind="replace_python_definition",
                symbol=action.symbol,
                path=action.path,
                definition_path=None,
                qualified_name=None,
                start_line=None,
                end_line=None,
                ok=False,
                message=str(error),
                diff="",
            )

    if isinstance(action, PythonCallGraphAction):
        try:
            raw_edges, total, total_files, errors = inspect_python_call_graph(
                workspace,
                relative_path=action.path,
                max_files=action.max_files,
                max_edges=action.max_edges,
            )
            edges = [PythonCall(**item) for item in raw_edges]
            truncated = len(edges) < total
            message = f"Found {total} Python call graph edge(s) across {total_files} file(s)."
            if truncated:
                message += f" Showing first {len(edges)}."
            if total_files > action.max_files:
                message += f" Inspected first {action.max_files} file(s)."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            edges = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonCallGraphObservation(
            kind="python_call_graph",
            path=action.path,
            edges=edges,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, PythonReferencesAction):
        try:
            raw_references, total, errors = find_python_references(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            references = [PythonReference(**item) for item in raw_references]
            truncated = len(references) < total
            message = f"Found {total} Python reference(s)."
            if truncated:
                message += f" Showing first {len(references)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            references = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonReferencesObservation(
            kind="python_references",
            symbol=action.symbol,
            path=action.path,
            references=references,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
        )

    if isinstance(action, PythonReferenceContextsAction):
        try:
            raw_references, total, errors = find_python_references(
                workspace,
                action.symbol,
                relative_path=action.path,
                max_matches=action.max_matches,
            )
            contexts = build_reference_context_results(
                workspace,
                raw_references,
                action.symbol,
                action.context_lines,
                action.max_bytes_per_context,
            )
            truncated = len(contexts) < total
            message = f"Found {total} Python reference context(s)."
            if truncated:
                message += f" Showing first {len(contexts)}."
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            ok = True
        except ValueError as error:
            contexts = []
            total = 0
            truncated = False
            errors = []
            message = str(error)
            ok = False
        return PythonReferenceContextsObservation(
            kind="python_reference_contexts",
            symbol=action.symbol,
            path=action.path,
            contexts=contexts,
            total=total,
            truncated=truncated,
            ok=ok,
            errors=errors,
            message=message,
            context_lines=action.context_lines,
            max_bytes_per_context=action.max_bytes_per_context,
        )

    if isinstance(action, PythonRenamePreviewAction):
        try:
            preview = preview_python_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_python_rename_preview_files(preview)
            message = str(preview["message"])
            if bool(preview["truncated"]):
                message += f" Showing first {action.max_replacements} replacement(s)."
            errors = list(preview["errors"])
            if errors:
                message += f" Skipped {len(errors)} file(s)."
            return PythonRenamePreviewObservation(
                kind="python_rename_preview",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=files,
                total_replacements=int(preview["total_replacements"]),
                total_files=int(preview["total_files"]),
                truncated=bool(preview["truncated"]),
                ok=True,
                errors=errors,
                message=message,
            )
        except ValueError as error:
            return PythonRenamePreviewObservation(
                kind="python_rename_preview",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=[],
                total_replacements=0,
                total_files=0,
                truncated=False,
                ok=False,
                errors=[],
                message=str(error),
            )

    if isinstance(action, PythonRenameAction):
        try:
            result = apply_python_rename(
                workspace,
                action.symbol,
                action.new_name,
                relative_path=action.path,
                max_files=action.max_files,
                max_replacements=action.max_replacements,
            )
            files = build_python_rename_preview_files(result)
            return PythonRenameObservation(
                kind="python_rename",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=files,
                total_replacements=int(result["total_replacements"]),
                total_files=int(result["total_files"]),
                ok=True,
                errors=[],
                message=f"Renamed {action.symbol} to {action.new_name} in {len(files)} file(s).",
                diff=str(result["diff"]),
            )
        except ValueError as error:
            return PythonRenameObservation(
                kind="python_rename",
                symbol=action.symbol,
                new_name=action.new_name,
                path=action.path,
                files=[],
                total_replacements=0,
                total_files=0,
                ok=False,
                errors=[],
                message=str(error),
                diff="",
            )

    if isinstance(action, SearchAction):
        try:
            result = search_project_result(
                workspace,
                action.query,
                max_matches=action.max_matches,
                relative_path=action.path,
                regex=action.regex,
                case_sensitive=action.case_sensitive,
                context_lines=action.context_lines,
            )
            matches = list(result["matches"])
            total = int(result["total"])
            truncated = bool(result["truncated"])
            message = f"Found {total} match(es)."
            if truncated:
                message += f" Showing {len(matches)}."
            ok = True
        except ValueError as error:
            matches = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return SearchObservation(
            kind="search",
            ok=ok,
            query=action.query,
            matches=matches,
            total=total,
            truncated=truncated,
            message=message,
            path=action.path,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            context_lines=action.context_lines,
        )

    if isinstance(action, SearchContextsAction):
        try:
            result = search_project_contexts_result(
                workspace,
                action.query,
                max_matches=action.max_matches,
                relative_path=action.path,
                regex=action.regex,
                case_sensitive=action.case_sensitive,
                context_lines=action.context_lines,
                max_bytes_per_context=action.max_bytes_per_context,
            )
            contexts = [SearchContextResult(**item) for item in result["contexts"]]
            total = int(result["total"])
            truncated = bool(result["truncated"])
            message = f"Found {total} match context(s)."
            if truncated:
                message += f" Showing {len(contexts)}."
            ok = True
        except ValueError as error:
            contexts = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return SearchContextsObservation(
            kind="search_contexts",
            ok=ok,
            query=action.query,
            contexts=contexts,
            total=total,
            truncated=truncated,
            message=message,
            path=action.path,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            context_lines=action.context_lines,
            max_bytes_per_context=action.max_bytes_per_context,
        )

    if isinstance(action, FindFilesAction):
        try:
            result = find_project_files_result(
                workspace,
                action.query,
                max_matches=action.max_matches,
                relative_path=action.path,
                regex=action.regex,
                case_sensitive=action.case_sensitive,
                include_dirs=action.include_dirs,
            )
            matches = list(result["matches"])
            total = int(result["total"])
            truncated = bool(result["truncated"])
            message = f"Found {total} path match(es)."
            if truncated:
                message += f" Showing {len(matches)}."
            ok = True
        except ValueError as error:
            matches = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return FindFilesObservation(
            kind="find_files",
            ok=ok,
            query=action.query,
            matches=matches,
            total=total,
            truncated=truncated,
            message=message,
            path=action.path,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            include_dirs=action.include_dirs,
        )

    if isinstance(action, GlobAction):
        try:
            matches, total = glob_project_files(
                workspace,
                action.pattern,
                max_matches=action.max_matches,
                include_dirs=action.include_dirs,
            )
            truncated = len(matches) < total
            noun = "file(s) or directories" if action.include_dirs else "file(s)"
            message = f"Found {total} {noun}."
            if truncated:
                message += f" Showing first {len(matches)}."
            ok = True
        except ValueError as error:
            matches = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return GlobObservation(
            kind="glob",
            pattern=action.pattern,
            matches=matches,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    git_observation = execute_git_action(workspace, action)
    if git_observation is not None:
        return git_observation

    if isinstance(action, ReviewChangesAction):
        try:
            review = review_project_changes(workspace, max_files=action.max_files)
        except ValueError as error:
            return ReviewChangesObservation(
                kind="review_changes",
                ok=False,
                changes_ok=False,
                diff_check_ok=False,
                staged_diff_check_ok=False,
                python_ok=False,
                config_ok=False,
                files=[],
                total_files=0,
                python=[],
                python_total=0,
                python_truncated=False,
                config=[],
                config_total=0,
                config_truncated=False,
                suggested_checks=[],
                suggested_checks_total=0,
                suggested_checks_truncated=False,
                diff_hunks=[],
                diff_hunks_total=0,
                diff_hunks_truncated=False,
                staged_diff_hunks=[],
                staged_diff_hunks_total=0,
                staged_diff_hunks_truncated=False,
                untracked_previews=[],
                untracked_previews_total=0,
                untracked_previews_truncated=False,
                diff_check="",
                staged_diff_check="",
                status="",
                message=str(error),
            )
        files = [GitChangeFile(**item) for item in review["files"]]
        python = [PythonCheckResult(**item) for item in review["python"]]
        config = [ConfigCheckResult(**item) for item in review["config"]]
        suggested_checks = [SuggestedCheck(**item) for item in review["suggested_checks"]]
        diff_hunks = [GitDiffHunk(**item) for item in review["diff_hunks"]]
        staged_diff_hunks = [GitDiffHunk(**item) for item in review["staged_diff_hunks"]]
        untracked_previews = [UntrackedFilePreview(**item) for item in review["untracked_previews"]]
        return ReviewChangesObservation(
            kind="review_changes",
            ok=bool(review["ok"]),
            changes_ok=bool(review["changes_ok"]),
            diff_check_ok=bool(review["diff_check_ok"]),
            staged_diff_check_ok=bool(review["staged_diff_check_ok"]),
            python_ok=bool(review["python_ok"]),
            config_ok=bool(review["config_ok"]),
            files=files,
            total_files=int(review["total_files"]),
            python=python,
            python_total=int(review["python_total"]),
            python_truncated=bool(review["python_truncated"]),
            config=config,
            config_total=int(review["config_total"]),
            config_truncated=bool(review["config_truncated"]),
            suggested_checks=suggested_checks,
            suggested_checks_total=int(review["suggested_checks_total"]),
            suggested_checks_truncated=bool(review["suggested_checks_truncated"]),
            diff_hunks=diff_hunks,
            diff_hunks_total=int(review["diff_hunks_total"]),
            diff_hunks_truncated=bool(review["diff_hunks_truncated"]),
            staged_diff_hunks=staged_diff_hunks,
            staged_diff_hunks_total=int(review["staged_diff_hunks_total"]),
            staged_diff_hunks_truncated=bool(review["staged_diff_hunks_truncated"]),
            untracked_previews=untracked_previews,
            untracked_previews_total=int(review["untracked_previews_total"]),
            untracked_previews_truncated=bool(review["untracked_previews_truncated"]),
            diff_check=str(review["diff_check"]),
            staged_diff_check=str(review["staged_diff_check"]),
            status=str(review["status"]),
            message=str(review["message"]),
        )

    if isinstance(action, FinalReviewAction):
        try:
            if action.max_checks < 1:
                raise ValueError("max_checks must be at least 1.")
            if action.max_checks > 50:
                raise ValueError("max_checks must be at most 50.")
            review = review_project_changes(workspace, max_files=action.max_files)
        except ValueError as error:
            return FinalReviewObservation(
                kind="final_review",
                ok=False,
                ready=False,
                blocking_issues=[str(error)],
                warnings=[],
                running_processes=[],
                files=[],
                total_files=0,
                suggested_checks=[],
                suggested_checks_total=0,
                suggested_checks_truncated=False,
                diff_check="",
                staged_diff_check="",
                status="",
                message=str(error),
            )
        files = [GitChangeFile(**item) for item in review["files"]]
        python = [PythonCheckResult(**item) for item in review["python"]]
        config = [ConfigCheckResult(**item) for item in review["config"]]
        all_suggestions = suggest_project_checks(workspace, max_commands=100)
        all_suggested_checks = [SuggestedCheck(**item) for item in all_suggestions["checks"]]
        suggested_checks = all_suggested_checks[: action.max_checks]
        suggested_checks_total = int(all_suggestions["total"])
        all_suggested_checks_truncated = bool(all_suggestions["truncated"])
        suggested_checks_truncated = (
            all_suggested_checks_truncated
            or len(all_suggested_checks) > len(suggested_checks)
            or suggested_checks_total > len(suggested_checks)
        )
        running_processes = [process for process in list_background_processes(workspace.root).processes if process.running]
        conflict_scan = read_git_conflicts(workspace, max_markers=20, max_files=5000)
        review_scan_files = final_review_scan_file_items(workspace, list(review["files"]))
        large_files, large_files_total = find_large_changed_files(
            workspace,
            review_scan_files,
            max_bytes=FINAL_REVIEW_LARGE_FILE_BYTES,
        )
        secret_findings, secret_findings_total, secret_scan_truncated = find_secret_like_changed_files(
            workspace,
            review_scan_files,
            max_bytes=FINAL_REVIEW_SECRET_SCAN_BYTES,
        )
        secret_diff_findings, secret_diff_findings_total, secret_diff_truncated, secret_diff_warnings = find_secret_like_git_diff_additions(
            workspace,
            max_bytes=FINAL_REVIEW_SECRET_SCAN_BYTES,
        )
        nested_git_repos, nested_git_repo_total = find_nested_git_repositories(workspace)
        changed_gitlinks, changed_gitlink_total, changed_gitlink_warnings = find_changed_gitlinks(workspace)
        hidden_git_changes, hidden_git_change_total, hidden_git_change_warnings = find_hidden_tracked_git_changes(workspace)
        unsafe_symlinks, unsafe_symlink_total, unsafe_symlink_warnings, unsafe_symlink_reasons = find_unsafe_changed_symlinks(
            workspace,
            list(review["files"]),
        )
        git_operation = read_git_operation_state(workspace)
        blocking_issues: list[str] = []
        if not bool(review["changes_ok"]):
            blocking_issues.append("Could not read git changes.")
        if not bool(review["diff_check_ok"]):
            blocking_issues.append("Unstaged diff whitespace check failed.")
        if not bool(review["staged_diff_check_ok"]):
            blocking_issues.append("Staged diff whitespace check failed.")
        if not bool(review["python_ok"]):
            blocking_issues.append("Changed Python files have syntax errors.")
        if not bool(review["config_ok"]):
            blocking_issues.append("Changed config files have syntax errors.")
        if all_suggested_checks_truncated:
            blocking_issues.append("Suggested verification checks exceed the maximum readiness scan.")
        unavailable = [item for item in all_suggested_checks if not item.available]
        if unavailable:
            blocking_issues.append("Suggested verification checks have missing executables.")
        if int(review["total_files"]) > len(files):
            blocking_issues.append("Changed file review was incomplete.")
        if bool(review["python_truncated"]):
            blocking_issues.append("Python syntax check was incomplete.")
        if bool(review["config_truncated"]):
            blocking_issues.append("Config syntax check was incomplete.")
        if large_files_total:
            blocking_issues.append("Changed files include large artifacts.")
        if secret_findings_total or secret_diff_findings_total:
            blocking_issues.append("Changed files include secret-like values.")
        if secret_diff_warnings:
            blocking_issues.append("Secret-like diff scan was incomplete.")
        if nested_git_repo_total:
            blocking_issues.append("Project contains nested git repositories.")
        if changed_gitlink_total:
            blocking_issues.append("Changed files include git submodule links.")
        if changed_gitlink_warnings:
            blocking_issues.append("Git submodule link scan was incomplete.")
        if hidden_git_change_total:
            blocking_issues.append("Tracked changes are hidden by project safety filters.")
        if hidden_git_change_warnings:
            blocking_issues.append("Hidden tracked change scan was incomplete.")
        if unsafe_symlink_total:
            if "points outside project" in unsafe_symlink_reasons:
                blocking_issues.append("Changed symlinks point outside the project.")
            if "points into protected project path" in unsafe_symlink_reasons:
                blocking_issues.append("Changed symlinks point into protected project paths.")
            if "points into ignored project path" in unsafe_symlink_reasons:
                blocking_issues.append("Changed symlinks point into ignored project paths.")
        if unsafe_symlink_warnings:
            blocking_issues.append("Changed symlink scan was incomplete.")
        git_operations = list(git_operation.get("operations", [])) if bool(git_operation.get("ok")) else []
        if git_operations:
            blocking_issues.append("Git operation is still in progress.")
        elif not bool(git_operation.get("ok")):
            blocking_issues.append("Could not inspect git operation state.")
        conflict_warnings: list[str] = []
        if bool(conflict_scan.get("ok")):
            if int(conflict_scan.get("unmerged_total", 0) or 0) > 0:
                blocking_issues.append("Unmerged git files are present.")
            if int(conflict_scan.get("markers_total", 0) or 0) > 0:
                blocking_issues.append("Unresolved merge conflict markers are present.")
            marker_items = list(conflict_scan.get("markers", []))
            if marker_items:
                marker_preview = ", ".join(
                    f"{item['path']}:{item['line']} {item['marker']}" for item in marker_items[:5]
                )
                conflict_warnings.append(f"Conflict markers: {marker_preview}.")
            if bool(conflict_scan.get("truncated")):
                blocking_issues.append("Conflict marker scan was incomplete.")
                conflict_warnings.append("Conflict marker scan was truncated.")
        else:
            blocking_issues.append("Could not scan merge conflicts.")
            conflict_warnings.append(
                f"Could not scan merge conflicts: {conflict_scan.get('message') or 'unknown error'}."
            )
        verification_blockers, verification_warnings = final_review_session_verification_issues(
            workspace,
            all_suggested_checks,
        )
        blocking_issues.extend(verification_blockers)

        warnings: list[str] = []
        warnings.extend(conflict_warnings)
        if large_files:
            large_preview = ", ".join(
                f"{item['path']} ({int(item['size_bytes'])} bytes)" for item in large_files[:5]
            )
            warnings.append(
                f"Large changed file(s) over {FINAL_REVIEW_LARGE_FILE_BYTES} bytes: {large_preview}."
            )
        if large_files_total > len(large_files):
            warnings.append(f"Large changed file list truncated at {len(large_files)}/{large_files_total}.")
        if secret_findings:
            secret_preview = ", ".join(
                f"{item['path']}:{item['line']} {item['label']}" for item in secret_findings[:5]
            )
            warnings.append(f"Secret-like changed file value(s): {secret_preview}.")
        if secret_findings_total > len(secret_findings):
            warnings.append(f"Secret-like finding list truncated at {len(secret_findings)}/{secret_findings_total}.")
        if secret_scan_truncated:
            warnings.append(f"Secret scan inspected the first {FINAL_REVIEW_SECRET_SCAN_BYTES} bytes of some file(s).")
        if secret_diff_findings:
            secret_diff_preview = ", ".join(
                f"{item['path']}:{item['line']} {item['label']} ({item['source']})" for item in secret_diff_findings[:5]
            )
            warnings.append(f"Secret-like added diff value(s): {secret_diff_preview}.")
        if secret_diff_findings_total > len(secret_diff_findings):
            warnings.append(f"Secret-like diff finding list truncated at {len(secret_diff_findings)}/{secret_diff_findings_total}.")
        if secret_diff_truncated:
            warnings.append(f"Secret diff scan inspected the first {FINAL_REVIEW_SECRET_SCAN_BYTES} bytes of some diff output.")
        for warning in secret_diff_warnings[:2]:
            warnings.append(f"Could not inspect secret-like diff values: {warning}.")
        if nested_git_repos:
            warnings.append(f"Nested git repos: {', '.join(nested_git_repos[:5])}.")
        if nested_git_repo_total > len(nested_git_repos):
            warnings.append(f"Nested git repo list truncated at {len(nested_git_repos)}/{nested_git_repo_total}.")
        if changed_gitlinks:
            warnings.append(f"Git submodule links: {', '.join(changed_gitlinks[:5])}.")
        if changed_gitlink_total > len(changed_gitlinks):
            warnings.append(f"Git submodule link list truncated at {len(changed_gitlinks)}/{changed_gitlink_total}.")
        for warning in changed_gitlink_warnings[:2]:
            warnings.append(f"Could not inspect git submodule links: {warning}.")
        if hidden_git_changes:
            hidden_preview = ", ".join(
                f"{item['status']} {item['path']}" for item in hidden_git_changes[:5]
            )
            warnings.append(f"Hidden tracked change(s): {hidden_preview}.")
        if hidden_git_change_total > len(hidden_git_changes):
            warnings.append(f"Hidden tracked change list truncated at {len(hidden_git_changes)}/{hidden_git_change_total}.")
        for warning in hidden_git_change_warnings[:2]:
            warnings.append(f"Could not inspect hidden tracked changes: {warning}.")
        if unsafe_symlinks:
            symlink_preview = ", ".join(
                f"{item['path']} -> {item['target']} ({item['reason']})" for item in unsafe_symlinks[:5]
            )
            warnings.append(f"Unsafe changed symlink(s): {symlink_preview}.")
        if unsafe_symlink_total > len(unsafe_symlinks):
            warnings.append(f"Unsafe symlink list truncated at {len(unsafe_symlinks)}/{unsafe_symlink_total}.")
        for warning in unsafe_symlink_warnings[:2]:
            warnings.append(f"Could not inspect changed symlinks: {warning}.")
        if git_operations:
            operations_preview = ", ".join(str(item.get("operation", "unknown")) for item in git_operations[:5] if isinstance(item, dict))
            warnings.append(f"Git operation in progress: {operations_preview}.")
        elif not bool(git_operation.get("ok")):
            warnings.append(f"Could not inspect git operation state: {git_operation.get('message') or 'unknown error'}.")
        total_files = int(review["total_files"])
        if total_files == 0:
            warnings.append("No changed files detected.")
        if total_files > len(files):
            warnings.append(f"Changed file list truncated at {len(files)}/{total_files}.")
        if bool(review["python_truncated"]):
            warnings.append(f"Python syntax checks truncated at {len(review['python'])}/{int(review['python_total'])}.")
        if bool(review["config_truncated"]):
            warnings.append(f"Config syntax checks truncated at {len(review['config'])}/{int(review['config_total'])}.")
        if suggested_checks_truncated:
            warnings.append(f"Suggested checks truncated at {len(suggested_checks)}/{suggested_checks_total}.")
        if unavailable:
            missing = ", ".join(sorted({item.missing_tool or item.command.split()[0] for item in unavailable})[:5])
            warnings.append(f"Some suggested checks have missing executables: {missing}.")
        if running_processes:
            warnings.append(
                f"{len(running_processes)} background process(es) still running; stop them before finishing if no longer needed."
            )
        warnings.extend(verification_warnings)

        ready = bool(review["ok"]) and not blocking_issues
        if ready:
            message = f"Final review ready: {total_files} changed file(s), {suggested_checks_total} suggested check(s)."
        else:
            message = f"Final review found {len(blocking_issues)} blocking issue(s)."
        return FinalReviewObservation(
            kind="final_review",
            ok=bool(review["ok"]),
            ready=ready,
            blocking_issues=blocking_issues,
            warnings=warnings,
            running_processes=running_processes,
            files=files,
            total_files=total_files,
            python=python,
            python_total=int(review["python_total"]),
            python_truncated=bool(review["python_truncated"]),
            config=config,
            config_total=int(review["config_total"]),
            config_truncated=bool(review["config_truncated"]),
            suggested_checks=suggested_checks,
            suggested_checks_total=suggested_checks_total,
            suggested_checks_truncated=suggested_checks_truncated,
            diff_check=str(review["diff_check"]),
            staged_diff_check=str(review["staged_diff_check"]),
            status=str(review["status"]),
            message=message,
        )

    project_context_observation = execute_project_context_action(workspace, action, command_timeout_ms)
    if project_context_observation is not None:
        return project_context_observation

    if isinstance(action, CommandCheckAction):
        return build_command_check_observation(workspace, action.command, action.cwd)

    if isinstance(action, CheckRunCommandsAction):
        checks = [
            build_command_check_observation(workspace, item.command, item.cwd)
            for item in action.commands
        ]
        failed_count = sum(1 for check in checks if not check.ok)
        return CheckRunCommandsObservation(
            kind="check_run_commands",
            ok=failed_count == 0,
            checks=checks,
            message=f"Preflighted {len(checks)} command(s); {failed_count} failed.",
        )

    if isinstance(action, CheckStartCommandAction):
        result = build_command_preflight(workspace, action.command, action.cwd)
        return CheckStartCommandObservation(
            kind="check_start_command",
            ok=bool(result["ok"]),
            command=action.command,
            cwd=str(result["cwd"]),
            cwd_ok=bool(result["cwd_ok"]),
            blocked=bool(result["blocked"]),
            block_reason=result["block_reason"] if isinstance(result["block_reason"], str) else None,
            executable_available=bool(result["executable_available"]),
            missing_tool=result["missing_tool"] if isinstance(result["missing_tool"], str) else None,
            message=str(result["message"]),
        )

    if isinstance(action, PortCheckAction):
        return check_tcp_port(action.host, action.port, action.timeout_ms or 1_000)

    if isinstance(action, HttpCheckAction):
        timeout_ms = action.timeout_ms if action.timeout_ms is not None else 2_000
        max_body_chars = action.max_body_chars if action.max_body_chars is not None else 2_000
        return check_http_url(
            action.url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            contains=action.contains,
            regex=action.regex,
        )

    if isinstance(action, HttpFetchAction):
        timeout_ms = action.timeout_ms if action.timeout_ms is not None else 5_000
        max_body_chars = action.max_body_chars if action.max_body_chars is not None else 12_000
        return fetch_http_url(action.url, timeout_ms=timeout_ms, max_body_chars=max_body_chars)

    if isinstance(action, EnvironmentInfoAction):
        try:
            info = read_environment_info(workspace)
            tools = [RuntimeToolInfo(**item) for item in info["tools"]]
            return EnvironmentInfoObservation(
                kind="environment_info",
                ok=True,
                project_root=str(info["project_root"]),
                python_version=str(info["python_version"]),
                python_executable=str(info["python_executable"]),
                platform=str(info["platform"]),
                is_git_repo=bool(info["is_git_repo"]),
                tools=tools,
                message=str(info["message"]),
            )
        except ValueError as error:
            return EnvironmentInfoObservation(
                kind="environment_info",
                ok=False,
                project_root=workspace.root.as_posix(),
                python_version="",
                python_executable="",
                platform="",
                is_git_repo=False,
                tools=[],
                message=str(error),
            )

    session_observation = execute_session_action(workspace, action)
    if session_observation is not None:
        return session_observation

    if isinstance(action, CheckpointCreateAction):
        return create_checkpoint_observation(workspace, action.label)

    if isinstance(action, CheckpointListAction):
        return list_checkpoints_observation(workspace.root, action.max_entries)

    if isinstance(action, CheckpointShowAction):
        return checkpoint_show_observation(workspace.root, action.checkpoint_id)

    if isinstance(action, CheckpointDiffAction):
        return checkpoint_diff_observation(workspace.root, action.checkpoint_id, action.max_chars)

    if isinstance(action, CheckpointStatusAction):
        return checkpoint_status_observation(workspace, action.checkpoint_id)

    if isinstance(action, CheckCheckpointRestoreAction):
        return check_checkpoint_restore_observation(workspace, action.checkpoint_id)

    if isinstance(action, CheckpointRestoreAction):
        return checkpoint_restore_observation(workspace, action.checkpoint_id)

    if isinstance(action, CheckCheckpointDeleteAction):
        return check_checkpoint_delete_observation(workspace.root, action.checkpoint_id)

    if isinstance(action, CheckpointDeleteAction):
        return checkpoint_delete_observation(workspace.root, action.checkpoint_id)

    if isinstance(action, CheckCheckpointPruneAction):
        return check_checkpoint_prune_observation(workspace.root, action.keep_last)

    if isinstance(action, CheckpointPruneAction):
        return checkpoint_prune_observation(workspace.root, action.keep_last)

    file_observation = execute_file_action(workspace, action)
    if file_observation is not None:
        return file_observation

    if isinstance(action, RunCommandAction):
        return RunCommandObservation(
            kind="run_command",
            result=execute_run_command_item(workspace, action, command_timeout_ms),
        )

    if isinstance(action, RunCommandsAction):
        results: list[CommandResult] = []
        stopped_early = False
        for item in action.commands:
            result = execute_run_command_item(workspace, item, command_timeout_ms)
            results.append(result)
            failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
            if failed and action.stop_on_failure:
                stopped_early = len(results) < len(action.commands)
                break
        ok = len(results) == len(action.commands) and all(
            result.exit_code == 0 and not result.timed_out for result in results
        )
        return RunCommandsObservation(
            kind="run_commands",
            results=results,
            ok=ok,
            stopped_early=stopped_early,
            message=f"Ran {len(results)}/{len(action.commands)} command(s); {'all passed' if ok else 'one or more failed'}.",
        )

    if isinstance(action, StartCommandAction):
        return start_background_command(workspace, action.command, action.cwd)

    if isinstance(action, ReadProcessAction):
        return attach_output_analysis_to_process_observation(
            workspace,
            read_background_process(workspace.root, action.process_id, max_output_chars=action.max_output_chars or 4_000),
        )

    if isinstance(action, ProcessOutputContextsAction):
        return read_background_process_output_contexts(workspace, action)

    if isinstance(action, ProcessOutputDiagnosticsAction):
        return read_background_process_output_diagnostics(workspace, action)

    if isinstance(action, WaitProcessAction):
        return attach_output_analysis_to_process_observation(
            workspace,
            wait_background_process(
                workspace.root,
                action.process_id,
                timeout_ms=action.timeout_ms or 5_000,
                stdout_contains=action.stdout_contains,
                stderr_contains=action.stderr_contains,
                regex=action.regex,
                max_output_chars=action.max_output_chars or 4_000,
            ),
        )

    if isinstance(action, CheckWriteProcessAction):
        return check_write_background_process(workspace.root, action.process_id, action.content)

    if isinstance(action, WriteProcessAction):
        return write_background_process(workspace.root, action.process_id, action.content)

    if isinstance(action, ListProcessesAction):
        return list_background_processes(workspace.root)

    if isinstance(action, CheckStopAllProcessesAction):
        return check_stop_all_background_processes(workspace.root)

    if isinstance(action, CheckStopProcessAction):
        return check_stop_background_process(workspace.root, action.process_id)

    if isinstance(action, StopAllProcessesAction):
        return stop_all_background_processes(workspace.root)

    if isinstance(action, StopProcessAction):
        return stop_background_process(workspace.root, action.process_id)

    if isinstance(action, UpdatePlanAction):
        return UpdatePlanObservation(
            kind="update_plan",
            plan=action.plan,
            message=summarize_plan_update(action),
        )

    return FinishObservation(kind="finish", message=action.message)
