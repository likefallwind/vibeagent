from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .types import (
    AgentAction,
    AppendFileAction,
    AppendFileObservation,
    CheckAppendFileAction,
    CheckAppendFileObservation,
    CheckCheckpointDeleteAction,
    CheckCheckpointDeleteObservation,
    CheckCheckpointPruneAction,
    CheckCheckpointPruneObservation,
    CheckCheckpointRestoreAction,
    CheckCheckpointRestoreObservation,
    CheckCreateDirectoryAction,
    CheckCreateDirectoryObservation,
    CheckCreateDirectoriesAction,
    CheckCreateDirectoriesObservation,
    CheckCopyDirectoryAction,
    CheckCopyDirectoryObservation,
    CheckCopyDirectoriesAction,
    CheckCopyDirectoriesObservation,
    CheckCopyFileAction,
    CheckCopyFileObservation,
    CheckCopyFilesAction,
    CheckCopyFilesObservation,
    CheckDeleteFileAction,
    CheckDeleteFileObservation,
    CheckDeleteFilesAction,
    CheckDeleteFilesObservation,
    CheckDeleteEmptyDirectoryAction,
    CheckDeleteEmptyDirectoryObservation,
    CheckDeleteEmptyDirectoriesAction,
    CheckDeleteEmptyDirectoriesObservation,
    CheckEditFileAction,
    CheckEditFileObservation,
    CheckGitCommitAction,
    CheckGitCommitObservation,
    CheckGitFetchAction,
    CheckGitFetchObservation,
    CheckGitPullAction,
    CheckGitPullObservation,
    CheckGitPushAction,
    CheckGitPushObservation,
    CheckGitRestoreAction,
    CheckGitRestoreObservation,
    CheckGitStashAction,
    CheckGitStashApplyAction,
    CheckGitStashApplyObservation,
    CheckGitStashDropAction,
    CheckGitStashDropObservation,
    CheckGitStashObservation,
    CheckGitStageAction,
    CheckGitStageObservation,
    CheckGitSwitchAction,
    CheckGitSwitchObservation,
    CheckGitUnstageAction,
    CheckGitUnstageObservation,
    CheckInsertLinesAction,
    CheckInsertLinesObservation,
    CheckJsonRemoveAction,
    CheckJsonRemoveObservation,
    CheckJsonPatchAction,
    CheckJsonPatchObservation,
    CheckJsonSetAction,
    CheckJsonSetObservation,
    CheckPatchAction,
    CheckPatchObservation,
    CheckPatchesAction,
    CheckPatchesObservation,
    CheckMultiEditAction,
    CheckMultiEditObservation,
    CheckMoveDirectoryAction,
    CheckMoveDirectoryObservation,
    CheckMoveDirectoriesAction,
    CheckMoveDirectoriesObservation,
    CheckMoveFileAction,
    CheckMoveFileObservation,
    CheckMoveFilesAction,
    CheckMoveFilesObservation,
    CheckReplaceLinesAction,
    CheckReplaceLinesObservation,
    CheckReplacePythonDefinitionAction,
    CheckReplacePythonDefinitionObservation,
    CheckRegexReplaceAction,
    CheckRegexReplaceObservation,
    CheckStartCommandAction,
    CheckStartCommandObservation,
    CheckStopAllProcessesAction,
    CheckStopAllProcessesObservation,
    CheckStopProcessAction,
    CheckStopProcessObservation,
    CheckWriteProcessAction,
    CheckWriteProcessObservation,
    CheckFocusedTestCommandsAction,
    CheckFocusedTestCommandsObservation,
    CheckpointCreateAction,
    CheckpointCreateObservation,
    CheckpointInfo,
    CheckpointDiffAction,
    CheckpointDiffObservation,
    CheckpointListAction,
    CheckpointListObservation,
    CheckpointDeleteAction,
    CheckpointDeleteObservation,
    CheckpointPruneAction,
    CheckpointPruneObservation,
    CheckpointRestoreAction,
    CheckpointRestoreObservation,
    CheckpointShowAction,
    CheckpointShowObservation,
    CheckpointStatusAction,
    CheckpointStatusObservation,
    CheckWriteFileAction,
    CheckWriteFileObservation,
    CheckWriteFileResult,
    CheckWriteFilesAction,
    CheckWriteFilesObservation,
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
    CodeRenamePreviewFile,
    CodeRenamePreviewObservation,
    CodeRenameReplacement,
    CopyFileAction,
    CopyFileObservation,
    CopyFilesAction,
    CopyFilesObservation,
    CopyDirectoryAction,
    CopyDirectoryObservation,
    CopyDirectoriesAction,
    CopyDirectoriesObservation,
    DirectoryTransfer,
    MoveDirectoryAction,
    MoveDirectoryObservation,
    MoveDirectoriesAction,
    MoveDirectoriesObservation,
    CreateDirectoryAction,
    CreateDirectoryObservation,
    CreateDirectoriesAction,
    CreateDirectoriesObservation,
    CommandCheckAction,
    CommandCheckObservation,
    CommandResult,
    CheckRunCommandsAction,
    CheckRunCommandsObservation,
    CodeOutlineAction,
    CodeOutlineObservation,
    CodeOutlineResult,
    ConfigCheckAction,
    ConfigCheckObservation,
    ConfigCheckResult,
    DeleteEmptyDirectoryAction,
    DeleteEmptyDirectoryObservation,
    DeleteEmptyDirectoriesAction,
    DeleteEmptyDirectoriesObservation,
    DeleteFileAction,
    DeleteFileObservation,
    DeleteFilesAction,
    DeleteFilesObservation,
    EditFileAction,
    EditFileObservation,
    EditOperation,
    EnvironmentInfoAction,
    EnvironmentInfoObservation,
    FinalReviewAction,
    FinalReviewObservation,
    FinishAction,
    FinishObservation,
    FileInfoAction,
    FileInfoObservation,
    FileInfoResult,
    ImageInfoAction,
    ImageInfoObservation,
    ImageInfoResult,
    GlobAction,
    GlobObservation,
    GitBlameAction,
    GitBlameObservation,
    GitBranchInfo,
    GitBranchesAction,
    GitBranchesObservation,
    GitChangeFile,
    GitChangesAction,
    GitChangesObservation,
    GitConflictMarker,
    GitConflictStatus,
    GitConflictsAction,
    GitConflictsObservation,
    GitCommitAction,
    GitCommitObservation,
    GitDiffAction,
    GitDiffContext,
    GitDiffContextsAction,
    GitDiffContextsObservation,
    GitDiffHunk,
    GitDiffHunksAction,
    GitDiffHunksObservation,
    GitDiffObservation,
    GitFetchAction,
    GitFetchObservation,
    GitPullAction,
    GitPullObservation,
    GitPushAction,
    GitPushObservation,
    GitRestoreAction,
    GitRestoreObservation,
    GitStashAction,
    GitStashApplyAction,
    GitStashApplyObservation,
    GitStashDropAction,
    GitStashDropObservation,
    GitStashEntry,
    GitStashesAction,
    GitStashesObservation,
    GitStashObservation,
    GitInfoAction,
    GitInfoObservation,
    GitLogAction,
    GitLogObservation,
    GitRemote,
    GitShowAction,
    GitShowObservation,
    GitStageAction,
    GitStageObservation,
    GitStatusAction,
    GitStatusObservation,
    GitSwitchAction,
    GitSwitchObservation,
    GitUnstageAction,
    GitUnstageObservation,
    HttpCheckAction,
    HttpCheckObservation,
    HttpFetchAction,
    HttpFetchObservation,
    InsertLinesAction,
    InsertLinesObservation,
    JsonRemoveAction,
    JsonRemoveObservation,
    JsonPatchAction,
    JsonPatchObservation,
    JsonPatchOperation,
    JsonSetAction,
    JsonSetObservation,
    ListProcessesAction,
    ListProcessesObservation,
    ListFilesAction,
    ListFilesObservation,
    ListTreeAction,
    ListTreeObservation,
    MultiEditAction,
    MultiEditObservation,
    Observation,
    OutputContextResult,
    OutputContextsAction,
    OutputContextsObservation,
    OutputDiagnostic,
    OutputDiagnosticsAction,
    OutputDiagnosticsObservation,
    PatchFileAction,
    PatchFileObservation,
    PatchFilesAction,
    PatchFilesObservation,
    PlanItem,
    PortCheckAction,
    PortCheckObservation,
    ProcessInfo,
    ProcessOutputContextsAction,
    ProcessOutputContextsObservation,
    ProcessOutputDiagnosticsAction,
    ProcessOutputDiagnosticsObservation,
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
    PythonRenamePreviewFile,
    PythonRenamePreviewObservation,
    PythonRenameReplacement,
    ReferenceContextResult,
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
    ReadFileContextItem,
    ReadFileContextObservation,
    ReadFileContextResult,
    ReadFileContextsAction,
    ReadFileContextsObservation,
    ReadFileObservation,
    ReadFileResult,
    ReadFilesAction,
    ReadFilesObservation,
    ReadFileRangeItem,
    ReadFileRangeResult,
    ReadFileRangesAction,
    ReadFileRangesObservation,
    ReadProcessAction,
    ReadProcessObservation,
    RegexReplaceAction,
    RegexReplaceObservation,
    ReplaceLinesAction,
    ReplaceLinesObservation,
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
    SessionCommandsAction,
    SessionCommandsObservation,
    SessionFilesAction,
    SessionFilesObservation,
    SessionFailuresAction,
    SessionFailuresObservation,
    SessionVerificationAction,
    SessionVerificationObservation,
    SessionAuditAction,
    SessionAuditObservation,
    SessionAuditProcess,
    SessionHandoffAction,
    SessionHandoffObservation,
    SessionOutputContextsAction,
    SessionOutputContextsObservation,
    SessionOutputDiagnosticsAction,
    SessionOutputDiagnosticsObservation,
    SessionPlanAction,
    SessionPlanObservation,
    SessionSearchAction,
    SessionSearchObservation,
    SessionSummaryAction,
    SessionSummaryObservation,
    SessionTranscriptAction,
    SessionTranscriptObservation,
    CheckSetExecutableAction,
    CheckSetExecutableObservation,
    SetExecutableAction,
    SetExecutableObservation,
    StartCommandAction,
    StartCommandObservation,
    StopAllProcessesAction,
    StopAllProcessesObservation,
    StopProcessAction,
    StopProcessObservation,
    StoppedProcessInfo,
    SuggestedCheck,
    SuggestChecksAction,
    SuggestChecksObservation,
    TailFileAction,
    TailFileObservation,
    UntrackedFilePreview,
    UpdatePlanAction,
    UpdatePlanObservation,
    WaitProcessAction,
    WaitProcessObservation,
    WriteFileAction,
    WriteFileItem,
    WriteFileObservation,
    WriteFileResult,
    WriteFilesAction,
    WriteFilesObservation,
    WriteProcessAction,
    WriteProcessObservation,
    MoveFileAction,
    MoveFileTransfer,
    MoveFileObservation,
    MoveFilesAction,
    MoveFilesObservation,
)
from .session import command_output_tail, format_session_audit, format_session_commands, format_session_failures, format_session_files, format_session_handoff, format_session_plan, format_session_search, format_session_summary, format_session_transcript, format_session_verification, format_sessions, read_session_events, session_audit_blockers, session_command_entries, session_dir, session_failure_entries, session_file_entries, summarize_session
from .workspace import (
    RunWorkspace,
    append_project_file,
    build_repo_map,
    check_project_patch,
    check_project_patches,
    commit_staged_changes,
    create_project_directory,
    create_project_directories,
    delete_project_empty_directory,
    delete_project_empty_directories,
    delete_project_file,
    delete_project_files,
    edit_project_file,
    list_project_files,
    list_project_tree,
    copy_project_file,
    copy_project_files,
    copy_project_directory,
    copy_project_directories,
    json_patch_project_file,
    json_remove_project_file,
    json_set_project_file,
    move_project_directory,
    move_project_directories,
    move_project_file,
    move_project_files,
    multi_edit_project_file,
    patch_project_file,
    patch_project_files,
    apply_code_rename,
    apply_python_rename,
    preview_code_rename,
    preview_python_rename,
    preview_multi_edit_project_file,
    preview_append_project_file,
    preview_create_project_directory,
    preview_create_project_directories,
    preview_copy_project_directory,
    preview_copy_project_directories,
    preview_copy_project_file,
    preview_copy_project_files,
    preview_delete_project_empty_directory,
    preview_delete_project_empty_directories,
    preview_delete_project_file,
    preview_delete_project_files,
    preview_insert_project_file_lines,
    preview_json_patch_project_file,
    preview_json_remove_project_file,
    preview_json_set_project_file,
    preview_move_project_directory,
    preview_move_project_directories,
    preview_move_project_file,
    preview_move_project_files,
    preview_replace_project_file_lines,
    preview_regex_replace_project_file,
    preview_commit_staged_changes,
    preview_fetch_git_remote,
    preview_pull_git_upstream,
    preview_push_git_upstream,
    preview_restore_git_paths,
    preview_stash_git_changes,
    preview_apply_git_stash,
    preview_drop_git_stash,
    preview_stage_git_paths,
    preview_switch_git_branch,
    preview_unstage_git_paths,
    preview_write_run_file,
    preview_write_run_files,
    read_git_changes,
    read_git_conflicts,
    read_git_branches,
    read_git_diff,
    read_git_diff_hunks,
    read_git_info,
    find_python_references,
    find_code_references,
    find_code_definitions,
    find_python_definitions,
    find_python_calls,
    inspect_python_call_graph,
    read_git_blame,
    read_environment_info,
    read_git_log,
    read_git_show,
    read_git_status,
    read_project_file_info,
    read_project_image_info,
    set_project_file_executable,
    preview_set_project_file_executable,
    insert_project_file_lines,
    read_project_file,
    read_project_file_context_result,
    read_project_file_result,
    read_project_file_tail_result,
    read_output_contexts_result,
    read_output_diagnostics_result,
    regex_replace_project_file,
    find_related_tests,
    suggest_focused_test_commands,
    read_project_commands,
    read_project_instruction_sources,
    read_project_manifests,
    read_project_todos,
    read_code_outline,
    read_python_symbol_outline,
    replace_project_file_lines,
    preview_replace_python_definition,
    review_project_changes,
    replace_python_definition,
    resolve_command_cwd,
    glob_project_files,
    inspect_code_dependencies,
    inspect_python_dependencies,
    missing_command_tool,
    preview_edit_project_file,
    search_project_contexts_result,
    search_project_result,
    check_config_syntax,
    check_python_syntax,
    stage_git_paths,
    switch_git_branch,
    fetch_git_remote,
    pull_git_upstream,
    push_git_upstream,
    restore_git_paths,
    read_git_stashes,
    stash_git_changes,
    apply_git_stash,
    drop_git_stash,
    suggest_project_checks,
    unstage_git_paths,
    write_run_file,
    write_run_files,
)


PROJECT_CHANGE_RESULT_KINDS = {
    "write_file",
    "write_files",
    "edit_file",
    "multi_edit_file",
    "replace_python_definition",
    "code_rename",
    "python_rename",
    "replace_lines",
    "insert_lines",
    "append_file",
    "regex_replace",
    "json_set",
    "json_remove",
    "json_patch",
    "patch_file",
    "patch_files",
    "delete_file",
    "delete_files",
    "move_file",
    "move_files",
    "copy_file",
    "copy_files",
    "move_dir",
    "move_dirs",
    "copy_dir",
    "copy_dirs",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "set_executable",
    "git_stage",
    "git_unstage",
    "git_commit",
    "git_restore",
    "checkpoint_restore",
}


class ActionParseError(ValueError):
    def __init__(self, message: str, raw: str):
        super().__init__(message)
        self.raw = raw


@dataclass
class BackgroundProcess:
    id: str
    command: str
    cwd: str
    process: subprocess.Popen[str]
    stdout_path: Path
    stderr_path: Path
    exit_code_path: Path
    stdout_handle: Any
    stderr_handle: Any


@dataclass(frozen=True)
class PersistentProcessRecord:
    id: str
    command: str
    cwd: str
    pid: int
    stdout_path: Path
    stderr_path: Path
    exit_code_path: Path | None = None
    start_ticks: int | None = None


BACKGROUND_PROCESSES: dict[str, BackgroundProcess] = {}
CHECKPOINT_UNTRACKED_SHOW_LIMIT = 50


AGENT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "list_files",
        "description": "List project files, optionally under a relative path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Optional relative path to list."}},
            "additionalProperties": False,
        },
    },
    {
        "name": "list_tree",
        "description": "List a shallow project directory tree with directories and files, optionally under one relative path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional relative directory or file path to list."},
                "max_depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum directory depth to include from the requested path. Defaults to 3.",
                },
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum entries to return. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "repo_map",
        "description": "Build a bounded project overview with directory tree, file list, and source import/symbol outlines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum directory depth to include. Defaults to 3.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum file and tree entry count to include. Defaults to 80.",
                },
                "max_symbols": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python symbol count across mapped files. Defaults to 120.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file from the project, optionally starting at a 1-based line number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional 1-based first line to read.",
                },
                "line_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Optional number of lines to read when start_line is provided. Defaults to 200.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum full-file characters to return when start_line is not provided. Defaults to 20000.",
                },
            },
            "required": ["path"],
            "dependentRequired": {"line_count": ["start_line"]},
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file_context",
        "description": "Read a focused line with surrounding context from a UTF-8 project text file, useful for stack traces and test failures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "1-based target line number to center in the excerpt.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines to include before and after the target line. Defaults to 20.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned from the focused context. Defaults to 20000.",
                },
            },
            "required": ["path", "line"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file_contexts",
        "description": "Read several focused file:line contexts in one call, useful for stack traces and multi-file test or lint failures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contexts": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Project-relative file path to read."},
                            "line": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "1-based target line number to center in the excerpt.",
                            },
                            "context_lines": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 500,
                                "description": "Lines to include before and after the target line. Defaults to 20.",
                            },
                        },
                        "required": ["path", "line"],
                        "additionalProperties": False,
                    },
                    "description": "Project-relative file line contexts to read.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per context. Defaults to 20000.",
                },
            },
            "required": ["contexts"],
            "additionalProperties": False,
        },
    },
    {
        "name": "output_contexts",
        "description": "Extract project file:line references from command, test, lint, or traceback output and read their surrounding contexts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Command or tool output containing references such as path:line[:column] or Python traceback File entries.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines to include before and after each referenced line. Defaults to 5.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to read. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per context. Defaults to 20000.",
                },
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "output_diagnostics",
        "description": "Summarize error, warning, failure, Python traceback, and file:line diagnostic lines from command/test/lint output, and include source contexts for referenced project files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Command or tool output to summarize.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines to include before and after each referenced source line. Defaults to 2.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic lines to include. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum referenced source contexts to read. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per context. Defaults to 20000.",
                },
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_traceback",
        "description": "Summarize Python traceback or pytest exception output, including exception summary lines and source contexts for traceback frames inside the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Python traceback, pytest failure, or command output containing Python exception details.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines to include before and after each referenced source line. Defaults to 2.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic lines to include. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum referenced source contexts to read. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per context. Defaults to 20000.",
                },
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "tail_file",
        "description": "Read the last lines of a UTF-8 text file from the project, useful for logs and long generated outputs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Number of trailing lines to read. Defaults to 80.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned from the file tail. Defaults to 20000.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_files",
        "description": "Read multiple UTF-8 text files from the project in one tool call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative file paths to read.",
                },
                "max_bytes_per_file": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per file. Defaults to 20000.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file_ranges",
        "description": "Read focused line ranges from one or more UTF-8 text files in one tool call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ranges": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Project-relative file path to read."},
                            "start_line": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "1-based first line to read.",
                            },
                            "line_count": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 1000,
                                "description": "Number of lines to read. Defaults to 120.",
                            },
                        },
                        "required": ["path", "start_line"],
                        "additionalProperties": False,
                    },
                    "description": "Project-relative file line ranges to read.",
                },
                "max_bytes_per_range": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per range. Defaults to 20000.",
                },
            },
            "required": ["ranges"],
            "additionalProperties": False,
        },
    },
    {
        "name": "file_info",
        "description": "Inspect project paths without reading full content. Returns existence, type, byte size, text line count, and binary detection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {"type": "string"},
                    "description": "Project-relative file or directory paths to inspect.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "image_info",
        "description": "Inspect project-relative PNG, JPEG, GIF, or WebP image files without reading full binary payload. Returns format, byte size, and dimensions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative image file paths to inspect.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_symbols",
        "description": "Read a Python source outline without executing code. Returns imports and class/function definitions with line numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative .py file paths to inspect.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_outline",
        "description": "Read a lightweight source outline for Python, JavaScript/TypeScript, Go, Rust, Java/Kotlin, C, or C++ files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string"},
                    "description": "Project-relative source file paths to inspect.",
                },
                "max_symbols": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum symbol count per file. Defaults to 200.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_check",
        "description": "Check Python files for syntax errors without executing code, optionally scoped to one project-relative file or directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to check. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "config_check",
        "description": "Check JSON and TOML config files for syntax errors without executing project code, optionally scoped to one project-relative file or directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative JSON/TOML file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum config file count to check. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_json_set",
        "description": "Preview setting one value in an existing project JSON file using a JSON Pointer without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to set, such as /scripts/dev or /compilerOptions/strict."},
                "value": {
                    "description": "JSON value to write at the pointer.",
                    "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                },
                "create_missing": {
                    "type": "boolean",
                    "description": "Create missing object keys along the pointer when true. Defaults to false.",
                },
            },
            "required": ["path", "pointer", "value"],
            "additionalProperties": False,
        },
    },
    {
        "name": "json_set",
        "description": "Set one value in an existing project JSON file using a JSON Pointer after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to set, such as /scripts/dev or /compilerOptions/strict."},
                "value": {
                    "description": "JSON value to write at the pointer.",
                    "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                },
                "create_missing": {
                    "type": "boolean",
                    "description": "Create missing object keys along the pointer when true. Defaults to false.",
                },
            },
            "required": ["path", "pointer", "value"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_json_remove",
        "description": "Preview removing one object key or array item from an existing project JSON file using a JSON Pointer without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to remove, such as /scripts/dev or /keywords/0."},
            },
            "required": ["path", "pointer"],
            "additionalProperties": False,
        },
    },
    {
        "name": "json_remove",
        "description": "Remove one object key or array item from an existing project JSON file using a JSON Pointer after approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "pointer": {"type": "string", "description": "JSON Pointer to remove, such as /scripts/dev or /keywords/0."},
            },
            "required": ["path", "pointer"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_json_patch",
        "description": "Preview applying multiple JSON Patch operations to one existing project JSON file without changing files. Supports add, replace, and remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "operations": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "oneOf": [
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["add", "replace"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                    "value": {
                                        "description": "JSON value for add or replace operations.",
                                        "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                                    },
                                },
                                "required": ["op", "path", "value"],
                                "additionalProperties": False,
                            },
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["remove"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                },
                                "required": ["op", "path"],
                                "additionalProperties": False,
                            },
                        ],
                    },
                },
            },
            "required": ["path", "operations"],
            "additionalProperties": False,
        },
    },
    {
        "name": "json_patch",
        "description": "Apply multiple JSON Patch operations to one existing project JSON file after approval. Supports add, replace, and remove, and validates all operations before writing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative JSON file path."},
                "operations": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "oneOf": [
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["add", "replace"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                    "value": {
                                        "description": "JSON value for add or replace operations.",
                                        "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                                    },
                                },
                                "required": ["op", "path", "value"],
                                "additionalProperties": False,
                            },
                            {
                                "properties": {
                                    "op": {"type": "string", "enum": ["remove"]},
                                    "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                                },
                                "required": ["op", "path"],
                                "additionalProperties": False,
                            },
                        ],
                    },
                },
            },
            "required": ["path", "operations"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_dependencies",
        "description": "Inspect Python imports without executing code, classifying local project modules versus external modules.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_imports": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum import entries to return across files. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "code_dependencies",
        "description": "Inspect imports, includes, and use statements in JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, and C++ files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_imports": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum import/include/use entries to return across files. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "code_references",
        "description": "Find bounded references to one symbol or literal in JavaScript, TypeScript, Go, Rust, Java, Kotlin, C, and C++ source files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to search for."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum reference count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_reference_contexts",
        "description": "Find non-Python source references and return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to search for."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 50.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each reference. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_definitions",
        "description": "Find non-Python source definitions by exact symbol name and return focused source excerpts without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Exact symbol name to inspect."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum definition count to return. Defaults to 50.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source lines to return per definition. Defaults to 80.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_rename_preview",
        "description": "Preview a bounded non-Python source symbol or literal rename using lexical reference matching without writing changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to rename."},
                "new_name": {"type": "string", "description": "Replacement symbol or single-line literal."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to include in diffs. Defaults to 500.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "code_rename",
        "description": "Apply a bounded non-Python source symbol or literal rename using lexical reference matching.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol or single-line literal to rename."},
                "new_name": {"type": "string", "description": "Replacement symbol or single-line literal."},
                "path": {"type": "string", "description": "Optional project-relative source file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum source file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to apply. Defaults to 2000.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_definitions",
        "description": "Find Python class/function definitions and return focused source excerpts without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python identifier or dotted identifier to inspect, such as run_agent or Runner.run.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum definition count to return. Defaults to 50.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum source lines to include for each definition. Defaults to 120.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_replace_python_definition",
        "description": "Validate replacing exactly one Python class/function definition by symbol without changing files. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python definition name or dotted qualified name, such as run_agent or Runner.run.",
                },
                "content": {
                    "type": "string",
                    "description": "Replacement source text for the full definition, with indentation appropriate for its location.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
            },
            "required": ["symbol", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "replace_python_definition",
        "description": "Replace exactly one Python class/function definition by symbol after validating the resulting file parses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python definition name or dotted qualified name, such as run_agent or Runner.run.",
                },
                "content": {
                    "type": "string",
                    "description": "Replacement source text for the full definition, with indentation appropriate for its location.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
            },
            "required": ["symbol", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_calls",
        "description": "Find Python call sites for a function, method, or dotted callable name without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Python callable name to find, such as run_agent, self.run, or client.complete.",
                },
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum call site count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_call_graph",
        "description": "Inspect Python caller-to-callee edges in a file or directory without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_edges": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum call graph edge count to return. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "python_references",
        "description": "Find Python definitions, imports, and AST references for one identifier without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Python identifier to find, such as Client or run_agent."},
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum reference count to return. Defaults to 200.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_reference_contexts",
        "description": "Find Python definitions, imports, and AST references, then return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Python identifier to find, such as Client or run_agent."},
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 50.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each reference. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_rename_preview",
        "description": "Preview an AST-guided Python identifier rename across files without writing changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Simple Python identifier to rename."},
                "new_name": {"type": "string", "description": "Replacement simple Python identifier."},
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to include in diffs. Defaults to 500.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "python_rename",
        "description": "Apply an AST-guided Python identifier rename across files after validating updated files parse.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Simple Python identifier to rename."},
                "new_name": {"type": "string", "description": "Replacement simple Python identifier."},
                "path": {"type": "string", "description": "Optional project-relative Python file or directory scope."},
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum Python file count to inspect. Defaults to 100.",
                },
                "max_replacements": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum replacement count to apply. Defaults to 2000.",
                },
            },
            "required": ["symbol", "new_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search",
        "description": "Search project text for an exact query string or regex, optionally under one path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "description": "Optional project-relative file or directory to search."},
                "regex": {"type": "boolean", "description": "Treat query as a regular expression."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum match count to return. Defaults to 80.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Number of surrounding lines to include around each match. Defaults to 0.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_contexts",
        "description": "Search project text and return structured line-centered context snippets for each match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string", "description": "Optional project-relative file or directory to search."},
                "regex": {"type": "boolean", "description": "Treat query as a regular expression."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum context count to return. Defaults to 20.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Number of surrounding lines to include around each match. Defaults to 3.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per context snippet. Defaults to 20000.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "glob",
        "description": "Find project files by relative glob pattern, such as **/*.py or tests/test_*.py.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum match count to return. Defaults to 200.",
                },
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_status",
        "description": "Read git status in short format for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_conflicts",
        "description": "Scan for merge/rebase conflicts by reading unmerged git index entries and conflict marker lines in project text files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative file or directory to scan."},
                "max_markers": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum conflict marker entries to return. Defaults to 200.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10000,
                    "description": "Maximum project text files to scan for conflict markers. Defaults to 5000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_info",
        "description": "Read git repository identity and collaboration state: branch, HEAD, upstream, ahead/behind counts, remotes, and short status. Does not fetch from the network.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_changes",
        "description": "Read a structured summary of changed git files, including status and staged/unstaged insertion/deletion counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_branches",
        "description": "List local git branches and the current branch without fetching from the network.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_branches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum local branch count to return. Defaults to 100.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_fetch",
        "description": "Validate which git remote would be fetched and report current ahead/behind state without contacting the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name to fetch, such as origin. If omitted, the single configured remote is selected.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_fetch",
        "description": "Run git fetch --prune for one configured remote. Requires approval and may contact the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "remote": {
                    "type": "string",
                    "description": "Remote name to fetch, such as origin. If omitted, the single configured remote is selected.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_pull",
        "description": "Validate whether the current branch can be updated from its upstream with git pull --ff-only without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_pull",
        "description": "Update the current branch from its configured upstream using git pull --ff-only. Requires approval, a clean worktree, and no divergent local commits.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_push",
        "description": "Validate whether the current branch can be pushed to its configured upstream without changing local or remote refs.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_push",
        "description": "Push the current branch to its configured upstream. Requires approval, a clean worktree, ahead commits, and no cached behind state. Does not force push.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_switch",
        "description": "Validate switching to an existing local branch or creating a new local branch without changing HEAD.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Local branch name to switch to or create."},
                "create": {
                    "type": "boolean",
                    "description": "Create the branch with git switch -c when true. Defaults to false.",
                },
            },
            "required": ["branch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_switch",
        "description": "Switch to an existing local branch, or create and switch to a new local branch. Requires approval and a clean worktree.",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Local branch name to switch to or create."},
                "create": {
                    "type": "boolean",
                    "description": "Create the branch with git switch -c when true. Defaults to false.",
                },
            },
            "required": ["branch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stage",
        "description": "Validate staging one or more project-relative paths without changing the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to stage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stage",
        "description": "Stage one or more project-relative paths in the git index. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to stage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_unstage",
        "description": "Validate unstaging one or more project-relative paths without changing the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to unstage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_unstage",
        "description": "Unstage one or more project-relative paths from the git index. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Project-relative paths to unstage, such as src/app.py or tests.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_restore",
        "description": "Preview discarding unstaged changes for tracked project-relative paths without changing files or the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Tracked project-relative paths whose unstaged changes would be restored from HEAD.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_restore",
        "description": "Discard unstaged changes for tracked project-relative paths with git restore. Requires approval. Does not delete untracked files or change the git index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string"},
                    "description": "Tracked project-relative paths whose unstaged changes should be restored from HEAD.",
                },
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stashes",
        "description": "List recent git stash entries without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum stash entry count to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stash",
        "description": "Preview saving current non-runtime changes to git stash without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Optional stash message. Defaults to 'vibeagent stash'."},
                "include_untracked": {
                    "type": "boolean",
                    "description": "Also stash non-runtime untracked files. Defaults to false.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stash",
        "description": "Save current non-runtime changes to git stash. Requires approval. Excludes .vibeagent runtime files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Optional stash message. Defaults to 'vibeagent stash'."},
                "include_untracked": {
                    "type": "boolean",
                    "description": "Also stash non-runtime untracked files. Defaults to false.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stash_apply",
        "description": "Preview applying one stash entry to a clean worktree without changing files or dropping the stash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stash_apply",
        "description": "Apply one stash entry to a clean worktree. Requires approval. Does not drop the stash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_stash_drop",
        "description": "Preview dropping one stash entry without changing the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_stash_drop",
        "description": "Drop one stash entry after approval. This permanently removes the stash entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stash_ref": {"type": "string", "description": "Stash reference such as stash@{0}."},
            },
            "required": ["stash_ref"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_git_commit",
        "description": "Validate that currently staged changes can be committed with the provided message without creating a commit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message to validate.",
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "git_commit",
        "description": "Commit currently staged changes with a message. Uses --no-verify and does not run git hooks. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message, up to 500 characters.",
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "review_changes",
        "description": "Run a read-only pre-final review: structured changed files, git diff whitespace checks, and Python syntax checks for changed Python files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum changed file and Python file count to report. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "final_review",
        "description": "Run a read-only final handoff review that summarizes blocking issues, warnings, changed files, and suggested verification commands before finishing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum changed file count to report. Defaults to 200.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum suggested verification command count to report. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "suggest_checks",
        "description": "Suggest relevant test, build, lint, and syntax-check commands from project metadata and current changed files without running them, including whether each command's main executable is available on PATH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum suggested command count to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_suggested_checks",
        "description": "Preflight the project's suggested test, build, lint, and syntax-check commands without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum suggested command count to preflight. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "run_suggested_checks",
        "description": "Run the project's available suggested test, build, lint, and syntax-check commands after approval. Stops at the first failure by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum suggested command count to run. Defaults to 10.",
                },
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional timeout in milliseconds per command. Defaults to the agent command timeout.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Stop after the first failing command. Defaults to true.",
                },
                "extract_output_contexts": {
                    "type": "boolean",
                    "description": "When true, extract file:line references from stdout/stderr and include source context for each reference. Defaults to false.",
                },
                "extract_output_diagnostics": {
                    "type": "boolean",
                    "description": "When true, summarize error/warning/failure diagnostic lines from stdout/stderr and include source contexts for referenced project files. Defaults to false.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines before and after each extracted reference when extract_output_contexts or extract_output_diagnostics is true. Defaults to 5.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic lines to include when extract_output_diagnostics is true. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to include when extract_output_contexts or extract_output_diagnostics is true. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per extracted file context when extract_output_contexts or extract_output_diagnostics is true. Defaults to 20000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_commands",
        "description": "List project-defined commands from package.json scripts, pyproject.toml console scripts, and Makefile targets without running them, including cwd and executable availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum command count to return. Defaults to 100.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum command metadata files to scan. Defaults to 30.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "related_tests",
        "description": "Suggest likely related test files for explicit project paths or the current git changes without running tests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum target path count to analyze. Defaults to 100.",
                },
                "max_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum related test candidate count to return. Defaults to 200.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "focused_test_commands",
        "description": "Suggest focused test commands for explicit project paths or the current git changes by mapping likely related test files to runnable commands without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum target path count to analyze. Defaults to 100.",
                },
                "max_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum related test candidate count to consider. Defaults to 200.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum focused test command count to return. Defaults to 50.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_focused_test_commands",
        "description": "Preflight focused test commands inferred from explicit project paths or the current git changes without running them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_candidates": {"type": "integer", "minimum": 1, "maximum": 1000},
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum focused test command count to preflight. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "run_focused_test_commands",
        "description": "Run focused test commands inferred from explicit project paths or the current git changes after approval. Stops at the first failure by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional project-relative source or test paths. Defaults to current git changed files.",
                },
                "max_paths": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_candidates": {"type": "integer", "minimum": 1, "maximum": 1000},
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum focused test command count to run. Defaults to 10.",
                },
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional timeout in milliseconds per command. Defaults to the agent command timeout.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Stop after the first failing command. Defaults to true.",
                },
                "extract_output_contexts": {
                    "type": "boolean",
                    "description": "When true, extract file:line references from stdout/stderr and include source context for each reference. Defaults to false.",
                },
                "extract_output_diagnostics": {
                    "type": "boolean",
                    "description": "When true, summarize error/warning/failure diagnostic lines from stdout/stderr and include source contexts for referenced project files. Defaults to false.",
                },
                "context_lines": {"type": "integer", "minimum": 0, "maximum": 500},
                "max_diagnostics": {"type": "integer", "minimum": 1, "maximum": 200},
                "max_contexts": {"type": "integer", "minimum": 1, "maximum": 100},
                "max_bytes_per_context": {"type": "integer", "minimum": 1000, "maximum": 200000},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_manifests",
        "description": "Read project manifest metadata and dependency/script groups from package.json and pyproject.toml files without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum manifest file count to scan. Defaults to 30.",
                },
                "max_items": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Maximum dependency/script item count to return across manifests. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_instructions",
        "description": "Read project instruction sources from AGENTS.md and CLAUDE.md files, including scope, file metadata, truncation status, and bounded instruction text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum instruction file count to scan. Defaults to 20.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 200,
                    "maximum": 50000,
                    "description": "Maximum instruction text bytes to return. Defaults to 12000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_todos",
        "description": "Scan project text files for TODO, FIXME, HACK, XXX, and BUG markers without executing code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative file or directory scope."},
                "max_items": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum TODO marker count to return. Defaults to 100.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5000,
                    "description": "Maximum project file count to scan. Defaults to 1000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "project_overview",
        "description": "Read a compact project orientation bundle without executing code: shallow repo map, git identity/status, manifest summaries, project commands, suggested checks, and runtime tool availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum repo-map file/tree entries to report. Defaults to 80.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum project command count to report. Defaults to 20.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum suggested check count to report. Defaults to 10.",
                },
                "max_manifests": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum manifest file count to scan. Defaults to 10.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "command_check",
        "description": "Preflight one proposed shell command without running it: validate project-relative cwd, dangerous-command blocking, and main executable availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to preflight without executing."},
                "cwd": {"type": "string", "description": "Optional project-relative directory to run from. Defaults to project root."},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_run_commands",
        "description": "Preflight several finite shell commands without running them. Validates cwd, dangerous-command blocking, and executable availability for each command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to preflight without executing."},
                            "cwd": {"type": "string", "description": "Optional project-relative directory to run from. Defaults to project root."},
                            "timeout_ms": {
                                "type": "integer",
                                "minimum": 100,
                                "maximum": 600000,
                                "description": "Optional timeout in milliseconds for run_commands. Defaults to the agent command timeout.",
                            },
                            "max_output_chars": {
                                "type": "integer",
                                "minimum": 1000,
                                "maximum": 50000,
                                "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                            },
                            "extract_output_contexts": {
                                "type": "boolean",
                                "description": "When true, extract project file:line references from this command's stdout/stderr and include source contexts. Defaults to false.",
                            },
                            "extract_output_diagnostics": {
                                "type": "boolean",
                                "description": "When true, summarize error/warning/failure diagnostic lines from this command's stdout/stderr and include referenced source contexts. Defaults to false.",
                            },
                            "context_lines": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 500,
                                "description": "Lines before and after each extracted reference when extract_output_contexts or extract_output_diagnostics is true. Defaults to 5.",
                            },
                            "max_diagnostics": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 200,
                                "description": "Maximum diagnostic lines to include when extract_output_diagnostics is true. Defaults to 50.",
                            },
                            "max_contexts": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "description": "Maximum extracted contexts for this command. Defaults to 20.",
                            },
                            "max_bytes_per_context": {
                                "type": "integer",
                                "minimum": 1000,
                                "maximum": 200000,
                                "description": "Maximum characters returned per extracted context. Defaults to 20000.",
                            },
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["commands"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_commands",
        "description": "Run several finite shell commands sequentially from the project directory after approval. Stops at the first failure by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Shell command to run."},
                            "cwd": {"type": "string", "description": "Optional project-relative directory to run from. Defaults to project root."},
                            "timeout_ms": {
                                "type": "integer",
                                "minimum": 100,
                                "maximum": 600000,
                                "description": "Optional timeout in milliseconds. Defaults to the agent command timeout.",
                            },
                            "max_output_chars": {
                                "type": "integer",
                                "minimum": 1000,
                                "maximum": 50000,
                                "description": "Optional stdout/stderr character cap per command. Defaults to 12000.",
                            },
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Stop running later commands after the first nonzero, timed-out, blocked, or invalid command. Defaults to true.",
                },
            },
            "required": ["commands"],
            "additionalProperties": False,
        },
    },
    {
        "name": "port_check",
        "description": "Check whether a TCP host:port is reachable without running a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "host": {"type": "string", "description": "Host to connect to. Defaults to 127.0.0.1."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional connect timeout in milliseconds. Defaults to 1000.",
                },
            },
            "required": ["port"],
            "additionalProperties": False,
        },
    },
    {
        "name": "http_check",
        "description": "Check an HTTP(S) URL status, final URL, and an optional response-body match without running a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "HTTP or HTTPS URL to request."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional request timeout in milliseconds. Defaults to 2000.",
                },
                "max_body_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50000,
                    "description": "Maximum response body characters to return. Defaults to 2000; use 0 for status-only checks.",
                },
                "contains": {
                    "type": "string",
                    "description": "Optional literal text or regex pattern to search for in the response body.",
                },
                "regex": {
                    "type": "boolean",
                    "description": "Treat contains as a regular expression when true. Defaults to false.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "http_fetch",
        "description": "Fetch an HTTP(S) URL and return bounded response metadata plus body text without running a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "HTTP or HTTPS URL to request."},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "description": "Optional request timeout in milliseconds. Defaults to 5000.",
                },
                "max_body_chars": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Maximum response body characters to return. Defaults to 12000.",
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "environment_info",
        "description": "Read fixed runtime environment facts such as Python version, platform, git repository status, and common tool availability without executing arbitrary project commands.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "git_diff",
        "description": "Read the current git diff for the project, optionally limited to one path or staged changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative path to diff."},
                "staged": {"type": "boolean", "description": "Show staged diff instead of unstaged diff."},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum diff characters to return. Defaults to 12000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_diff_hunks",
        "description": "Read a structured summary of current git diff hunks with file paths, old/new ranges, changed-line counts, and bounded hunk lines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative path to diff."},
                "staged": {"type": "boolean", "description": "Show staged diff hunks instead of unstaged diff hunks."},
                "max_hunks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum hunk count to return. Defaults to 80.",
                },
                "max_lines_per_hunk": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum diff lines to return per hunk. Defaults to 80.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_diff_contexts",
        "description": "Read current source context around each git diff hunk so changed code can be reviewed without manually requesting file ranges.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Optional project-relative path to diff."},
                "staged": {"type": "boolean", "description": "Show staged diff contexts instead of unstaged diff contexts."},
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Source context lines before and after each hunk's new range start. Defaults to 5.",
                },
                "max_hunks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum hunk context count to return. Defaults to 80.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per source context excerpt. Defaults to 20000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_log",
        "description": "Read recent git commit history in one-line format, optionally limited to one path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum commit count to return. Defaults to 5.",
                },
                "path": {"type": "string", "description": "Optional project-relative path to limit history."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_show",
        "description": "Read one git revision with metadata, stat, and patch, optionally limited to one path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rev": {
                    "type": "string",
                    "description": "Revision to inspect. Defaults to HEAD.",
                },
                "path": {"type": "string", "description": "Optional project-relative path to limit output."},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum output characters to return. Defaults to 12000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "git_blame",
        "description": "Read git blame attribution for one project file, optionally limited to a line range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative file path to blame."},
                "start_line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Optional starting line for a focused blame range.",
                },
                "line_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Optional number of lines to include when start_line is provided. Defaults to 120.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum blame output characters to return. Defaults to 12000.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "session_summary",
        "description": "Read a compact local VibeAgent session summary without exposing full tool payloads. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to summarize. Defaults to the current run id.",
                },
                "recent_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Number of recent session rows to include. Defaults to 5.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_plan",
        "description": "Read the latest task plan from a local VibeAgent session. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to read. Defaults to the current run id.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_transcript",
        "description": "Read a safe local VibeAgent session event timeline without exposing full tool payloads. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to read. Defaults to the current run id.",
                },
                "max_events": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum recent events to include. Defaults to 80.",
                },
                "max_text": {
                    "type": "integer",
                    "minimum": 80,
                    "maximum": 5000,
                    "description": "Maximum text characters per timeline item. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_search",
        "description": "Search the safe local VibeAgent session event timeline for a query without exposing full tool payloads. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to find in the safe session timeline.",
                },
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to search. Defaults to the current run id.",
                },
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum matching timeline rows to include. Defaults to 20.",
                },
                "max_text": {
                    "type": "integer",
                    "minimum": 80,
                    "maximum": 5000,
                    "description": "Maximum text characters per timeline item. Defaults to 500.",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Use case-sensitive matching. Defaults to false.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "session_commands",
        "description": "Read bounded stdout/stderr tails from run_command and run_commands results in a local VibeAgent session. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum recent command results to include. Defaults to 20.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20000,
                    "description": "Maximum stdout and stderr characters per command. Defaults to 2000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_output_contexts",
        "description": "Extract project file:line references from recent command output in a local VibeAgent session and read their surrounding contexts. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum recent command results to inspect. Defaults to 20.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20000,
                    "description": "Maximum stdout and stderr tail characters per command to scan. Defaults to 20000.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines to include before and after each referenced line. Defaults to 5.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to read. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per context. Defaults to 20000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_output_diagnostics",
        "description": "Summarize errors, warnings, and failures from recent command output in a local VibeAgent session and read referenced source contexts. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum recent command results to inspect. Defaults to 20.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20000,
                    "description": "Maximum stdout and stderr tail characters per command to scan. Defaults to 20000.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines to include before and after each referenced line. Defaults to 2.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic rows to include. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to read. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per context. Defaults to 20000.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_files",
        "description": "Summarize project paths referenced by safe local VibeAgent session tool calls/results without exposing file contents or full tool payloads. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum file rows to include. Defaults to 100.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_failures",
        "description": "Summarize failed tool results, failed commands, failed final run results, malformed events, and denied approvals in a local VibeAgent session without exposing full tool payloads. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_failures": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum recent failure rows to include. Defaults to 50.",
                },
                "max_text": {
                    "type": "integer",
                    "minimum": 80,
                    "maximum": 5000,
                    "description": "Maximum text characters per failure message/detail. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_verification",
        "description": "Read verified, pending, and failed suggested-check status for a local VibeAgent session. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum verified, pending, and failed check rows to include per group. Defaults to 50.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_audit",
        "description": "Read a finish-time audit for a local VibeAgent session: readiness, blockers, active background processes, verification counts, plan status, failures, recent commands, and referenced files. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_failures": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum recent failure rows and pending items to include. Defaults to 10.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum referenced file rows to include. Defaults to 20.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum recent command rows to include. Defaults to 10.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum verification check rows per group to include. Defaults to 50.",
                },
                "max_text": {
                    "type": "integer",
                    "minimum": 80,
                    "maximum": 5000,
                    "description": "Maximum text characters per audit item. Defaults to 300.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "session_handoff",
        "description": "Read a compact safe handoff bundle for a local VibeAgent session: summary, finish-readiness blockers, plan, failures, referenced files, and command output tails. Defaults to the current run.",
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Optional session id to inspect. Defaults to the current run id.",
                },
                "max_failures": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum recent failure rows to include. Defaults to 20.",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum referenced file rows to include. Defaults to 50.",
                },
                "max_commands": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum recent command results to include. Defaults to 10.",
                },
                "max_checks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum verification check rows per group to include. Defaults to 50.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20000,
                    "description": "Maximum stdout and stderr characters per command. Defaults to 1000.",
                },
                "max_text": {
                    "type": "integer",
                    "minimum": 80,
                    "maximum": 5000,
                    "description": "Maximum text characters per failure message/detail. Defaults to 500.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_create",
        "description": "Save the current git HEAD, short status, staged patch, and unstaged patch under .vibeagent/checkpoints for later inspection or tracked-file recovery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "description": "Optional short label describing why the checkpoint was created.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_list",
        "description": "List saved local checkpoints for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum checkpoint rows to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_show",
        "description": "Inspect one saved checkpoint's metadata, saved short git status, and saved untracked file paths without restoring files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string"}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_diff",
        "description": "Read bounded staged and unstaged patch text saved in one checkpoint without restoring files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string"},
                "max_chars": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 200000,
                    "description": "Maximum characters to return for each saved patch. Defaults to 40000.",
                },
            },
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_status",
        "description": "Compare current git status, staged patch, unstaged patch, and saved untracked file contents with one saved checkpoint.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string"}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_checkpoint_restore",
        "description": "Preview whether a checkpoint can restore tracked staged/unstaged changes and saved untracked files. Does not restore files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string"}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_restore",
        "description": "Restore tracked staged/unstaged changes and saved untracked files from one compatible checkpoint after approval. Refuses HEAD mismatches and extra current untracked files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string"}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_checkpoint_delete",
        "description": "Preview deleting one saved checkpoint snapshot. Does not delete files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string"}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_delete",
        "description": "Delete one saved checkpoint snapshot from the local runtime directory after approval. Does not modify project files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string"}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_checkpoint_prune",
        "description": "Preview deleting older saved checkpoint snapshots while keeping the newest N. Does not delete files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keep_last": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 1000,
                    "description": "Number of newest checkpoints to keep. Use 0 to prune all checkpoints.",
                }
            },
            "required": ["keep_last"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_prune",
        "description": "Delete older saved checkpoint snapshots after approval while keeping the newest N. Does not modify project files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keep_last": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 1000,
                    "description": "Number of newest checkpoints to keep. Use 0 to prune all checkpoints.",
                }
            },
            "required": ["keep_last"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_edit_file",
        "description": "Validate one exact text replacement in an existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
    },
    {
        "name": "edit_file",
        "description": "Replace one exact text block in an existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_multi_edit_file",
        "description": "Validate multiple exact text replacements against one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string"},
                            "new": {"type": "string"},
                        },
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["path", "edits"],
            "additionalProperties": False,
        },
    },
    {
        "name": "multi_edit_file",
        "description": "Apply multiple exact text replacements to one existing project file atomically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "edits": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string"},
                            "new": {"type": "string"},
                        },
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["path", "edits"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_replace_lines",
        "description": "Validate an inclusive 1-based line range replacement in one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "content": {
                    "type": "string",
                    "description": "Replacement text for the selected lines. Use an empty string to delete the range.",
                },
            },
            "required": ["path", "start_line", "end_line", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "replace_lines",
        "description": "Replace an inclusive 1-based line range in one existing project file. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "content": {
                    "type": "string",
                    "description": "Replacement text for the selected lines. Use an empty string to delete the range.",
                },
            },
            "required": ["path", "start_line", "end_line", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_insert_lines",
        "description": "Validate inserting text before a 1-based line in one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "1-based line before which to insert. Use file line count + 1 to append.",
                },
                "content": {"type": "string", "description": "Text to insert."},
            },
            "required": ["path", "line", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "insert_lines",
        "description": "Insert text before a 1-based line in one existing project file. Use line_count + 1 to append. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "line": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "1-based line before which to insert. Use file line count + 1 to append.",
                },
                "content": {"type": "string", "description": "Text to insert."},
            },
            "required": ["path", "line", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_append_file",
        "description": "Validate appending exact UTF-8 text to one existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Text to append exactly as provided."},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "append_file",
        "description": "Append exact UTF-8 text to one existing project file. Does not add an implicit newline. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Exact text to append."},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_regex_replace",
        "description": "Preview a Python regular expression replacement in one existing UTF-8 project file without writing changes. Returns replacement count and diff.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string", "description": "Python regular expression pattern. Must not be empty."},
                "replacement": {"type": "string", "description": "Python regex replacement text, including backreferences if needed."},
                "count": {"type": "integer", "minimum": 0, "description": "Maximum replacements to preview. Use 0 for all matches."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "multiline": {"type": "boolean", "description": "Whether ^ and $ match line boundaries. Defaults to false."},
                "max_replacements": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["path", "pattern", "replacement"],
            "additionalProperties": False,
        },
    },
    {
        "name": "regex_replace",
        "description": "Apply a Python regular expression replacement to one existing UTF-8 project file after bounding the replacement count. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string", "description": "Python regular expression pattern. Must not be empty."},
                "replacement": {"type": "string", "description": "Python regex replacement text, including backreferences if needed."},
                "count": {"type": "integer", "minimum": 0, "description": "Maximum replacements to apply. Use 0 for all matches."},
                "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive. Defaults to true."},
                "multiline": {"type": "boolean", "description": "Whether ^ and $ match line boundaries. Defaults to false."},
                "max_replacements": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["path", "pattern", "replacement"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_patch",
        "description": "Validate one unified diff patch against an existing project file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with @@ hunk headers. The file path is provided separately.",
                },
            },
            "required": ["path", "patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_patches",
        "description": "Validate a multi-file unified diff without writing changes. The diff may modify existing text files, create new text files, or delete text files. Returns the combined diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with ---/+++ file headers and @@ hunk headers.",
                },
            },
            "required": ["patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "patch_file",
        "description": "Apply one or more unified diff hunks to an existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with @@ hunk headers. The file path is provided separately.",
                },
            },
            "required": ["path", "patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "patch_files",
        "description": "Apply a multi-file unified diff atomically. The diff may modify existing text files, create new text files, or delete text files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff text with ---/+++ file headers and @@ hunk headers.",
                },
            },
            "required": ["patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_write_file",
        "description": "Validate creating or replacing one UTF-8 text file without writing changes. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": "Create or replace a UTF-8 text file under the project directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_write_files",
        "description": "Validate creating or replacing up to 20 UTF-8 text files without writing changes. Returns per-file diffs that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                    "description": "Files to create or replace.",
                }
            },
            "required": ["files"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_files",
        "description": "Create or replace up to 20 UTF-8 text files under the project directory in one atomic operation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                    "description": "Files to create or replace.",
                }
            },
            "required": ["files"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_delete_file",
        "description": "Validate deleting one existing UTF-8 text project file without removing it. Returns the diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_file",
        "description": "Delete one existing project file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_delete_files",
        "description": "Validate deleting explicit existing UTF-8 text project files without removing them. Returns the combined diff that would be applied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                    "description": "Explicit project-relative file paths to delete. Globs are not expanded.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_files",
        "description": "Delete explicit existing project files after approval. All files are validated before any file is removed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                    "description": "Explicit project-relative file paths to delete. Globs are not expanded.",
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_move_file",
        "description": "Validate moving or renaming one existing project file to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_file",
        "description": "Move or rename one existing project file to a new project-relative path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_move_files",
        "description": "Validate moving or renaming explicit existing project files without changing files. All transfers are validated together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_files",
        "description": "Move or rename explicit existing project files after approval. All transfers are validated before any file is moved.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_copy_file",
        "description": "Validate copying one existing project file to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "copy_file",
        "description": "Copy one existing project file to a new project-relative path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_copy_files",
        "description": "Validate copying explicit existing project files to new project-relative paths without changing files. All transfers are validated together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "copy_files",
        "description": "Copy explicit existing project files to new project-relative paths after approval. All transfers are validated before any file is copied.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_move_dir",
        "description": "Validate moving or renaming one existing project directory to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_dir",
        "description": "Move or rename one existing project directory to a new project-relative path without overwriting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_move_dirs",
        "description": "Validate moving or renaming one or more existing project directories to new project-relative paths without changing files. Rejects overlapping sources or destinations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_dirs",
        "description": "Move or rename one or more existing project directories to new project-relative paths without overwriting after validating the whole batch. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_copy_dir",
        "description": "Validate copying one existing project directory tree to a new project-relative path without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_copy_dirs",
        "description": "Validate copying one or more existing project directory trees to new project-relative paths without changing files. Rejects symbolic links, very large directories, protected paths, and overlapping destinations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "copy_dir",
        "description": "Copy one existing project directory to a new project-relative path without overwriting. Refuses symbolic links, very large directories, and protected paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "copy_dirs",
        "description": "Copy one or more existing project directories to new project-relative paths without overwriting after validating the whole batch. Refuses symbolic links, very large directories, and protected paths. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transfers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                        },
                        "required": ["source", "destination"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["transfers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_create_dir",
        "description": "Validate creating one project-relative directory, including missing parent directories, without changing files.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_create_dirs",
        "description": "Validate creating one or more project-relative directories, including missing parent directories, without changing files. Rejects duplicate targets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_dir",
        "description": "Create one project-relative directory, including missing parent directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_dirs",
        "description": "Create one or more project-relative directories, including missing parent directories. Validates all targets before creating any directory. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_delete_empty_dir",
        "description": "Validate deleting one existing empty project-relative directory without removing it.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_delete_empty_dirs",
        "description": "Validate deleting one or more existing empty project-relative directories without removing them. Parent directories may be included when their listed child directories are also deleted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_empty_dir",
        "description": "Delete one existing empty project-relative directory. Does not delete non-empty directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "delete_empty_dirs",
        "description": "Delete one or more existing empty project-relative directories after validating all targets. Does not delete non-empty directories. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100,
                }
            },
            "required": ["paths"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_set_executable",
        "description": "Validate setting or clearing executable permission bits on one existing project file without changing mode bits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "executable": {
                    "type": "boolean",
                    "description": "True to add executable bits, false to remove them. Defaults to true.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_executable",
        "description": "Set or clear executable permission bits on one existing project file. Requires approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "executable": {
                    "type": "boolean",
                    "description": "True to add executable bits, false to remove them. Defaults to true.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command from the project directory with a timeout and safety checks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional command timeout in milliseconds. Defaults to the session timeout.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional project-relative directory to run in. Defaults to the project root.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional maximum characters to keep for each output stream. Defaults to 12000.",
                },
                "extract_output_contexts": {
                    "type": "boolean",
                    "description": "When true, extract project file:line references from stdout/stderr and include surrounding source contexts. Defaults to false.",
                },
                "extract_output_diagnostics": {
                    "type": "boolean",
                    "description": "When true, summarize error/warning/failure diagnostic lines from stdout/stderr and include referenced source contexts. Defaults to false.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines before and after each extracted reference when extract_output_contexts or extract_output_diagnostics is true. Defaults to 5.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic lines to include when extract_output_diagnostics is true. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to include when extract_output_contexts or extract_output_diagnostics is true. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum characters returned per extracted context. Defaults to 20000.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_start_command",
        "description": "Validate starting a long-running shell command from the project directory without launching it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {
                    "type": "string",
                    "description": "Optional project-relative directory to run in. Defaults to the project root.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "start_command",
        "description": "Start a long-running shell command from the project directory and return a process id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {
                    "type": "string",
                    "description": "Optional project-relative directory to run in. Defaults to the project root.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_process",
        "description": "Read status and recent stdout/stderr from a background command started by start_command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional maximum characters to keep for each output stream. Defaults to 4000.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "process_output_contexts",
        "description": "Extract file:line references from recent stdout/stderr of a background command started by start_command and include source context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50000,
                    "description": "Maximum recent characters to scan from each output stream. Defaults to 20000.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines before and after each extracted reference. Defaults to 5.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum extracted contexts to include. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per extracted file context. Defaults to 20000.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "process_output_diagnostics",
        "description": "Summarize error, warning, and failure lines from recent stdout/stderr of a background command started by start_command and include referenced source context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50000,
                    "description": "Maximum recent characters to scan from each output stream. Defaults to 20000.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 500,
                    "description": "Lines before and after each referenced source line. Defaults to 2.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum diagnostic rows to include. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum referenced source contexts to include. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "description": "Maximum bytes per extracted file context. Defaults to 20000.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "wait_process",
        "description": "Wait for a background command to exit up to a timeout, returning recent stdout/stderr without stopping it on timeout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Optional wait timeout in milliseconds. Defaults to 5000.",
                },
                "stdout_contains": {
                    "type": "string",
                    "description": "Optional stdout text or regex pattern to wait for before returning.",
                },
                "stderr_contains": {
                    "type": "string",
                    "description": "Optional stderr text or regex pattern to wait for before returning.",
                },
                "regex": {
                    "type": "boolean",
                    "description": "Treat stdout_contains and stderr_contains as Python regular expressions. Defaults to false.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Optional maximum characters to keep for each output stream. Defaults to 4000.",
                },
            },
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_write_process",
        "description": "Preview whether text can be written to stdin of a running background command without writing it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "content": {
                    "type": "string",
                    "description": "Exact text intended for stdin. Include \\n when pressing Enter is required.",
                },
            },
            "required": ["process_id", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_process",
        "description": "Write exact text to stdin of a running background command started by start_command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {"type": "string"},
                "content": {
                    "type": "string",
                    "description": "Exact text to write to stdin. Include \\n when pressing Enter is required.",
                },
            },
            "required": ["process_id", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_processes",
        "description": "List background commands started by start_command for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_stop_all_processes",
        "description": "Preview all background commands for the current project that stop_all_processes would stop.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_stop_process",
        "description": "Validate that a background command id exists and report whether stop_process would stop it.",
        "input_schema": {
            "type": "object",
            "properties": {"process_id": {"type": "string"}},
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "stop_all_processes",
        "description": "Stop all background commands started by start_command for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "stop_process",
        "description": "Stop a background command started by start_command.",
        "input_schema": {
            "type": "object",
            "properties": {"process_id": {"type": "string"}},
            "required": ["process_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_plan",
        "description": "Replace the current task plan with a concise checklist of remaining work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "explanation": {
                    "type": "string",
                    "description": "Optional short reason for the plan change.",
                },
                "plan": {
                    "type": "array",
                    "description": "Ordered task checklist. Keep it short and update it as work changes.",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                        },
                        "required": ["step", "status"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["plan"],
            "additionalProperties": False,
        },
    },
    {
        "name": "finish",
        "description": "Finish the task with a concise summary for the user.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
            "additionalProperties": False,
        },
    },
]


def build_command_preflight(workspace: RunWorkspace, command: str, cwd: str | None) -> dict[str, object]:
    cwd_label = cwd or "."
    try:
        resolve_command_cwd(workspace, cwd)
        cwd_ok = True
        cwd_message = ""
    except ValueError as error:
        cwd_ok = False
        cwd_message = str(error)

    block_reason = get_blocked_command_reason(command)
    missing_tool = missing_command_tool(command)
    ok = cwd_ok and block_reason is None and missing_tool is None
    if ok:
        message = "Command preflight passed."
    else:
        issues: list[str] = []
        if not cwd_ok:
            issues.append(cwd_message)
        if block_reason:
            issues.append(f"Command blocked: {block_reason}")
        if missing_tool:
            issues.append(f"Missing executable on PATH: {missing_tool}")
        message = "Command preflight failed: " + "; ".join(issues) + "."
    return {
        "ok": ok,
        "cwd": cwd_label,
        "cwd_ok": cwd_ok,
        "blocked": block_reason is not None,
        "block_reason": block_reason,
        "executable_available": missing_tool is None,
        "missing_tool": missing_tool,
        "message": message,
    }


def build_command_check_observation(workspace: RunWorkspace, command: str, cwd: str | None) -> CommandCheckObservation:
    result = build_command_preflight(workspace, command, cwd)
    return CommandCheckObservation(
        kind="command_check",
        ok=bool(result["ok"]),
        command=command,
        cwd=str(result["cwd"]),
        cwd_ok=bool(result["cwd_ok"]),
        blocked=bool(result["blocked"]),
        block_reason=result["block_reason"] if isinstance(result["block_reason"], str) else None,
        executable_available=bool(result["executable_available"]),
        missing_tool=result["missing_tool"] if isinstance(result["missing_tool"], str) else None,
        message=str(result["message"]),
    )


def check_tcp_port(host: str, port: int, timeout_ms: int = 1_000) -> PortCheckObservation:
    try:
        with socket.create_connection((host, port), timeout=timeout_ms / 1000):
            return PortCheckObservation(
                kind="port_check",
                ok=True,
                host=host,
                port=port,
                timeout_ms=timeout_ms,
                reachable=True,
                error=None,
                message=f"{host}:{port} is reachable.",
            )
    except ConnectionRefusedError as error:
        return PortCheckObservation(
            kind="port_check",
            ok=True,
            host=host,
            port=port,
            timeout_ms=timeout_ms,
            reachable=False,
            error=str(error),
            message=f"{host}:{port} is not accepting TCP connections.",
        )
    except TimeoutError as error:
        return PortCheckObservation(
            kind="port_check",
            ok=True,
            host=host,
            port=port,
            timeout_ms=timeout_ms,
            reachable=False,
            error=str(error),
            message=f"{host}:{port} did not respond before timeout.",
        )
    except OSError as error:
        return PortCheckObservation(
            kind="port_check",
            ok=False,
            host=host,
            port=port,
            timeout_ms=timeout_ms,
            reachable=False,
            error=str(error),
            message=f"Could not check {host}:{port}: {error}.",
        )


def check_http_url(
    url: str,
    timeout_ms: int = 2_000,
    max_body_chars: int = 2_000,
    contains: str | None = None,
    regex: bool = False,
) -> HttpCheckObservation:
    request = urllib.request.Request(url, headers={"User-Agent": "vibeagent-http-check/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_ms / 1000) as response:
            status = int(response.getcode())
            final_url = str(response.geturl())
            reason = str(getattr(response, "reason", "") or "") or None
            return build_http_check_observation(
                url=url,
                final_url=final_url,
                status=status,
                reason=reason,
                timeout_ms=timeout_ms,
                max_body_chars=max_body_chars,
                contains=contains,
                regex=regex,
                body_reader=response.read,
                error=None,
            )
    except urllib.error.HTTPError as error:
        return build_http_check_observation(
            url=url,
            final_url=str(error.geturl() or url),
            status=int(error.code),
            reason=str(error.reason or "") or None,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            contains=contains,
            regex=regex,
            body_reader=error.read,
            error=None,
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
        return HttpCheckObservation(
            kind="http_check",
            ok=True,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            timeout_ms=timeout_ms,
            reachable=False,
            matched=False,
            matched_pattern=contains,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"{url} is not reachable over HTTP: {error}.",
        )
    except OSError as error:
        return HttpCheckObservation(
            kind="http_check",
            ok=False,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            timeout_ms=timeout_ms,
            reachable=False,
            matched=False,
            matched_pattern=contains,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"Could not check {url}: {error}.",
        )


def build_http_check_observation(
    *,
    url: str,
    final_url: str,
    status: int,
    reason: str | None,
    timeout_ms: int,
    max_body_chars: int,
    contains: str | None,
    regex: bool,
    body_reader: Any,
    error: str | None,
) -> HttpCheckObservation:
    raw = body_reader(max_body_chars + 1)
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    elif not isinstance(raw, bytes):
        raw = bytes(raw)
    body_truncated = len(raw) > max_body_chars
    body = raw[:max_body_chars].decode("utf-8", errors="replace")
    matched = False
    if contains is not None:
        try:
            matched = re.search(contains, body) is not None if regex else contains in body
        except re.error as regex_error:
            return HttpCheckObservation(
                kind="http_check",
                ok=False,
                url=url,
                final_url=final_url,
                status=status,
                reason=reason,
                timeout_ms=timeout_ms,
                reachable=True,
                matched=False,
                matched_pattern=contains,
                body=body,
                body_truncated=body_truncated,
                max_body_chars=max_body_chars,
                error=str(regex_error),
                message=f"{url} returned HTTP {status}, but contains regex is invalid: {regex_error}.",
            )
    match_detail = ""
    if contains is not None:
        match_detail = " Body pattern matched." if matched else " Body pattern did not match."
    return HttpCheckObservation(
        kind="http_check",
        ok=True,
        url=url,
        final_url=final_url,
        status=status,
        reason=reason,
        timeout_ms=timeout_ms,
        reachable=True,
        matched=matched,
        matched_pattern=contains,
        body=body,
        body_truncated=body_truncated,
        max_body_chars=max_body_chars,
        error=error,
        message=f"{final_url} returned HTTP {status}.{match_detail}",
    )


def fetch_http_url(url: str, timeout_ms: int = 5_000, max_body_chars: int = 12_000) -> HttpFetchObservation:
    request = urllib.request.Request(url, headers={"User-Agent": "vibeagent-http-fetch/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_ms / 1000) as response:
            return build_http_fetch_observation(
                url=url,
                final_url=str(response.geturl()),
                status=int(response.getcode()),
                reason=str(getattr(response, "reason", "") or "") or None,
                content_type=response_content_type(response),
                timeout_ms=timeout_ms,
                max_body_chars=max_body_chars,
                body_reader=response.read,
                error=None,
            )
    except urllib.error.HTTPError as error:
        return build_http_fetch_observation(
            url=url,
            final_url=str(error.geturl() or url),
            status=int(error.code),
            reason=str(error.reason or "") or None,
            content_type=response_content_type(error),
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            body_reader=error.read,
            error=None,
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
        return HttpFetchObservation(
            kind="http_fetch",
            ok=True,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            content_type=None,
            timeout_ms=timeout_ms,
            reachable=False,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"{url} is not reachable over HTTP: {error}.",
        )
    except OSError as error:
        return HttpFetchObservation(
            kind="http_fetch",
            ok=False,
            url=url,
            final_url=None,
            status=None,
            reason=None,
            content_type=None,
            timeout_ms=timeout_ms,
            reachable=False,
            body="",
            body_truncated=False,
            max_body_chars=max_body_chars,
            error=str(error),
            message=f"Could not fetch {url}: {error}.",
        )


def build_http_fetch_observation(
    *,
    url: str,
    final_url: str,
    status: int,
    reason: str | None,
    content_type: str | None,
    timeout_ms: int,
    max_body_chars: int,
    body_reader: Any,
    error: str | None,
) -> HttpFetchObservation:
    raw = body_reader(max_body_chars + 1)
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    elif not isinstance(raw, bytes):
        raw = bytes(raw)
    body_truncated = len(raw) > max_body_chars
    body = raw[:max_body_chars].decode("utf-8", errors="replace")
    return HttpFetchObservation(
        kind="http_fetch",
        ok=True,
        url=url,
        final_url=final_url,
        status=status,
        reason=reason,
        content_type=content_type,
        timeout_ms=timeout_ms,
        reachable=True,
        body=body,
        body_truncated=body_truncated,
        max_body_chars=max_body_chars,
        error=error,
        message=f"{final_url} returned HTTP {status}.",
    )


def response_content_type(response: Any) -> str | None:
    getheader = getattr(response, "getheader", None)
    if callable(getheader):
        value = getheader("Content-Type")
        return str(value) if value else None
    headers = getattr(response, "headers", None)
    if isinstance(headers, dict):
        value = headers.get("Content-Type") or headers.get("content-type")
        return str(value) if value else None
    return None


def output_context_results_from_dicts(items: object) -> list[OutputContextResult]:
    if not isinstance(items, list):
        return []
    results: list[OutputContextResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        results.append(
            OutputContextResult(
                path=str(item["path"]),
                line=int(item["line"]),
                column=int(item["column"]) if item["column"] is not None else None,
                raw=str(item["raw"]),
                ok=bool(item["ok"]),
                content=str(item["content"]),
                message=str(item["message"]),
                context_lines=int(item["context_lines"]),
                start_line=int(item["start_line"]),
                end_line=int(item["end_line"]),
                line_count=int(item["line_count"]),
                total_lines=int(item["total_lines"]) if item["total_lines"] is not None else None,
                target_line_exists=bool(item["target_line_exists"]),
                truncated=bool(item["truncated"]),
                max_bytes=int(item["max_bytes"]),
            )
        )
    return results


def output_diagnostics_from_dicts(items: object) -> list[OutputDiagnostic]:
    if not isinstance(items, list):
        return []
    diagnostics: list[OutputDiagnostic] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "info")
        if severity not in {"error", "warning", "failure", "info"}:
            severity = "info"
        diagnostics.append(
            OutputDiagnostic(
                severity=severity,  # type: ignore[arg-type]
                output_line=int(item["output_line"]),
                text=str(item["text"]),
                path=str(item["path"]) if item.get("path") is not None else None,
                line=int(item["line"]) if item.get("line") is not None else None,
                column=int(item["column"]) if item.get("column") is not None else None,
                raw=str(item["raw"]) if item.get("raw") is not None else None,
            )
        )
    return diagnostics


def parse_session_search_counts(text: str) -> tuple[int, int]:
    total_matches = 0
    shown_matches = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("matches:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                total_matches = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_matches = int(raw_shown)
    return total_matches, shown_matches


def parse_session_commands_counts(text: str) -> tuple[int, int]:
    command_count = 0
    shown_commands = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("commands:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                command_count = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_commands = int(raw_shown)
    return command_count, shown_commands


def build_session_command_output_scan_text(
    workspace: RunWorkspace,
    run_id: str,
    max_commands: int,
    max_output_chars: int,
) -> tuple[bool, int, int, str, str]:
    current_session_dir = session_dir(workspace.root, run_id)
    if not current_session_dir.is_dir():
        return False, 0, 0, "", f"Session not found: {run_id}"

    entries = session_command_entries(read_session_events(workspace.root, run_id))
    shown_entries = entries[-max_commands:]
    chunks: list[str] = []
    for entry in shown_entries:
        result = entry["result"]
        command = result.get("command")
        header = f"# {entry['kind']}[{entry['index']}] command: {command if isinstance(command, str) else 'unknown'}"
        stdout = command_output_tail(result.get("stdout") if isinstance(result.get("stdout"), str) else "", max_output_chars)
        stderr = command_output_tail(result.get("stderr") if isinstance(result.get("stderr"), str) else "", max_output_chars)
        chunks.append("\n".join([header, "stdout:", stdout, "stderr:", stderr]))
    return True, len(entries), len(shown_entries), "\n\n".join(chunks), (
        f"Scanned {len(shown_entries)}/{len(entries)} command result(s) from session {run_id}."
    )


def parse_session_files_counts(text: str) -> tuple[int, int]:
    file_count = 0
    shown_files = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("files:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                file_count = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_files = int(raw_shown)
    return file_count, shown_files


def parse_session_failures_counts(text: str) -> tuple[int, int]:
    failure_count = 0
    shown_failures = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("failures:"):
            raw_total = stripped.split(":", 1)[1].strip()
            if raw_total.isdigit():
                failure_count = int(raw_total)
        elif stripped.startswith("shown:"):
            raw_shown = stripped.split(":", 1)[1].strip().split("/", 1)[0]
            if raw_shown.isdigit():
                shown_failures = int(raw_shown)
    return failure_count, shown_failures


def build_reference_context_results(
    workspace: RunWorkspace,
    references: list[dict[str, object]],
    symbol: str,
    context_lines: int,
    max_bytes_per_context: int,
) -> list[ReferenceContextResult]:
    contexts: list[ReferenceContextResult] = []
    for reference in references:
        path = str(reference["path"])
        line = int(reference["line"])
        context = read_project_file_context_result(
            workspace,
            path,
            line=line,
            context_lines=context_lines,
            max_bytes=max_bytes_per_context,
        )
        contexts.append(
            ReferenceContextResult(
                path=path,
                line=line,
                column=int(reference.get("column", 0)),
                symbol=str(reference.get("symbol", symbol)),
                kind=str(reference.get("kind", "reference")),
                language=str(reference["language"]) if reference.get("language") is not None else None,
                matched_line=str(reference.get("context", "")),
                content=str(context["content"]),
                context_lines=int(context["context_lines"]),
                start_line=int(context["start_line"]),
                end_line=int(context["end_line"]),
                line_count=int(context["line_count"]),
                total_lines=int(context["total_lines"]) if context["total_lines"] is not None else None,
                truncated=bool(context["truncated"]),
                max_bytes=int(context["max_bytes"]),
            )
        )
    return contexts


def final_review_session_verification_issues(
    workspace: RunWorkspace,
    suggested_checks: list[SuggestedCheck],
) -> tuple[list[str], list[str]]:
    suggested_commands = {
        (check.command, check.cwd or ".")
        for check in suggested_checks
        if check.command
    }
    if not suggested_commands:
        return [], []

    events = read_session_events(workspace.root, workspace.run_id)
    last_change_index = latest_successful_project_change_event_index(events)
    if last_change_index is None:
        return [], []

    statuses: dict[tuple[str, str], bool] = {}
    for event in events[last_change_index + 1 :]:
        result = event.payload.get("result") if not event.malformed and event.type == "tool_result" else None
        if not isinstance(result, dict):
            continue
        for command_result in iter_command_results(result):
            key = command_result_key(command_result)
            if key not in suggested_commands:
                continue
            statuses[key] = command_result_succeeded(command_result)

    verified_commands = {key for key, passed in statuses.items() if passed}
    failed_commands = {key for key, passed in statuses.items() if not passed}
    failed_labels = [suggested_check_label(command, cwd) for command, cwd in sorted(failed_commands)]
    pending_labels = [
        suggested_check_label(command, cwd)
        for command, cwd in sorted(suggested_commands - verified_commands - failed_commands)
    ]
    blockers: list[str] = []
    warnings: list[str] = []
    if failed_labels:
        blockers.append("Suggested verification checks failed after the latest project change.")
        warnings.append("Failed suggested check(s): " + ", ".join(failed_labels[:5]) + ".")
    if pending_labels:
        blockers.append("Suggested verification checks are still pending after the latest project change.")
        warnings.append("Pending suggested check(s): " + ", ".join(pending_labels[:5]) + ".")
    return blockers, warnings


def latest_successful_project_change_event_index(events: list[Any]) -> int | None:
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        if event.malformed or event.type != "tool_result":
            continue
        result = event.payload.get("result")
        if not isinstance(result, dict):
            continue
        if result.get("kind") in PROJECT_CHANGE_RESULT_KINDS and result.get("ok") is not False:
            return index
    return None


def iter_command_results(result: dict[str, Any]) -> list[dict[str, Any]]:
    kind = result.get("kind")
    if kind == "run_command":
        command_result = result.get("result")
        return [command_result] if isinstance(command_result, dict) else []
    if kind in {"run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        command_results = result.get("results")
        if isinstance(command_results, list):
            return [item for item in command_results if isinstance(item, dict)]
    return []


def command_result_key(result: dict[str, Any]) -> tuple[str, str]:
    command = result.get("command")
    cwd = result.get("cwd")
    return (command if isinstance(command, str) else "", cwd if isinstance(cwd, str) and cwd else ".")


def command_result_succeeded(result: dict[str, Any]) -> bool:
    return result.get("exit_code") == 0 and result.get("timed_out") is not True


def suggested_check_label(command: str, cwd: str) -> str:
    return command if cwd in {"", "."} else f"{command} (cwd={cwd})"


def execute_action(workspace: RunWorkspace, action: AgentAction, command_timeout_ms: int = 30_000) -> Observation:
    # Dispatch one action at a time; all side effects stay within the given project workspace.
    if isinstance(action, ListFilesAction):
        try:
            files, total = list_project_files(workspace, action.path)
            truncated = len(files) < total
            message = f"Found {total} file(s)."
            if truncated:
                message += f" Showing first {len(files)}."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            message = str(error)
        return ListFilesObservation(
            kind="list_files",
            path=action.path or ".",
            files=files,
            total=total,
            truncated=truncated,
            message=message,
        )

    if isinstance(action, ListTreeAction):
        try:
            entries, total = list_project_tree(
                workspace,
                action.path,
                max_depth=action.max_depth,
                max_entries=action.max_entries,
            )
            truncated = len(entries) < total
            entry_word = "entry" if total == 1 else "entries"
            message = f"Found {total} {entry_word}."
            if truncated:
                message += f" Showing first {len(entries)}."
            ok = True
        except ValueError as error:
            entries = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return ListTreeObservation(
            kind="list_tree",
            path=action.path or ".",
            entries=entries,
            total=total,
            truncated=truncated,
            max_depth=action.max_depth,
            ok=ok,
            message=message,
        )

    if isinstance(action, RepoMapAction):
        try:
            repo_map = build_repo_map(
                workspace,
                action.path,
                max_depth=action.max_depth,
                max_files=action.max_files,
                max_symbols=action.max_symbols,
            )
            python_files = [
                RepoMapPythonFile(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    imports=list(item["imports"]),
                    symbols=[PythonSymbol(**symbol) for symbol in item["symbols"]],
                    message=str(item["message"]),
                )
                for item in repo_map["python_files"]
            ]
            code_files = [
                CodeOutlineResult(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    language=str(item["language"]) if item.get("language") is not None else None,
                    imports=list(item["imports"]),
                    symbols=[PythonSymbol(**symbol) for symbol in item["symbols"]],
                    message=str(item["message"]),
                )
                for item in repo_map["code_files"]
            ]
            return RepoMapObservation(
                kind="repo_map",
                path=str(repo_map["path"]),
                tree=list(repo_map["tree"]),
                files=list(repo_map["files"]),
                python_files=python_files,
                code_files=code_files,
                total_tree_entries=int(repo_map["total_tree_entries"]),
                total_files=int(repo_map["total_files"]),
                truncated=bool(repo_map["truncated"]),
                ok=True,
                message=str(repo_map["message"]),
            )
        except ValueError as error:
            return RepoMapObservation(
                kind="repo_map",
                path=action.path or ".",
                tree=[],
                files=[],
                python_files=[],
                code_files=[],
                total_tree_entries=0,
                total_files=0,
                truncated=False,
                ok=False,
                message=str(error),
            )

    if isinstance(action, ReadFileAction):
        try:
            result = read_project_file_result(
                workspace,
                action.path,
                max_bytes=action.max_bytes,
                start_line=action.start_line,
                line_count=action.line_count,
            )
            content = str(result["content"])
            truncated = bool(result["truncated"])
            total_bytes = int(result["total_bytes"])
            max_bytes = int(result["max_bytes"])
            if action.start_line is None:
                message = f"Read {action.path}."
            else:
                message = f"Read {action.path} from line {action.start_line}."
        except ValueError as error:
            content = ""
            message = str(error)
            truncated = False
            total_bytes = None
            max_bytes = action.max_bytes
        return ReadFileObservation(
            kind="read_file",
            path=action.path,
            content=content,
            message=message,
            start_line=action.start_line,
            line_count=action.line_count,
            truncated=truncated,
            total_bytes=total_bytes,
            max_bytes=max_bytes,
        )

    if isinstance(action, ReadFileContextAction):
        try:
            result = read_project_file_context_result(
                workspace,
                action.path,
                line=action.line,
                context_lines=action.context_lines,
                max_bytes=action.max_bytes,
            )
            return ReadFileContextObservation(
                kind="read_file_context",
                path=action.path,
                ok=True,
                content=str(result["content"]),
                message=f"Read {action.path} around line {action.line}.",
                line=int(result["line"]),
                context_lines=int(result["context_lines"]),
                start_line=int(result["start_line"]),
                end_line=int(result["end_line"]),
                line_count=int(result["line_count"]),
                total_lines=int(result["total_lines"]),
                target_line_exists=bool(result["target_line_exists"]),
                truncated=bool(result["truncated"]),
                max_bytes=int(result["max_bytes"]),
            )
        except ValueError as error:
            return ReadFileContextObservation(
                kind="read_file_context",
                path=action.path,
                ok=False,
                content="",
                message=str(error),
                line=action.line,
                context_lines=action.context_lines,
                max_bytes=action.max_bytes,
            )

    if isinstance(action, ReadFileContextsAction):
        contexts: list[ReadFileContextResult] = []
        for item in action.contexts:
            try:
                result = read_project_file_context_result(
                    workspace,
                    item.path,
                    line=item.line,
                    context_lines=item.context_lines,
                    max_bytes=action.max_bytes_per_context,
                )
                contexts.append(
                    ReadFileContextResult(
                        path=item.path,
                        line=int(result["line"]),
                        context_lines=int(result["context_lines"]),
                        ok=True,
                        content=str(result["content"]),
                        message=f"Read {item.path} around line {item.line}.",
                        start_line=int(result["start_line"]),
                        end_line=int(result["end_line"]),
                        line_count=int(result["line_count"]),
                        total_lines=int(result["total_lines"]),
                        target_line_exists=bool(result["target_line_exists"]),
                        truncated=bool(result["truncated"]),
                        max_bytes=int(result["max_bytes"]),
                    )
                )
            except ValueError as error:
                contexts.append(
                    ReadFileContextResult(
                        path=item.path,
                        line=item.line,
                        context_lines=item.context_lines,
                        ok=False,
                        content="",
                        message=str(error),
                        max_bytes=action.max_bytes_per_context,
                    )
                )
        ok_count = sum(1 for item in contexts if item.ok)
        return ReadFileContextsObservation(
            kind="read_file_contexts",
            contexts=contexts,
            message=f"Read {ok_count}/{len(contexts)} file context(s).",
        )

    if isinstance(action, OutputContextsAction):
        result = read_output_contexts_result(
            workspace,
            action.text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        contexts = output_context_results_from_dicts(result["contexts"])
        return OutputContextsObservation(
            kind="output_contexts",
            contexts=contexts,
            total_refs=int(result["total_refs"]),
            truncated=bool(result["truncated"]),
            message=str(result["message"]),
        )

    if isinstance(action, OutputDiagnosticsAction):
        result = read_output_diagnostics_result(
            workspace,
            action.text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        return OutputDiagnosticsObservation(
            kind="output_diagnostics",
            diagnostics=output_diagnostics_from_dicts(result["diagnostics"]),
            contexts=output_context_results_from_dicts(result["contexts"]),
            total_diagnostics=int(result["total_diagnostics"]),
            total_refs=int(result["total_refs"]),
            diagnostics_truncated=bool(result["diagnostics_truncated"]),
            contexts_truncated=bool(result["contexts_truncated"]),
            message=str(result["message"]),
        )

    if isinstance(action, TailFileAction):
        try:
            result = read_project_file_tail_result(
                workspace,
                action.path,
                line_count=action.line_count,
                max_bytes=action.max_bytes,
            )
            return TailFileObservation(
                kind="tail_file",
                path=action.path,
                ok=True,
                content=str(result["content"]),
                message=f"Read last {result['line_count']} line(s) from {action.path}.",
                start_line=int(result["start_line"]),
                line_count=int(result["line_count"]),
                requested_line_count=int(result["requested_line_count"]),
                total_lines=int(result["total_lines"]),
                truncated=bool(result["truncated"]),
                max_bytes=int(result["max_bytes"]),
            )
        except ValueError as error:
            return TailFileObservation(
                kind="tail_file",
                path=action.path,
                ok=False,
                content="",
                message=str(error),
                requested_line_count=action.line_count,
                max_bytes=action.max_bytes,
            )

    if isinstance(action, ReadFilesAction):
        files: list[ReadFileResult] = []
        for path in action.paths:
            try:
                result = read_project_file_result(workspace, path, max_bytes=action.max_bytes_per_file)
                files.append(
                    ReadFileResult(
                        path=path,
                        ok=True,
                        content=str(result["content"]),
                        message=f"Read {path}.",
                        truncated=bool(result["truncated"]),
                        total_bytes=int(result["total_bytes"]),
                        max_bytes=int(result["max_bytes"]),
                    )
                )
            except ValueError as error:
                files.append(
                    ReadFileResult(
                        path=path,
                        ok=False,
                        content="",
                        message=str(error),
                        truncated=False,
                        total_bytes=None,
                        max_bytes=action.max_bytes_per_file,
                    )
                )
        ok_count = sum(1 for item in files if item.ok)
        return ReadFilesObservation(
            kind="read_files",
            files=files,
            message=f"Read {ok_count}/{len(files)} file(s).",
        )

    if isinstance(action, ReadFileRangesAction):
        ranges: list[ReadFileRangeResult] = []
        for item in action.ranges:
            try:
                result = read_project_file_result(
                    workspace,
                    item.path,
                    max_bytes=action.max_bytes_per_range,
                    start_line=item.start_line,
                    line_count=item.line_count,
                )
                content = str(result["content"])
                ranges.append(
                    ReadFileRangeResult(
                        path=item.path,
                        start_line=item.start_line,
                        line_count=item.line_count,
                        ok=True,
                        content=content,
                        message=f"Read {item.path}:{item.start_line}+{item.line_count}.",
                        truncated=bool(result["truncated"]),
                        total_bytes=int(result["total_bytes"]),
                        max_bytes=int(result["max_bytes"]),
                    )
                )
            except ValueError as error:
                ranges.append(
                    ReadFileRangeResult(
                        path=item.path,
                        start_line=item.start_line,
                        line_count=item.line_count,
                        ok=False,
                        content="",
                        message=str(error),
                        truncated=False,
                        total_bytes=None,
                        max_bytes=action.max_bytes_per_range,
                    )
                )
        ok_count = sum(1 for item in ranges if item.ok)
        return ReadFileRangesObservation(
            kind="read_file_ranges",
            ranges=ranges,
            message=f"Read {ok_count}/{len(ranges)} file range(s).",
        )

    if isinstance(action, FileInfoAction):
        files: list[FileInfoResult] = []
        for path in action.paths:
            try:
                info = read_project_file_info(workspace, path)
                files.append(FileInfoResult(**info))
            except ValueError as error:
                files.append(
                    FileInfoResult(
                        path=path,
                        ok=False,
                        exists=False,
                        is_file=False,
                        is_dir=False,
                        size_bytes=None,
                        line_count=None,
                        is_binary=None,
                        message=str(error),
                    )
                )
        ok_count = sum(1 for item in files if item.ok)
        return FileInfoObservation(
            kind="file_info",
            files=files,
            message=f"Inspected {ok_count}/{len(files)} path(s).",
        )

    if isinstance(action, ImageInfoAction):
        images: list[ImageInfoResult] = []
        for path in action.paths:
            try:
                info = read_project_image_info(workspace, path)
                images.append(ImageInfoResult(**info))
            except ValueError as error:
                images.append(
                    ImageInfoResult(
                        path=path,
                        ok=False,
                        exists=False,
                        is_file=False,
                        size_bytes=None,
                        format=None,
                        mime_type=None,
                        width=None,
                        height=None,
                        message=str(error),
                    )
                )
        ok_count = sum(1 for item in images if item.ok)
        return ImageInfoObservation(
            kind="image_info",
            images=images,
            message=f"Inspected {ok_count}/{len(images)} image(s).",
        )

    if isinstance(action, PythonSymbolsAction):
        files: list[PythonSymbolsResult] = []
        for path in action.paths:
            try:
                outline = read_python_symbol_outline(workspace, path)
                symbols = [PythonSymbol(**item) for item in outline["symbols"]]
                files.append(
                    PythonSymbolsResult(
                        path=str(outline["path"]),
                        ok=True,
                        symbols=symbols,
                        imports=list(outline["imports"]),
                        message=str(outline["message"]),
                    )
                )
            except ValueError as error:
                files.append(PythonSymbolsResult(path=path, ok=False, symbols=[], imports=[], message=str(error)))
        ok_count = sum(1 for item in files if item.ok)
        return PythonSymbolsObservation(
            kind="python_symbols",
            files=files,
            message=f"Read symbols for {ok_count}/{len(files)} Python file(s).",
        )

    if isinstance(action, CodeOutlineAction):
        files: list[CodeOutlineResult] = []
        for path in action.paths:
            try:
                outline = read_code_outline(workspace, path, max_symbols=action.max_symbols)
                symbols = [PythonSymbol(**item) for item in outline["symbols"]]
                files.append(
                    CodeOutlineResult(
                        path=str(outline["path"]),
                        ok=True,
                        language=str(outline["language"]),
                        symbols=symbols,
                        imports=list(outline["imports"]),
                        message=str(outline["message"]),
                    )
                )
            except ValueError as error:
                files.append(CodeOutlineResult(path=path, ok=False, language=None, symbols=[], imports=[], message=str(error)))
        ok_count = sum(1 for item in files if item.ok)
        return CodeOutlineObservation(
            kind="code_outline",
            files=files,
            message=f"Read outlines for {ok_count}/{len(files)} source file(s).",
        )

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

    if isinstance(action, GlobAction):
        try:
            matches, total = glob_project_files(workspace, action.pattern, max_matches=action.max_matches)
            truncated = len(matches) < total
            message = f"Found {total} file(s)."
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

    if isinstance(action, GitStatusAction):
        result = read_git_status(workspace)
        message = "Read git status." if result.ok else result.stderr or "git status failed."
        return GitStatusObservation(
            kind="git_status",
            ok=result.ok,
            status=result.stdout,
            message=message,
        )

    if isinstance(action, GitConflictsAction):
        try:
            conflicts = read_git_conflicts(
                workspace,
                action.path,
                max_markers=action.max_markers,
                max_files=action.max_files,
            )
            unmerged = [GitConflictStatus(**item) for item in conflicts["unmerged"]]
            markers = [GitConflictMarker(**item) for item in conflicts["markers"]]
            return GitConflictsObservation(
                kind="git_conflicts",
                ok=bool(conflicts["ok"]),
                path=str(conflicts["path"]),
                unmerged=unmerged,
                unmerged_total=int(conflicts["unmerged_total"]),
                markers=markers,
                markers_total=int(conflicts["markers_total"]),
                scanned_files=int(conflicts["scanned_files"]),
                total_files=int(conflicts["total_files"]),
                truncated=bool(conflicts["truncated"]),
                message=str(conflicts["message"]),
            )
        except ValueError as error:
            return GitConflictsObservation(
                kind="git_conflicts",
                ok=False,
                path=action.path or ".",
                unmerged=[],
                unmerged_total=0,
                markers=[],
                markers_total=0,
                scanned_files=0,
                total_files=0,
                truncated=False,
                message=str(error),
            )

    if isinstance(action, GitInfoAction):
        info = read_git_info(workspace)
        remotes = [GitRemote(**item) for item in info["remotes"]]
        return GitInfoObservation(
            kind="git_info",
            ok=bool(info["ok"]),
            is_git_repo=bool(info["is_git_repo"]),
            branch=str(info["branch"]),
            head=str(info["head"]),
            upstream=str(info["upstream"]),
            ahead=int(info["ahead"]),
            behind=int(info["behind"]),
            remotes=remotes,
            status=str(info["status"]),
            message=str(info["message"]),
        )

    if isinstance(action, GitChangesAction):
        changes = read_git_changes(workspace)
        files = [GitChangeFile(**item) for item in changes["files"]]
        return GitChangesObservation(
            kind="git_changes",
            ok=bool(changes["ok"]),
            files=files,
            status=str(changes["status"]),
            message=str(changes["message"]),
        )

    if isinstance(action, GitBranchesAction):
        try:
            result = read_git_branches(workspace, max_branches=action.max_branches)
        except ValueError as error:
            result = {
                "ok": False,
                "current": "",
                "branches": [],
                "total": 0,
                "truncated": False,
                "status": "",
                "message": str(error),
            }
        branches = [GitBranchInfo(**item) for item in result["branches"]]
        return GitBranchesObservation(
            kind="git_branches",
            ok=bool(result["ok"]),
            current=str(result["current"]),
            branches=branches,
            total=int(result["total"]),
            truncated=bool(result["truncated"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitFetchAction):
        try:
            result = preview_fetch_git_remote(workspace, action.remote)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": action.remote or "",
                "remote_url": "",
                "branch": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "message": str(error),
            }
        return CheckGitFetchObservation(
            kind="check_git_fetch",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            remote_url=str(result["remote_url"]),
            branch=str(result["branch"]),
            upstream=str(result["upstream"]),
            ahead=int(result["ahead"]),
            behind=int(result["behind"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitFetchAction):
        try:
            result = fetch_git_remote(workspace, action.remote)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": action.remote or "",
                "remote_url": "",
                "branch": "",
                "upstream": "",
                "ahead_before": 0,
                "behind_before": 0,
                "ahead_after": 0,
                "behind_after": 0,
                "message": str(error),
            }
        return GitFetchObservation(
            kind="git_fetch",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            remote_url=str(result["remote_url"]),
            branch=str(result["branch"]),
            upstream=str(result["upstream"]),
            ahead_before=int(result["ahead_before"]),
            behind_before=int(result["behind_before"]),
            ahead_after=int(result["ahead_after"]),
            behind_after=int(result["behind_after"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitPullAction):
        try:
            result = preview_pull_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "worktree_clean": False,
                "status": "",
                "message": str(error),
            }
        return CheckGitPullObservation(
            kind="check_git_pull",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current=str(result["current"]),
            upstream=str(result["upstream"]),
            ahead=int(result["ahead"]),
            behind=int(result["behind"]),
            worktree_clean=bool(result["worktree_clean"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitPullAction):
        try:
            result = pull_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current_before": "",
                "current_after": "",
                "upstream": "",
                "ahead_before": 0,
                "behind_before": 0,
                "ahead_after": 0,
                "behind_after": 0,
                "status": "",
                "message": str(error),
            }
        return GitPullObservation(
            kind="git_pull",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current_before=str(result["current_before"]),
            current_after=str(result["current_after"]),
            upstream=str(result["upstream"]),
            ahead_before=int(result["ahead_before"]),
            behind_before=int(result["behind_before"]),
            ahead_after=int(result["ahead_after"]),
            behind_after=int(result["behind_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitPushAction):
        try:
            result = preview_push_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "worktree_clean": False,
                "status": "",
                "message": str(error),
            }
        return CheckGitPushObservation(
            kind="check_git_push",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current=str(result["current"]),
            upstream=str(result["upstream"]),
            ahead=int(result["ahead"]),
            behind=int(result["behind"]),
            worktree_clean=bool(result["worktree_clean"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitPushAction):
        try:
            result = push_git_upstream(workspace)
        except ValueError as error:
            result = {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "",
                "upstream": "",
                "ahead_before": 0,
                "behind_before": 0,
                "status": "",
                "message": str(error),
            }
        return GitPushObservation(
            kind="git_push",
            ok=bool(result["ok"]),
            remote=str(result["remote"]),
            branch=str(result["branch"]),
            current=str(result["current"]),
            upstream=str(result["upstream"]),
            ahead_before=int(result["ahead_before"]),
            behind_before=int(result["behind_before"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitSwitchAction):
        try:
            result = preview_switch_git_branch(workspace, action.branch, create=action.create)
        except ValueError as error:
            result = {
                "ok": False,
                "branch": action.branch,
                "create": action.create,
                "current_before": "",
                "branch_exists": False,
                "worktree_clean": False,
                "status": "",
                "message": str(error),
            }
        return CheckGitSwitchObservation(
            kind="check_git_switch",
            ok=bool(result["ok"]),
            branch=str(result["branch"]),
            create=bool(result["create"]),
            current_before=str(result["current_before"]),
            branch_exists=bool(result["branch_exists"]),
            worktree_clean=bool(result["worktree_clean"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitSwitchAction):
        try:
            result = switch_git_branch(workspace, action.branch, create=action.create)
        except ValueError as error:
            result = {
                "ok": False,
                "branch": action.branch,
                "create": action.create,
                "current_before": "",
                "current_after": "",
                "status": "",
                "message": str(error),
            }
        return GitSwitchObservation(
            kind="git_switch",
            ok=bool(result["ok"]),
            branch=str(result["branch"]),
            create=bool(result["create"]),
            current_before=str(result["current_before"]),
            current_after=str(result["current_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStageAction):
        try:
            result = preview_stage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return CheckGitStageObservation(
            kind="check_git_stage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStageAction):
        try:
            result = stage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return GitStageObservation(
            kind="git_stage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitUnstageAction):
        try:
            result = preview_unstage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return CheckGitUnstageObservation(
            kind="check_git_unstage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitUnstageAction):
        try:
            result = unstage_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "status": "", "message": str(error)}
        return GitUnstageObservation(
            kind="git_unstage",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitRestoreAction):
        try:
            result = preview_restore_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "diff": "", "status": "", "message": str(error)}
        return CheckGitRestoreObservation(
            kind="check_git_restore",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            diff=str(result["diff"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitRestoreAction):
        try:
            result = restore_git_paths(workspace, action.paths)
        except ValueError as error:
            result = {"ok": False, "paths": action.paths, "diff": "", "status": "", "message": str(error)}
        return GitRestoreObservation(
            kind="git_restore",
            ok=bool(result["ok"]),
            paths=list(result["paths"]),
            diff=str(result["diff"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStashesAction):
        try:
            result = read_git_stashes(workspace, max_entries=action.max_entries)
        except ValueError as error:
            result = {"ok": False, "entries": [], "total": 0, "truncated": False, "message": str(error)}
        entries = [GitStashEntry(**item) for item in result["entries"]]
        return GitStashesObservation(
            kind="git_stashes",
            ok=bool(result["ok"]),
            entries=entries,
            total=int(result["total"]),
            truncated=bool(result["truncated"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStashAction):
        try:
            result = preview_stash_git_changes(workspace, action.message, include_untracked=action.include_untracked)
        except ValueError as error:
            result = {
                "ok": False,
                "message_text": action.message or "",
                "include_untracked": action.include_untracked,
                "status": "",
                "diff": "",
                "message": str(error),
            }
        return CheckGitStashObservation(
            kind="check_git_stash",
            ok=bool(result["ok"]),
            message_text=str(result["message_text"]),
            include_untracked=bool(result["include_untracked"]),
            status=str(result["status"]),
            diff=str(result["diff"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStashAction):
        try:
            result = stash_git_changes(workspace, action.message, include_untracked=action.include_untracked)
        except ValueError as error:
            result = {
                "ok": False,
                "message_text": action.message or "",
                "include_untracked": action.include_untracked,
                "stash_ref": "",
                "status": "",
                "diff": "",
                "message": str(error),
            }
        return GitStashObservation(
            kind="git_stash",
            ok=bool(result["ok"]),
            message_text=str(result["message_text"]),
            include_untracked=bool(result["include_untracked"]),
            stash_ref=str(result["stash_ref"]),
            status=str(result["status"]),
            diff=str(result["diff"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStashApplyAction):
        try:
            result = preview_apply_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {"ok": False, "stash_ref": action.stash_ref, "worktree_clean": False, "patch": "", "status": "", "message": str(error)}
        return CheckGitStashApplyObservation(
            kind="check_git_stash_apply",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            worktree_clean=bool(result["worktree_clean"]),
            patch=str(result["patch"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStashApplyAction):
        try:
            result = apply_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {"ok": False, "stash_ref": action.stash_ref, "patch": "", "status": "", "message": str(error)}
        return GitStashApplyObservation(
            kind="git_stash_apply",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            patch=str(result["patch"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitStashDropAction):
        try:
            result = preview_drop_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {"ok": False, "stash_ref": action.stash_ref, "patch": "", "summary": "", "message": str(error)}
        return CheckGitStashDropObservation(
            kind="check_git_stash_drop",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            patch=str(result["patch"]),
            summary=str(result["summary"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitStashDropAction):
        try:
            result = drop_git_stash(workspace, action.stash_ref)
        except ValueError as error:
            result = {"ok": False, "stash_ref": action.stash_ref, "patch": "", "summary": "", "remaining_total": 0, "message": str(error)}
        return GitStashDropObservation(
            kind="git_stash_drop",
            ok=bool(result["ok"]),
            stash_ref=str(result["stash_ref"]),
            patch=str(result["patch"]),
            summary=str(result["summary"]),
            remaining_total=int(result["remaining_total"]),
            message=str(result["message"]),
        )

    if isinstance(action, CheckGitCommitAction):
        try:
            result = preview_commit_staged_changes(workspace, action.message)
        except ValueError as error:
            result = {"ok": False, "head_before": "", "head_after": "", "status": "", "message": str(error)}
        return CheckGitCommitObservation(
            kind="check_git_commit",
            ok=bool(result["ok"]),
            head_before=str(result["head_before"]),
            head_after=str(result["head_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

    if isinstance(action, GitCommitAction):
        try:
            result = commit_staged_changes(workspace, action.message)
        except ValueError as error:
            result = {"ok": False, "head_before": "", "head_after": "", "status": "", "message": str(error)}
        return GitCommitObservation(
            kind="git_commit",
            ok=bool(result["ok"]),
            head_before=str(result["head_before"]),
            head_after=str(result["head_after"]),
            status=str(result["status"]),
            message=str(result["message"]),
        )

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
        all_suggested_checks = [SuggestedCheck(**item) for item in review["suggested_checks"]]
        suggested_checks = all_suggested_checks[: action.max_checks]
        suggested_checks_total = int(review["suggested_checks_total"])
        suggested_checks_truncated = (
            bool(review["suggested_checks_truncated"])
            or len(all_suggested_checks) > len(suggested_checks)
            or suggested_checks_total > len(suggested_checks)
        )
        running_processes = [process for process in list_background_processes(workspace.root).processes if process.running]
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
        verification_blockers, verification_warnings = final_review_session_verification_issues(
            workspace,
            suggested_checks,
        )
        blocking_issues.extend(verification_blockers)

        warnings: list[str] = []
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
        unavailable = [item for item in suggested_checks if not item.available]
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

    if isinstance(action, SuggestChecksAction):
        try:
            suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
            checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            return SuggestChecksObservation(
                kind="suggest_checks",
                ok=bool(suggestions["ok"]),
                checks=checks,
                total=int(suggestions["total"]),
                truncated=bool(suggestions["truncated"]),
                changed_files=list(suggestions["changed_files"]),
                message=str(suggestions["message"]),
            )
        except ValueError as error:
            return SuggestChecksObservation(
                kind="suggest_checks",
                ok=False,
                checks=[],
                total=0,
                truncated=False,
                changed_files=[],
                message=str(error),
            )

    if isinstance(action, CheckSuggestedChecksAction):
        try:
            suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
            suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            checks = [
                build_command_check_observation(workspace, item.command, item.cwd)
                for item in suggested_checks
            ]
            failed_count = sum(1 for check in checks if not check.ok)
            return CheckSuggestedChecksObservation(
                kind="check_suggested_checks",
                ok=failed_count == 0,
                checks=checks,
                suggested_checks=suggested_checks,
                total=int(suggestions["total"]),
                truncated=bool(suggestions["truncated"]),
                max_commands=action.max_commands,
                message=f"Preflighted {len(checks)}/{int(suggestions['total'])} suggested check command(s); {failed_count} failed.",
            )
        except ValueError as error:
            return CheckSuggestedChecksObservation(
                kind="check_suggested_checks",
                ok=False,
                checks=[],
                suggested_checks=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                message=str(error),
            )

    if isinstance(action, RunSuggestedChecksAction):
        try:
            suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
            suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            runnable_checks = [item for item in suggested_checks if item.available]
            skipped_unavailable = len(suggested_checks) - len(runnable_checks)
            results: list[CommandResult] = []
            stopped_early = False
            for item in runnable_checks:
                result = execute_run_command_item(
                    workspace,
                    RunCommandItem(
                        command=item.command,
                        cwd=item.cwd,
                        timeout_ms=action.timeout_ms,
                        max_output_chars=action.max_output_chars,
                        extract_output_contexts=action.extract_output_contexts,
                        extract_output_diagnostics=action.extract_output_diagnostics,
                        context_lines=action.context_lines,
                        max_diagnostics=action.max_diagnostics,
                        max_contexts=action.max_contexts,
                        max_bytes_per_context=action.max_bytes_per_context,
                    ),
                    command_timeout_ms,
                )
                results.append(result)
                failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
                if failed and action.stop_on_failure:
                    stopped_early = len(results) < len(runnable_checks)
                    break
            ok = (
                skipped_unavailable == 0
                and len(results) == len(runnable_checks)
                and all(result.exit_code == 0 and not result.timed_out for result in results)
            )
            return RunSuggestedChecksObservation(
                kind="run_suggested_checks",
                ok=ok,
                results=results,
                suggested_checks=suggested_checks,
                total=int(suggestions["total"]),
                truncated=bool(suggestions["truncated"]),
                max_commands=action.max_commands,
                stopped_early=stopped_early,
                skipped_unavailable=skipped_unavailable,
                message=(
                    f"Ran {len(results)}/{len(runnable_checks)} available suggested check command(s); "
                    f"{'all passed' if ok else 'one or more failed or were unavailable'}."
                ),
            )
        except ValueError as error:
            return RunSuggestedChecksObservation(
                kind="run_suggested_checks",
                ok=False,
                results=[],
                suggested_checks=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                stopped_early=False,
                skipped_unavailable=0,
                message=str(error),
            )

    if isinstance(action, ProjectCommandsAction):
        try:
            metadata = read_project_commands(
                workspace,
                max_commands=action.max_commands,
                max_files=action.max_files,
            )
            commands = [ProjectCommand(**item) for item in metadata["commands"]]
            return ProjectCommandsObservation(
                kind="project_commands",
                ok=bool(metadata["ok"]),
                commands=commands,
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectCommandsObservation(
                kind="project_commands",
                ok=False,
                commands=[],
                total=0,
                truncated=False,
                total_files=0,
                scanned_files=0,
                message=str(error),
            )

    if isinstance(action, RelatedTestsAction):
        try:
            metadata = find_related_tests(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
            )
            candidates = [RelatedTestCandidate(**item) for item in metadata["candidates"]]
            return RelatedTestsObservation(
                kind="related_tests",
                ok=bool(metadata["ok"]),
                target_paths=list(metadata["target_paths"]),
                candidates=candidates,
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                test_files_total=int(metadata["test_files_total"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return RelatedTestsObservation(
                kind="related_tests",
                ok=False,
                target_paths=[],
                candidates=[],
                total=0,
                truncated=False,
                test_files_total=0,
                message=str(error),
            )

    if isinstance(action, FocusedTestCommandsAction):
        try:
            metadata = suggest_focused_test_commands(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
                max_commands=action.max_commands,
            )
            commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
            return FocusedTestCommandsObservation(
                kind="focused_test_commands",
                ok=bool(metadata["ok"]),
                target_paths=list(metadata["target_paths"]),
                commands=commands,
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                related_tests_total=int(metadata["related_tests_total"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return FocusedTestCommandsObservation(
                kind="focused_test_commands",
                ok=False,
                target_paths=[],
                commands=[],
                total=0,
                truncated=False,
                related_tests_total=0,
                message=str(error),
            )

    if isinstance(action, CheckFocusedTestCommandsAction):
        try:
            if action.max_commands > 50:
                raise ValueError("max_commands must be at most 50")
            metadata = suggest_focused_test_commands(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
                max_commands=action.max_commands,
            )
            focused_commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
            checks = [
                build_command_check_observation(workspace, item.command, item.cwd)
                for item in focused_commands
            ]
            failed_count = sum(1 for check in checks if not check.ok)
            return CheckFocusedTestCommandsObservation(
                kind="check_focused_test_commands",
                ok=failed_count == 0,
                checks=checks,
                focused_commands=focused_commands,
                target_paths=list(metadata["target_paths"]),
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                max_commands=action.max_commands,
                related_tests_total=int(metadata["related_tests_total"]),
                message=f"Preflighted {len(checks)}/{int(metadata['total'])} focused test command(s); {failed_count} failed.",
            )
        except ValueError as error:
            return CheckFocusedTestCommandsObservation(
                kind="check_focused_test_commands",
                ok=False,
                checks=[],
                focused_commands=[],
                target_paths=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                related_tests_total=0,
                message=str(error),
            )

    if isinstance(action, RunFocusedTestCommandsAction):
        try:
            if action.max_commands > 50:
                raise ValueError("max_commands must be at most 50")
            metadata = suggest_focused_test_commands(
                workspace,
                paths=action.paths,
                max_paths=action.max_paths,
                max_candidates=action.max_candidates,
                max_commands=action.max_commands,
            )
            focused_commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
            runnable_commands = [item for item in focused_commands if item.available]
            skipped_unavailable = len(focused_commands) - len(runnable_commands)
            results: list[CommandResult] = []
            stopped_early = False
            for item in runnable_commands:
                result = execute_run_command_item(
                    workspace,
                    RunCommandItem(
                        command=item.command,
                        cwd=item.cwd,
                        timeout_ms=action.timeout_ms,
                        max_output_chars=action.max_output_chars,
                        extract_output_contexts=action.extract_output_contexts,
                        extract_output_diagnostics=action.extract_output_diagnostics,
                        context_lines=action.context_lines,
                        max_diagnostics=action.max_diagnostics,
                        max_contexts=action.max_contexts,
                        max_bytes_per_context=action.max_bytes_per_context,
                    ),
                    command_timeout_ms,
                )
                results.append(result)
                failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
                if failed and action.stop_on_failure:
                    stopped_early = len(results) < len(runnable_commands)
                    break
            ok = (
                skipped_unavailable == 0
                and len(results) == len(runnable_commands)
                and all(result.exit_code == 0 and not result.timed_out for result in results)
            )
            return RunFocusedTestCommandsObservation(
                kind="run_focused_test_commands",
                ok=ok,
                results=results,
                focused_commands=focused_commands,
                target_paths=list(metadata["target_paths"]),
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                max_commands=action.max_commands,
                related_tests_total=int(metadata["related_tests_total"]),
                stopped_early=stopped_early,
                skipped_unavailable=skipped_unavailable,
                message=(
                    f"Ran {len(results)}/{len(runnable_commands)} available focused test command(s); "
                    f"{'all passed' if ok else 'one or more failed or were unavailable'}."
                ),
            )
        except ValueError as error:
            return RunFocusedTestCommandsObservation(
                kind="run_focused_test_commands",
                ok=False,
                results=[],
                focused_commands=[],
                target_paths=[],
                total=0,
                truncated=False,
                max_commands=action.max_commands,
                related_tests_total=0,
                stopped_early=False,
                skipped_unavailable=0,
                message=str(error),
            )

    if isinstance(action, ProjectManifestsAction):
        try:
            metadata = read_project_manifests(
                workspace,
                max_files=action.max_files,
                max_items=action.max_items,
            )
            manifests = [
                ProjectManifest(
                    path=str(item["path"]),
                    kind=str(item["kind"]),
                    ok=bool(item["ok"]),
                    name=str(item["name"]),
                    version=str(item["version"]),
                    items=[ProjectManifestItem(**manifest_item) for manifest_item in item["items"]],
                    item_count=int(item["item_count"]),
                    truncated=bool(item["truncated"]),
                    message=str(item["message"]),
                )
                for item in metadata["manifests"]
            ]
            return ProjectManifestsObservation(
                kind="project_manifests",
                ok=bool(metadata["ok"]),
                manifests=manifests,
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                total_items=int(metadata["total_items"]),
                truncated=bool(metadata["truncated"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectManifestsObservation(
                kind="project_manifests",
                ok=False,
                manifests=[],
                total_files=0,
                scanned_files=0,
                total_items=0,
                truncated=False,
                message=str(error),
            )

    if isinstance(action, ProjectInstructionsAction):
        try:
            if action.max_bytes < 200:
                raise ValueError("max_bytes must be at least 200.")
            metadata = read_project_instruction_sources(
                workspace,
                max_files=action.max_files,
                max_bytes=action.max_bytes,
            )
            files = [ProjectInstructionSource(**item) for item in metadata["files"]]
            return ProjectInstructionsObservation(
                kind="project_instructions",
                ok=bool(metadata["ok"]),
                files=files,
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                omitted_files=int(metadata["omitted_files"]),
                truncated=bool(metadata["truncated"]),
                text=str(metadata["text"]),
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectInstructionsObservation(
                kind="project_instructions",
                ok=False,
                files=[],
                total_files=0,
                scanned_files=0,
                omitted_files=0,
                truncated=False,
                text="",
                message=str(error),
            )

    if isinstance(action, ProjectTodosAction):
        try:
            metadata = read_project_todos(
                workspace,
                relative_path=action.path,
                max_items=action.max_items,
                max_files=action.max_files,
            )
            return ProjectTodosObservation(
                kind="project_todos",
                ok=bool(metadata["ok"]),
                todos=[ProjectTodo(**item) for item in metadata["todos"]],
                total=int(metadata["total"]),
                truncated=bool(metadata["truncated"]),
                total_files=int(metadata["total_files"]),
                scanned_files=int(metadata["scanned_files"]),
                path=str(metadata["path"]),
                markers=[str(item) for item in metadata["markers"]],
                message=str(metadata["message"]),
            )
        except ValueError as error:
            return ProjectTodosObservation(
                kind="project_todos",
                ok=False,
                todos=[],
                total=0,
                truncated=False,
                total_files=0,
                scanned_files=0,
                path=action.path or ".",
                markers=[],
                message=str(error),
            )

    if isinstance(action, ProjectOverviewAction):
        try:
            repo_map = build_repo_map(workspace, max_depth=2, max_files=action.max_files, max_symbols=80)
            git_info = read_git_info(workspace)
            commands_metadata = read_project_commands(
                workspace,
                max_commands=action.max_commands,
                max_files=action.max_manifests,
            )
            manifests_metadata = read_project_manifests(
                workspace,
                max_files=action.max_manifests,
                max_items=200,
            )
            suggestions = suggest_project_checks(workspace, max_commands=action.max_checks)
            environment = read_environment_info(workspace)
            commands = [ProjectCommand(**item) for item in commands_metadata["commands"]]
            manifests = [
                ProjectManifest(
                    path=str(item["path"]),
                    kind=str(item["kind"]),
                    ok=bool(item["ok"]),
                    name=str(item["name"]),
                    version=str(item["version"]),
                    items=[ProjectManifestItem(**manifest_item) for manifest_item in item["items"]],
                    item_count=int(item["item_count"]),
                    truncated=bool(item["truncated"]),
                    message=str(item["message"]),
                )
                for item in manifests_metadata["manifests"]
            ]
            suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
            tools = [RuntimeToolInfo(**item) for item in environment["tools"]]
            return ProjectOverviewObservation(
                kind="project_overview",
                ok=True,
                project_root=str(environment["project_root"]),
                is_git_repo=bool(git_info["is_git_repo"]),
                git_branch=str(git_info["branch"]),
                git_head=str(git_info["head"]),
                git_upstream=str(git_info["upstream"]),
                git_ahead=int(git_info["ahead"]),
                git_behind=int(git_info["behind"]),
                git_status=str(git_info["status"]),
                tree=list(repo_map["tree"]),
                files=list(repo_map["files"]),
                total_tree_entries=int(repo_map["total_tree_entries"]),
                total_files=int(repo_map["total_files"]),
                repo_truncated=bool(repo_map["truncated"]),
                commands=commands,
                commands_total=int(commands_metadata["total"]),
                commands_truncated=bool(commands_metadata["truncated"]),
                manifests=manifests,
                manifest_files_total=int(manifests_metadata["total_files"]),
                manifests_truncated=bool(manifests_metadata["truncated"]),
                suggested_checks=suggested_checks,
                suggested_checks_total=int(suggestions["total"]),
                suggested_checks_truncated=bool(suggestions["truncated"]),
                tools=tools,
                message=(
                    f"Project overview: {int(repo_map['total_files'])} file(s), "
                    f"{int(commands_metadata['total'])} command(s), "
                    f"{int(manifests_metadata['total_files'])} manifest file(s)."
                ),
            )
        except ValueError as error:
            return ProjectOverviewObservation(
                kind="project_overview",
                ok=False,
                project_root=workspace.root.as_posix(),
                is_git_repo=False,
                git_branch="",
                git_head="",
                git_upstream="",
                git_ahead=0,
                git_behind=0,
                git_status="",
                tree=[],
                files=[],
                total_tree_entries=0,
                total_files=0,
                repo_truncated=False,
                commands=[],
                commands_total=0,
                commands_truncated=False,
                manifests=[],
                manifest_files_total=0,
                manifests_truncated=False,
                suggested_checks=[],
                suggested_checks_total=0,
                suggested_checks_truncated=False,
                tools=[],
                message=str(error),
            )

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

    if isinstance(action, GitDiffAction):
        try:
            result = read_git_diff(workspace, action.path, action.staged)
        except ValueError as error:
            return GitDiffObservation(
                kind="git_diff",
                ok=False,
                diff="",
                path=action.path,
                staged=action.staged,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        diff, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git diff." if result.ok else result.stderr or "git diff failed."
        return GitDiffObservation(
            kind="git_diff",
            ok=result.ok,
            diff=diff,
            path=action.path,
            staged=action.staged,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    if isinstance(action, GitDiffHunksAction):
        try:
            summary = read_git_diff_hunks(
                workspace,
                action.path,
                action.staged,
                max_hunks=action.max_hunks,
                max_lines_per_hunk=action.max_lines_per_hunk,
            )
            hunks = [GitDiffHunk(**item) for item in summary["hunks"]]
            return GitDiffHunksObservation(
                kind="git_diff_hunks",
                ok=bool(summary["ok"]),
                hunks=hunks,
                total_hunks=int(summary["total_hunks"]),
                truncated=bool(summary["truncated"]),
                path=action.path,
                staged=action.staged,
                message=str(summary["message"]),
            )
        except ValueError as error:
            return GitDiffHunksObservation(
                kind="git_diff_hunks",
                ok=False,
                hunks=[],
                total_hunks=0,
                truncated=False,
                path=action.path,
                staged=action.staged,
                message=str(error),
            )

    if isinstance(action, GitDiffContextsAction):
        try:
            summary = read_git_diff_hunks(
                workspace,
                action.path,
                action.staged,
                max_hunks=action.max_hunks,
                max_lines_per_hunk=1,
            )
            contexts: list[GitDiffContext] = []
            for item in summary["hunks"]:
                hunk = GitDiffHunk(**item)
                try:
                    result = read_project_file_context_result(
                        workspace,
                        hunk.file,
                        line=max(1, hunk.new_start),
                        context_lines=action.context_lines,
                        max_bytes=action.max_bytes_per_context,
                    )
                    context = ReadFileContextResult(
                        path=hunk.file,
                        line=int(result["line"]),
                        context_lines=int(result["context_lines"]),
                        ok=True,
                        content=str(result["content"]),
                        message=f"Read {hunk.file} around diff hunk line {hunk.new_start}.",
                        start_line=int(result["start_line"]),
                        end_line=int(result["end_line"]),
                        line_count=int(result["line_count"]),
                        total_lines=int(result["total_lines"]),
                        target_line_exists=bool(result["target_line_exists"]),
                        truncated=bool(result["truncated"]),
                        max_bytes=int(result["max_bytes"]),
                    )
                except ValueError as error:
                    context = ReadFileContextResult(
                        path=hunk.file,
                        line=max(1, hunk.new_start),
                        context_lines=action.context_lines,
                        ok=False,
                        content="",
                        message=str(error),
                        max_bytes=action.max_bytes_per_context,
                    )
                contexts.append(GitDiffContext(hunk=hunk, context=context))
            return GitDiffContextsObservation(
                kind="git_diff_contexts",
                ok=bool(summary["ok"]),
                contexts=contexts,
                total_hunks=int(summary["total_hunks"]),
                truncated=bool(summary["truncated"]),
                path=action.path,
                staged=action.staged,
                context_lines=action.context_lines,
                message=str(summary["message"]),
            )
        except ValueError as error:
            return GitDiffContextsObservation(
                kind="git_diff_contexts",
                ok=False,
                contexts=[],
                total_hunks=0,
                truncated=False,
                path=action.path,
                staged=action.staged,
                context_lines=action.context_lines,
                message=str(error),
            )

    if isinstance(action, GitLogAction):
        try:
            result = read_git_log(workspace, action.max_count, action.path)
        except ValueError as error:
            return GitLogObservation(
                kind="git_log",
                ok=False,
                log="",
                max_count=action.max_count,
                path=action.path,
                message=str(error),
            )
        message = "Read git log." if result.ok else result.stderr or "git log failed."
        return GitLogObservation(
            kind="git_log",
            ok=result.ok,
            log=result.stdout,
            max_count=action.max_count,
            path=action.path,
            message=message,
        )

    if isinstance(action, GitShowAction):
        try:
            result = read_git_show(workspace, action.rev, action.path)
        except ValueError as error:
            return GitShowObservation(
                kind="git_show",
                ok=False,
                output="",
                rev=action.rev,
                path=action.path,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        output, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git show." if result.ok else result.stderr or "git show failed."
        return GitShowObservation(
            kind="git_show",
            ok=result.ok,
            output=output,
            rev=action.rev,
            path=action.path,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    if isinstance(action, GitBlameAction):
        try:
            result = read_git_blame(workspace, action.path, action.start_line, action.line_count)
        except ValueError as error:
            return GitBlameObservation(
                kind="git_blame",
                ok=False,
                blame="",
                path=action.path,
                start_line=action.start_line,
                line_count=action.line_count,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        blame, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git blame." if result.ok else result.stderr or "git blame failed."
        return GitBlameObservation(
            kind="git_blame",
            ok=result.ok,
            blame=blame,
            path=action.path,
            start_line=action.start_line,
            line_count=action.line_count,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    if isinstance(action, SessionSummaryAction):
        run_id = action.run_id or workspace.run_id
        try:
            summary_text = format_session_summary(summarize_session(workspace.root, run_id))
            ok = not summary_text.startswith("Session not found:")
            message = f"Read session summary for {run_id}." if ok else summary_text
        except ValueError as error:
            summary_text = ""
            ok = False
            message = str(error)
        recent_text = format_sessions(workspace.root, limit=action.recent_limit)
        return SessionSummaryObservation(
            kind="session_summary",
            run_id=run_id,
            ok=ok,
            summary=summary_text,
            recent_sessions=recent_text.splitlines(),
            message=message,
        )

    if isinstance(action, SessionPlanAction):
        run_id = action.run_id or workspace.run_id
        try:
            plan_text = format_session_plan(summarize_session(workspace.root, run_id))
            ok = not plan_text.startswith("Session not found:")
            message = f"Read session plan for {run_id}." if ok else plan_text
        except ValueError as error:
            plan_text = ""
            ok = False
            message = str(error)
        return SessionPlanObservation(
            kind="session_plan",
            run_id=run_id,
            ok=ok,
            plan=plan_text,
            message=message,
        )

    if isinstance(action, SessionTranscriptAction):
        run_id = action.run_id or workspace.run_id
        try:
            transcript = format_session_transcript(
                workspace.root,
                run_id,
                max_events=action.max_events,
                max_text=action.max_text,
            )
            ok = not transcript.startswith("Session not found:")
            message = f"Read session transcript for {run_id}." if ok else transcript
        except ValueError as error:
            transcript = ""
            ok = False
            message = str(error)
        return SessionTranscriptObservation(
            kind="session_transcript",
            run_id=run_id,
            ok=ok,
            transcript=transcript,
            message=message,
        )

    if isinstance(action, SessionSearchAction):
        run_id = action.run_id or workspace.run_id
        try:
            matches = format_session_search(
                workspace.root,
                run_id,
                action.query,
                max_matches=action.max_matches,
                max_text=action.max_text,
                case_sensitive=action.case_sensitive,
            )
            ok = not matches.startswith("Session not found:")
            message = f"Searched session {run_id} for {action.query!r}." if ok else matches
            total_matches, shown_matches = parse_session_search_counts(matches)
        except ValueError as error:
            matches = ""
            ok = False
            message = str(error)
            total_matches = 0
            shown_matches = 0
        return SessionSearchObservation(
            kind="session_search",
            run_id=run_id,
            ok=ok,
            query=action.query,
            matches=matches,
            total_matches=total_matches,
            shown_matches=shown_matches,
            message=message,
        )

    if isinstance(action, SessionCommandsAction):
        run_id = action.run_id or workspace.run_id
        try:
            commands = format_session_commands(
                workspace.root,
                run_id,
                max_commands=action.max_commands,
                max_output_chars=action.max_output_chars,
            )
            ok = not commands.startswith("Session not found:")
            message = f"Read session command results for {run_id}." if ok else commands
            command_count, shown_commands = parse_session_commands_counts(commands)
        except ValueError as error:
            commands = ""
            ok = False
            message = str(error)
            command_count = 0
            shown_commands = 0
        return SessionCommandsObservation(
            kind="session_commands",
            run_id=run_id,
            ok=ok,
            commands=commands,
            command_count=command_count,
            shown_commands=shown_commands,
            message=message,
        )

    if isinstance(action, SessionOutputContextsAction):
        run_id = action.run_id or workspace.run_id
        try:
            ok, command_count, shown_commands, output_text, scan_message = build_session_command_output_scan_text(
                workspace,
                run_id,
                max_commands=action.max_commands,
                max_output_chars=action.max_output_chars,
            )
            if not ok:
                return SessionOutputContextsObservation(
                    kind="session_output_contexts",
                    run_id=run_id,
                    ok=False,
                    contexts=[],
                    command_count=0,
                    shown_commands=0,
                    total_refs=0,
                    truncated=False,
                    message=scan_message,
                )
            if not output_text.strip():
                return SessionOutputContextsObservation(
                    kind="session_output_contexts",
                    run_id=run_id,
                    ok=True,
                    contexts=[],
                    command_count=command_count,
                    shown_commands=shown_commands,
                    total_refs=0,
                    truncated=False,
                    message=f"{scan_message} No command output references found.",
                )
            result = read_output_contexts_result(
                workspace,
                output_text,
                context_lines=action.context_lines,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
            contexts = output_context_results_from_dicts(result["contexts"])
            failed_contexts = sum(1 for item in contexts if not item.ok)
            return SessionOutputContextsObservation(
                kind="session_output_contexts",
                run_id=run_id,
                ok=failed_contexts == 0,
                contexts=contexts,
                command_count=command_count,
                shown_commands=shown_commands,
                total_refs=int(result["total_refs"]),
                truncated=bool(result["truncated"]),
                message=f"{scan_message} {result['message']}",
            )
        except ValueError as error:
            return SessionOutputContextsObservation(
                kind="session_output_contexts",
                run_id=run_id,
                ok=False,
                contexts=[],
                command_count=0,
                shown_commands=0,
                total_refs=0,
                truncated=False,
                message=str(error),
            )

    if isinstance(action, SessionOutputDiagnosticsAction):
        run_id = action.run_id or workspace.run_id
        try:
            ok, command_count, shown_commands, output_text, scan_message = build_session_command_output_scan_text(
                workspace,
                run_id,
                max_commands=action.max_commands,
                max_output_chars=action.max_output_chars,
            )
            if not ok:
                return SessionOutputDiagnosticsObservation(
                    kind="session_output_diagnostics",
                    run_id=run_id,
                    ok=False,
                    diagnostics=[],
                    contexts=[],
                    command_count=0,
                    shown_commands=0,
                    total_diagnostics=0,
                    total_refs=0,
                    diagnostics_truncated=False,
                    contexts_truncated=False,
                    message=scan_message,
                )
            if not output_text.strip():
                return SessionOutputDiagnosticsObservation(
                    kind="session_output_diagnostics",
                    run_id=run_id,
                    ok=True,
                    diagnostics=[],
                    contexts=[],
                    command_count=command_count,
                    shown_commands=shown_commands,
                    total_diagnostics=0,
                    total_refs=0,
                    diagnostics_truncated=False,
                    contexts_truncated=False,
                    message=f"{scan_message} No command output diagnostics found.",
                )
            result = read_output_diagnostics_result(
                workspace,
                output_text,
                context_lines=action.context_lines,
                max_diagnostics=action.max_diagnostics,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
            diagnostics = output_diagnostics_from_dicts(result["diagnostics"])
            contexts = output_context_results_from_dicts(result["contexts"])
            failed_contexts = sum(1 for item in contexts if not item.ok)
            return SessionOutputDiagnosticsObservation(
                kind="session_output_diagnostics",
                run_id=run_id,
                ok=failed_contexts == 0,
                diagnostics=diagnostics,
                contexts=contexts,
                command_count=command_count,
                shown_commands=shown_commands,
                total_diagnostics=int(result["total_diagnostics"]),
                total_refs=int(result["total_refs"]),
                diagnostics_truncated=bool(result["diagnostics_truncated"]),
                contexts_truncated=bool(result["contexts_truncated"]),
                message=f"{scan_message} {result['message']}",
            )
        except ValueError as error:
            return SessionOutputDiagnosticsObservation(
                kind="session_output_diagnostics",
                run_id=run_id,
                ok=False,
                diagnostics=[],
                contexts=[],
                command_count=0,
                shown_commands=0,
                total_diagnostics=0,
                total_refs=0,
                diagnostics_truncated=False,
                contexts_truncated=False,
                message=str(error),
            )

    if isinstance(action, SessionFilesAction):
        run_id = action.run_id or workspace.run_id
        try:
            files = format_session_files(workspace.root, run_id, max_files=action.max_files)
            ok = not files.startswith("Session not found:")
            message = f"Read session file references for {run_id}." if ok else files
            file_count, shown_files = parse_session_files_counts(files)
        except ValueError as error:
            files = ""
            ok = False
            message = str(error)
            file_count = 0
            shown_files = 0
        return SessionFilesObservation(
            kind="session_files",
            run_id=run_id,
            ok=ok,
            files=files,
            file_count=file_count,
            shown_files=shown_files,
            message=message,
        )

    if isinstance(action, SessionFailuresAction):
        run_id = action.run_id or workspace.run_id
        try:
            failures = format_session_failures(
                workspace.root,
                run_id,
                max_failures=action.max_failures,
                max_text=action.max_text,
            )
            ok = not failures.startswith("Session not found:")
            message = f"Read session failures for {run_id}." if ok else failures
            failure_count, shown_failures = parse_session_failures_counts(failures)
        except ValueError as error:
            failures = ""
            ok = False
            message = str(error)
            failure_count = 0
            shown_failures = 0
        return SessionFailuresObservation(
            kind="session_failures",
            run_id=run_id,
            ok=ok,
            failures=failures,
            failure_count=failure_count,
            shown_failures=shown_failures,
            message=message,
        )

    if isinstance(action, SessionVerificationAction):
        run_id = action.run_id or workspace.run_id
        try:
            summary = summarize_session(workspace.root, run_id)
            verification = format_session_verification(summary, max_checks=action.max_checks)
            ok = not verification.startswith("Session not found:")
            message = f"Read session verification for {run_id}." if ok else verification
        except ValueError as error:
            verification = ""
            ok = False
            message = str(error)
        return SessionVerificationObservation(
            kind="session_verification",
            run_id=run_id,
            ok=ok,
            verification=verification,
            message=message,
        )

    if isinstance(action, SessionAuditAction):
        run_id = action.run_id or workspace.run_id
        try:
            audit = format_session_audit(
                workspace.root,
                run_id,
                max_failures=action.max_failures,
                max_files=action.max_files,
                max_commands=action.max_commands,
                max_checks=action.max_checks,
                max_text=action.max_text,
            )
            ok = not audit.startswith("Session not found:")
            ready = "\n  ready: yes\n" in f"\n{audit}\n"
            message = f"Read session audit for {run_id}." if ok else audit
            blockers: list[str] = []
            background_processes_started = 0
            active_background_processes: list[SessionAuditProcess] = []
            if ok:
                summary = summarize_session(workspace.root, run_id)
                events = read_session_events(workspace.root, run_id)
                failures = session_failure_entries(events, max_text=action.max_text)
                files = session_file_entries(events)
                blockers = session_audit_blockers(summary, failures, files)
                background_processes_started = summary.background_processes_started
                active_background_processes = [
                    SessionAuditProcess(
                        process_id=process.process_id,
                        pid=process.pid,
                        command=process.command,
                        cwd=process.cwd,
                        line_number=process.line_number,
                    )
                    for process in summary.active_background_processes
                ]
        except ValueError as error:
            audit = ""
            ok = False
            ready = False
            blockers = []
            background_processes_started = 0
            active_background_processes = []
            message = str(error)
        return SessionAuditObservation(
            kind="session_audit",
            run_id=run_id,
            ok=ok,
            audit=audit,
            ready=ready,
            blockers=blockers,
            background_processes_started=background_processes_started,
            active_background_processes=active_background_processes,
            message=message,
        )

    if isinstance(action, SessionHandoffAction):
        run_id = action.run_id or workspace.run_id
        try:
            handoff = format_session_handoff(
                workspace.root,
                run_id,
                max_failures=action.max_failures,
                max_files=action.max_files,
                max_commands=action.max_commands,
                max_checks=action.max_checks,
                max_output_chars=action.max_output_chars,
                max_text=action.max_text,
            )
            ok = not handoff.startswith("Session not found:")
            message = f"Read session handoff for {run_id}." if ok else handoff
        except ValueError as error:
            handoff = ""
            ok = False
            message = str(error)
        return SessionHandoffObservation(
            kind="session_handoff",
            run_id=run_id,
            ok=ok,
            handoff=handoff,
            message=message,
        )

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

    if isinstance(action, CheckEditFileAction):
        try:
            _, diff = preview_edit_project_file(workspace, action.path, action.old, action.new)
            ok = True
            message = f"Edit can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckEditFileObservation(
            kind="check_edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, EditFileAction):
        try:
            _, diff = edit_project_file(workspace, action.path, action.old, action.new)
            ok = True
            message = f"Edited {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return EditFileObservation(
            kind="edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckMultiEditAction):
        try:
            _, diff = preview_multi_edit_project_file(
                workspace,
                action.path,
                [(edit.old, edit.new) for edit in action.edits],
            )
            ok = True
            message = f"Multi-edit can apply {len(action.edits)} edit(s) to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckMultiEditObservation(
            kind="check_multi_edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, MultiEditAction):
        try:
            _, diff = multi_edit_project_file(
                workspace,
                action.path,
                [(edit.old, edit.new) for edit in action.edits],
            )
            ok = True
            message = f"Applied {len(action.edits)} edit(s) to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return MultiEditObservation(
            kind="multi_edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckReplaceLinesAction):
        try:
            _, diff = preview_replace_project_file_lines(
                workspace,
                action.path,
                action.start_line,
                action.end_line,
                action.content,
            )
            ok = True
            message = f"Line replacement can apply to lines {action.start_line}-{action.end_line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckReplaceLinesObservation(
            kind="check_replace_lines",
            path=action.path,
            start_line=action.start_line,
            end_line=action.end_line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, ReplaceLinesAction):
        try:
            _, diff = replace_project_file_lines(
                workspace,
                action.path,
                action.start_line,
                action.end_line,
                action.content,
            )
            ok = True
            message = f"Replaced lines {action.start_line}-{action.end_line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return ReplaceLinesObservation(
            kind="replace_lines",
            path=action.path,
            start_line=action.start_line,
            end_line=action.end_line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckInsertLinesAction):
        try:
            _, diff = preview_insert_project_file_lines(workspace, action.path, action.line, action.content)
            ok = True
            message = f"Line insertion can apply before line {action.line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckInsertLinesObservation(
            kind="check_insert_lines",
            path=action.path,
            line=action.line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, InsertLinesAction):
        try:
            _, diff = insert_project_file_lines(workspace, action.path, action.line, action.content)
            ok = True
            message = f"Inserted lines before line {action.line} in {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return InsertLinesObservation(
            kind="insert_lines",
            path=action.path,
            line=action.line,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckAppendFileAction):
        try:
            _, diff = preview_append_project_file(workspace, action.path, action.content)
            ok = True
            message = f"Append can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckAppendFileObservation(
            kind="check_append_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, AppendFileAction):
        try:
            _, diff = append_project_file(workspace, action.path, action.content)
            ok = True
            message = f"Appended to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return AppendFileObservation(
            kind="append_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckRegexReplaceAction):
        try:
            _, replacements, diff = preview_regex_replace_project_file(
                workspace,
                action.path,
                action.pattern,
                action.replacement,
                count=action.count,
                case_sensitive=action.case_sensitive,
                multiline=action.multiline,
                max_replacements=action.max_replacements,
            )
            ok = True
            message = f"Regex replacement can apply to {replacements} match(es) in {action.path}."
        except ValueError as error:
            replacements = 0
            diff = ""
            ok = False
            message = str(error)
        return CheckRegexReplaceObservation(
            kind="check_regex_replace",
            path=action.path,
            pattern=action.pattern,
            count=action.count,
            replacements=replacements,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, RegexReplaceAction):
        try:
            _, replacements, diff = regex_replace_project_file(
                workspace,
                action.path,
                action.pattern,
                action.replacement,
                count=action.count,
                case_sensitive=action.case_sensitive,
                multiline=action.multiline,
                max_replacements=action.max_replacements,
            )
            ok = True
            message = f"Applied {replacements} regex replacement(s) in {action.path}."
        except ValueError as error:
            replacements = 0
            diff = ""
            ok = False
            message = str(error)
        return RegexReplaceObservation(
            kind="regex_replace",
            path=action.path,
            pattern=action.pattern,
            count=action.count,
            replacements=replacements,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckPatchAction):
        try:
            _, diff = check_project_patch(workspace, action.path, action.patch)
            ok = True
            message = f"Patch can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckPatchObservation(
            kind="check_patch",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckPatchesAction):
        try:
            paths, diff = check_project_patches(workspace, action.patch)
            files = [path.relative_to(workspace.root).as_posix() for path in paths]
            ok = True
            message = f"Patches can apply to {len(files)} file(s)."
        except ValueError as error:
            files = []
            diff = ""
            ok = False
            message = str(error)
        return CheckPatchesObservation(
            kind="check_patches",
            files=files,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, PatchFileAction):
        try:
            _, diff = patch_project_file(workspace, action.path, action.patch)
            ok = True
            message = f"Patched {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return PatchFileObservation(
            kind="patch_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, PatchFilesAction):
        try:
            paths, diff = patch_project_files(workspace, action.patch)
            files = [path.relative_to(workspace.root).as_posix() for path in paths]
            ok = True
            message = f"Patched {len(files)} file(s)."
        except ValueError as error:
            files = []
            diff = ""
            ok = False
            message = str(error)
        return PatchFilesObservation(
            kind="patch_files",
            files=files,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckWriteFileAction):
        try:
            _, diff = preview_write_run_file(workspace, action.path, action.content)
            return CheckWriteFileObservation(
                kind="check_write_file",
                path=action.path,
                ok=True,
                message=f"Write can apply to {action.path}.",
                diff=diff,
            )
        except ValueError as error:
            return CheckWriteFileObservation(
                kind="check_write_file",
                path=action.path,
                ok=False,
                message=str(error),
                diff="",
            )

    if isinstance(action, WriteFileAction):
        try:
            write_run_file(workspace, action.path, action.content)
            return WriteFileObservation(kind="write_file", path=action.path, ok=True, message=f"Wrote {action.path}")
        except ValueError as error:
            return WriteFileObservation(kind="write_file", path=action.path, ok=False, message=str(error))

    if isinstance(action, CheckWriteFilesAction):
        try:
            previews = preview_write_run_files(workspace, [(file.path, file.content) for file in action.files])
            files = [
                CheckWriteFileResult(path=relative_path, ok=True, message=f"Write can apply to {relative_path}.", diff=diff)
                for relative_path, _target, diff in previews
            ]
            return CheckWriteFilesObservation(
                kind="check_write_files",
                files=files,
                ok=True,
                message=f"Write can apply to {len(files)} file(s).",
            )
        except ValueError as error:
            files = [
                CheckWriteFileResult(path=file.path, ok=False, message=str(error), diff="")
                for file in action.files
            ]
            return CheckWriteFilesObservation(
                kind="check_write_files",
                files=files,
                ok=False,
                message=str(error),
            )

    if isinstance(action, WriteFilesAction):
        try:
            write_run_files(workspace, [(file.path, file.content) for file in action.files])
            files = [WriteFileResult(path=file.path, ok=True, message=f"Wrote {file.path}") for file in action.files]
            return WriteFilesObservation(
                kind="write_files",
                files=files,
                ok=True,
                message=f"Wrote {len(files)} file(s).",
            )
        except ValueError as error:
            files = [WriteFileResult(path=file.path, ok=False, message=str(error)) for file in action.files]
            return WriteFilesObservation(
                kind="write_files",
                files=files,
                ok=False,
                message=str(error),
            )

    if isinstance(action, CheckDeleteFileAction):
        try:
            _, diff = preview_delete_project_file(workspace, action.path)
            ok = True
            message = f"Delete can apply to {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckDeleteFileObservation(
            kind="check_delete_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, DeleteFileAction):
        try:
            _, diff = delete_project_file(workspace, action.path)
            ok = True
            message = f"Deleted {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return DeleteFileObservation(
            kind="delete_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckDeleteFilesAction):
        try:
            _, diff = preview_delete_project_files(workspace, action.paths)
            ok = True
            message = f"Delete can apply to {len(action.paths)} file(s)."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return CheckDeleteFilesObservation(
            kind="check_delete_files",
            paths=action.paths,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, DeleteFilesAction):
        try:
            _, diff = delete_project_files(workspace, action.paths)
            ok = True
            message = f"Deleted {len(action.paths)} file(s)."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return DeleteFilesObservation(
            kind="delete_files",
            paths=action.paths,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, CheckMoveFileAction):
        try:
            preview_move_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Move can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveFileObservation(
            kind="check_move_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveFileAction):
        try:
            move_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Moved {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveFileObservation(
            kind="move_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveFilesAction):
        try:
            preview_move_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Move can apply to {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveFilesObservation(
            kind="check_move_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveFilesAction):
        try:
            move_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Moved {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveFilesObservation(
            kind="move_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyFileAction):
        try:
            preview_copy_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Copy can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyFileObservation(
            kind="check_copy_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyFileAction):
        try:
            copy_project_file(workspace, action.source, action.destination)
            ok = True
            message = f"Copied {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyFileObservation(
            kind="copy_file",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyFilesAction):
        try:
            preview_copy_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Copy can apply to {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyFilesObservation(
            kind="check_copy_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyFilesAction):
        try:
            copy_project_files(workspace, [transfer.__dict__ for transfer in action.transfers])
            ok = True
            message = f"Copied {len(action.transfers)} file(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyFilesObservation(
            kind="copy_files",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveDirectoryAction):
        try:
            preview_move_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Directory move can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveDirectoryObservation(
            kind="check_move_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveDirectoryAction):
        try:
            move_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Moved directory {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveDirectoryObservation(
            kind="move_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckMoveDirectoriesAction):
        try:
            preview_move_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Directory move can apply to {len(action.transfers)} transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckMoveDirectoriesObservation(
            kind="check_move_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, MoveDirectoriesAction):
        try:
            move_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Moved {len(action.transfers)} directory transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return MoveDirectoriesObservation(
            kind="move_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyDirectoryAction):
        try:
            preview_copy_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Directory copy can apply from {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyDirectoryObservation(
            kind="check_copy_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCopyDirectoriesAction):
        try:
            preview_copy_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Directory copy can apply to {len(action.transfers)} transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCopyDirectoriesObservation(
            kind="check_copy_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyDirectoryAction):
        try:
            copy_project_directory(workspace, action.source, action.destination)
            ok = True
            message = f"Copied directory {action.source} to {action.destination}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyDirectoryObservation(
            kind="copy_dir",
            source=action.source,
            destination=action.destination,
            ok=ok,
            message=message,
        )

    if isinstance(action, CopyDirectoriesAction):
        try:
            copy_project_directories(workspace, directory_transfer_pairs(action.transfers))
            ok = True
            message = f"Copied {len(action.transfers)} directory transfer(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CopyDirectoriesObservation(
            kind="copy_dirs",
            transfers=action.transfers,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCreateDirectoryAction):
        try:
            preview_create_project_directory(workspace, action.path)
            ok = True
            message = f"Directory creation can apply to {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCreateDirectoryObservation(
            kind="check_create_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckCreateDirectoriesAction):
        try:
            preview_create_project_directories(workspace, action.paths)
            ok = True
            message = f"Directory creation can apply to {len(action.paths)} path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckCreateDirectoriesObservation(
            kind="check_create_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, CreateDirectoryAction):
        try:
            create_project_directory(workspace, action.path)
            ok = True
            message = f"Created directory {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CreateDirectoryObservation(
            kind="create_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CreateDirectoriesAction):
        try:
            create_project_directories(workspace, action.paths)
            ok = True
            message = f"Created {len(action.paths)} directory path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CreateDirectoriesObservation(
            kind="create_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckDeleteEmptyDirectoryAction):
        try:
            preview_delete_project_empty_directory(workspace, action.path)
            ok = True
            message = f"Empty directory deletion can apply to {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckDeleteEmptyDirectoryObservation(
            kind="check_delete_empty_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckDeleteEmptyDirectoriesAction):
        try:
            preview_delete_project_empty_directories(workspace, action.paths)
            ok = True
            message = f"Empty directory deletion can apply to {len(action.paths)} path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return CheckDeleteEmptyDirectoriesObservation(
            kind="check_delete_empty_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, DeleteEmptyDirectoryAction):
        try:
            delete_project_empty_directory(workspace, action.path)
            ok = True
            message = f"Deleted empty directory {action.path}."
        except ValueError as error:
            ok = False
            message = str(error)
        return DeleteEmptyDirectoryObservation(
            kind="delete_empty_dir",
            path=action.path,
            ok=ok,
            message=message,
        )

    if isinstance(action, DeleteEmptyDirectoriesAction):
        try:
            delete_project_empty_directories(workspace, action.paths)
            ok = True
            message = f"Deleted {len(action.paths)} empty directory path(s)."
        except ValueError as error:
            ok = False
            message = str(error)
        return DeleteEmptyDirectoriesObservation(
            kind="delete_empty_dirs",
            paths=action.paths,
            ok=ok,
            message=message,
        )

    if isinstance(action, CheckSetExecutableAction):
        try:
            _path, before, after = preview_set_project_file_executable(workspace, action.path, executable=action.executable)
            ok = True
            state = "executable" if action.executable else "not executable"
            message = f"Executable bit change can apply to set {action.path} {state}."
        except ValueError as error:
            before = 0
            after = 0
            ok = False
            message = str(error)
        return CheckSetExecutableObservation(
            kind="check_set_executable",
            path=action.path,
            executable=action.executable,
            ok=ok,
            mode_before=format_file_mode(before),
            mode_after=format_file_mode(after),
            message=message,
        )

    if isinstance(action, SetExecutableAction):
        try:
            _path, before, after = set_project_file_executable(workspace, action.path, executable=action.executable)
            ok = True
            state = "executable" if action.executable else "not executable"
            message = f"Set {action.path} {state}."
        except ValueError as error:
            before = 0
            after = 0
            ok = False
            message = str(error)
        return SetExecutableObservation(
            kind="set_executable",
            path=action.path,
            executable=action.executable,
            ok=ok,
            mode_before=format_file_mode(before),
            mode_after=format_file_mode(after),
            message=message,
        )

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


def create_checkpoint_observation(workspace: RunWorkspace, label: str | None = None) -> CheckpointCreateObservation:
    status = read_git_status(workspace)
    if not status.ok:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=status.stderr or "git status failed.",
        )
    staged = read_git_diff(workspace, staged=True)
    unstaged = read_git_diff(workspace, staged=False)
    if not staged.ok or not unstaged.ok:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=staged.stderr or unstaged.stderr or "git diff failed.",
        )
    head = read_checkpoint_git_head(workspace.root)
    if not head:
        return CheckpointCreateObservation(
            kind="checkpoint_create",
            ok=False,
            checkpoint=None,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message="git rev-parse HEAD failed.",
        )

    filtered_status = filter_checkpoint_status(status.stdout)
    counts = count_checkpoint_status_kinds(filtered_status)
    checkpoint_id = make_checkpoint_id()
    created_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    info = CheckpointInfo(
        checkpoint_id=checkpoint_id,
        label=normalize_checkpoint_label(label),
        created_at=created_at,
        head=head,
        changed_files=counts["changed_files"],
        staged_files=counts["staged_files"],
        unstaged_files=counts["unstaged_files"],
        untracked_files=counts["untracked_files"],
    )
    checkpoint_dir = checkpoint_root(workspace.root) / checkpoint_id
    checkpoint_dir.mkdir(parents=True, exist_ok=False)
    metadata = checkpoint_info_to_metadata(info, str(workspace.root), filtered_status, len(staged.stdout), len(unstaged.stdout))
    saved_untracked, skipped_untracked = save_checkpoint_untracked_files(workspace.root, checkpoint_dir, filtered_status)
    metadata["untracked_saved_files"] = saved_untracked
    metadata["untracked_skipped_files"] = skipped_untracked
    (checkpoint_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (checkpoint_dir / "staged.patch").write_text(staged.stdout, encoding="utf-8")
    (checkpoint_dir / "unstaged.patch").write_text(unstaged.stdout, encoding="utf-8")
    return CheckpointCreateObservation(
        kind="checkpoint_create",
        ok=True,
        checkpoint=info,
        staged_patch_chars=len(staged.stdout),
        unstaged_patch_chars=len(unstaged.stdout),
        message=f"Saved checkpoint {checkpoint_id}.",
    )


def list_checkpoints_observation(root: Path, max_entries: int = 20) -> CheckpointListObservation:
    checkpoints = read_checkpoint_infos(root)
    shown = checkpoints[:max_entries]
    return CheckpointListObservation(
        kind="checkpoint_list",
        ok=True,
        checkpoints=shown,
        total=len(checkpoints),
        message=f"Found {len(checkpoints)} checkpoint(s).",
    )


def checkpoint_show_observation(root: Path, checkpoint_id: str) -> CheckpointShowObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckpointShowObservation(
            kind="checkpoint_show",
            ok=False,
            checkpoint=None,
            project_root="",
            git_status="",
            untracked_saved_files=0,
            untracked_skipped_files=0,
            saved_untracked_paths=[],
            saved_untracked_paths_truncated=False,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=message,
        )
    info = checkpoint_info_from_metadata(metadata)
    if info is None:
        return CheckpointShowObservation(
            kind="checkpoint_show",
            ok=False,
            checkpoint=None,
            project_root=str(metadata.get("project_root") or ""),
            git_status="",
            untracked_saved_files=0,
            untracked_skipped_files=0,
            saved_untracked_paths=[],
            saved_untracked_paths_truncated=False,
            staged_patch_chars=0,
            unstaged_patch_chars=0,
            message=f"Checkpoint metadata is invalid: {checkpoint_id}",
        )
    saved_untracked_paths, saved_untracked_paths_truncated = clip_checkpoint_untracked_paths(
        [item["path"] for item in read_checkpoint_untracked_manifest(root, info.checkpoint_id)],
    )
    return CheckpointShowObservation(
        kind="checkpoint_show",
        ok=True,
        checkpoint=info,
        project_root=str(metadata.get("project_root") or ""),
        git_status=str(metadata.get("git_status") or ""),
        untracked_saved_files=int(metadata.get("untracked_saved_files") or 0),
        untracked_skipped_files=int(metadata.get("untracked_skipped_files") or 0),
        saved_untracked_paths=saved_untracked_paths,
        saved_untracked_paths_truncated=saved_untracked_paths_truncated,
        staged_patch_chars=int(metadata.get("staged_diff_chars") or 0),
        unstaged_patch_chars=int(metadata.get("unstaged_diff_chars") or 0),
        message=f"Read checkpoint {info.checkpoint_id}.",
    )


def checkpoint_diff_observation(root: Path, checkpoint_id: str, max_chars: int = 40_000) -> CheckpointDiffObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckpointDiffObservation(
            kind="checkpoint_diff",
            ok=False,
            checkpoint_id=checkpoint_id,
            label="",
            created_at="",
            staged_patch="",
            staged_patch_chars=0,
            staged_patch_truncated=False,
            unstaged_patch="",
            unstaged_patch_chars=0,
            unstaged_patch_truncated=False,
            max_chars=max_chars,
            message=message,
        )
    checkpoint_id = str(metadata.get("id") or checkpoint_id)
    staged_patch = read_checkpoint_patch(root, checkpoint_id, "staged.patch")
    unstaged_patch = read_checkpoint_patch(root, checkpoint_id, "unstaged.patch")
    staged_text, staged_truncated = clip_text_with_flag(staged_patch, max_chars)
    unstaged_text, unstaged_truncated = clip_text_with_flag(unstaged_patch, max_chars)
    return CheckpointDiffObservation(
        kind="checkpoint_diff",
        ok=True,
        checkpoint_id=checkpoint_id,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        staged_patch=staged_text,
        staged_patch_chars=len(staged_patch),
        staged_patch_truncated=staged_truncated,
        unstaged_patch=unstaged_text,
        unstaged_patch_chars=len(unstaged_patch),
        unstaged_patch_truncated=unstaged_truncated,
        max_chars=max_chars,
        message=f"Read checkpoint diff {checkpoint_id}.",
    )


def checkpoint_status_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckpointStatusObservation:
    metadata, message = read_checkpoint_metadata(workspace.root, checkpoint_id)
    if metadata is None:
        return empty_checkpoint_status(checkpoint_id, message)
    status = read_git_status(workspace)
    staged = read_git_diff(workspace, staged=True)
    unstaged = read_git_diff(workspace, staged=False)
    if not status.ok or not staged.ok or not unstaged.ok:
        return empty_checkpoint_status(
            str(metadata.get("id") or checkpoint_id),
            status.stderr or staged.stderr or unstaged.stderr or "git status/diff failed.",
        )
    saved_status = str(metadata.get("git_status") or "")
    saved_staged = read_checkpoint_patch(workspace.root, checkpoint_id, "staged.patch")
    saved_unstaged = read_checkpoint_patch(workspace.root, checkpoint_id, "unstaged.patch")
    untracked_matches = checkpoint_untracked_files_match(workspace.root, checkpoint_id, int(metadata.get("untracked_files") or 0))
    current_status = filter_checkpoint_status(status.stdout)
    current_counts = count_checkpoint_status_kinds(current_status)
    status_matches = current_status == saved_status
    staged_matches = staged.stdout == saved_staged
    unstaged_matches = unstaged.stdout == saved_unstaged
    matches = status_matches and staged_matches and unstaged_matches and untracked_matches
    return CheckpointStatusObservation(
        kind="checkpoint_status",
        ok=True,
        checkpoint_id=str(metadata.get("id") or checkpoint_id),
        matches=matches,
        status_matches=status_matches,
        staged_patch_matches=staged_matches,
        unstaged_patch_matches=unstaged_matches,
        untracked_file_matches=untracked_matches,
        saved_changed_files=int(metadata.get("changed_files") or 0),
        saved_staged_files=int(metadata.get("staged_files") or 0),
        saved_unstaged_files=int(metadata.get("unstaged_files") or 0),
        saved_untracked_files=int(metadata.get("untracked_files") or 0),
        current_changed_files=current_counts["changed_files"],
        current_staged_files=current_counts["staged_files"],
        current_unstaged_files=current_counts["unstaged_files"],
        current_untracked_files=current_counts["untracked_files"],
        message="Current worktree matches checkpoint." if matches else "Current worktree differs from checkpoint.",
    )


def check_checkpoint_restore_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckCheckpointRestoreObservation:
    metadata, message = read_checkpoint_metadata(workspace.root, checkpoint_id)
    if metadata is None:
        return empty_check_checkpoint_restore(checkpoint_id, message)
    status = read_git_status(workspace)
    if not status.ok:
        return empty_check_checkpoint_restore(str(metadata.get("id") or checkpoint_id), status.stderr or "git status failed.")
    current_head = read_checkpoint_git_head(workspace.root)
    saved_head = metadata.get("head")
    current_counts = count_checkpoint_status_kinds(filter_checkpoint_status(status.stdout))
    saved_untracked = int(metadata.get("untracked_files") or 0)
    saved_untracked_paths = read_checkpoint_untracked_paths(workspace.root, checkpoint_id)
    current_untracked_paths = set(checkpoint_untracked_paths(filter_checkpoint_status(status.stdout)))
    staged_patch = read_checkpoint_patch(workspace.root, checkpoint_id, "staged.patch")
    unstaged_patch = read_checkpoint_patch(workspace.root, checkpoint_id, "unstaged.patch")
    can_restore = True
    restore_message = "Checkpoint can restore tracked staged/unstaged changes and saved untracked files."
    if not isinstance(saved_head, str) or not saved_head:
        can_restore = False
        restore_message = "Checkpoint does not record HEAD; create a new checkpoint before using restore."
    elif current_head != saved_head:
        can_restore = False
        restore_message = f"Checkpoint was created at HEAD {short_checkpoint_head(saved_head)}, but current HEAD is {short_checkpoint_head(current_head)}."
    elif saved_untracked and len(saved_untracked_paths) != saved_untracked:
        can_restore = False
        restore_message = "Checkpoint contains untracked files that were not fully saved."
    elif current_untracked_paths - saved_untracked_paths:
        can_restore = False
        restore_message = "Current worktree contains extra untracked files; move, delete, or commit them before checkpoint restore."
    return CheckCheckpointRestoreObservation(
        kind="check_checkpoint_restore",
        ok=can_restore,
        checkpoint_id=str(metadata.get("id") or checkpoint_id),
        can_restore=can_restore,
        saved_head=saved_head if isinstance(saved_head, str) else "",
        current_head=current_head,
        saved_untracked_files=saved_untracked,
        current_untracked_files=current_counts["untracked_files"],
        staged_patch_chars=len(staged_patch),
        unstaged_patch_chars=len(unstaged_patch),
        message=restore_message,
    )


def checkpoint_restore_observation(workspace: RunWorkspace, checkpoint_id: str) -> CheckpointRestoreObservation:
    restore_check = check_checkpoint_restore_observation(workspace, checkpoint_id)
    if not restore_check.ok:
        return CheckpointRestoreObservation(
            kind="checkpoint_restore",
            ok=False,
            checkpoint_id=restore_check.checkpoint_id,
            restored=False,
            matches=False,
            saved_head=restore_check.saved_head,
            current_head=restore_check.current_head,
            saved_untracked_files=restore_check.saved_untracked_files,
            current_untracked_files=restore_check.current_untracked_files,
            staged_patch_chars=restore_check.staged_patch_chars,
            unstaged_patch_chars=restore_check.unstaged_patch_chars,
            message=restore_check.message,
        )

    restored_id = restore_check.checkpoint_id
    staged_patch = read_checkpoint_patch(workspace.root, restored_id, "staged.patch")
    unstaged_patch = read_checkpoint_patch(workspace.root, restored_id, "unstaged.patch")
    steps: list[tuple[list[str], str | None]] = [(["restore", "--staged", "--worktree", "--", "."], None)]
    if staged_patch.strip():
        steps.extend(
            [
                (["apply", "--check", "--whitespace=nowarn", "-"], staged_patch),
                (["apply", "--cached", "--check", "--whitespace=nowarn", "-"], staged_patch),
                (["apply", "--whitespace=nowarn", "-"], staged_patch),
                (["apply", "--cached", "--whitespace=nowarn", "-"], staged_patch),
            ]
        )
    if unstaged_patch.strip():
        steps.extend(
            [
                (["apply", "--check", "--whitespace=nowarn", "-"], unstaged_patch),
                (["apply", "--whitespace=nowarn", "-"], unstaged_patch),
            ]
        )

    for args, stdin in steps:
        result = run_checkpoint_git_command(workspace.root, args, stdin)
        if result.returncode != 0:
            return CheckpointRestoreObservation(
                kind="checkpoint_restore",
                ok=False,
                checkpoint_id=restore_check.checkpoint_id,
                restored=False,
                matches=False,
                saved_head=restore_check.saved_head,
                current_head=restore_check.current_head,
                saved_untracked_files=restore_check.saved_untracked_files,
                current_untracked_files=restore_check.current_untracked_files,
                staged_patch_chars=restore_check.staged_patch_chars,
                unstaged_patch_chars=restore_check.unstaged_patch_chars,
                message=(
                    f"Failed to restore checkpoint while running git {' '.join(args)}: "
                    f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
                ),
            )

    restore_untracked_error = restore_checkpoint_untracked_files(workspace.root, restored_id)
    if restore_untracked_error:
        return CheckpointRestoreObservation(
            kind="checkpoint_restore",
            ok=False,
            checkpoint_id=restore_check.checkpoint_id,
            restored=False,
            matches=False,
            saved_head=restore_check.saved_head,
            current_head=restore_check.current_head,
            saved_untracked_files=restore_check.saved_untracked_files,
            current_untracked_files=restore_check.current_untracked_files,
            staged_patch_chars=restore_check.staged_patch_chars,
            unstaged_patch_chars=restore_check.unstaged_patch_chars,
            message=restore_untracked_error,
        )

    status = checkpoint_status_observation(workspace, restored_id)
    current_head = read_checkpoint_git_head(workspace.root)
    return CheckpointRestoreObservation(
        kind="checkpoint_restore",
        ok=status.ok and status.matches,
        checkpoint_id=restore_check.checkpoint_id,
        restored=status.ok and status.matches,
        matches=status.matches if status.ok else False,
        saved_head=restore_check.saved_head,
        current_head=current_head,
        saved_untracked_files=restore_check.saved_untracked_files,
        current_untracked_files=status.current_untracked_files if status.ok else restore_check.current_untracked_files,
        staged_patch_chars=restore_check.staged_patch_chars,
        unstaged_patch_chars=restore_check.unstaged_patch_chars,
        message=(
            "Restored tracked staged/unstaged changes and saved untracked files from checkpoint."
            if status.ok and status.matches
            else status.message
        ),
    )


def check_checkpoint_delete_observation(root: Path, checkpoint_id: str) -> CheckCheckpointDeleteObservation:
    metadata, message = read_checkpoint_metadata(root, checkpoint_id)
    if metadata is None:
        return CheckCheckpointDeleteObservation(
            kind="check_checkpoint_delete",
            ok=False,
            checkpoint_id=checkpoint_id,
            can_delete=False,
            label="",
            created_at="",
            message=message,
        )
    resolved_id = checkpoint_id.strip()
    display_id = str(metadata.get("id") or resolved_id)
    return CheckCheckpointDeleteObservation(
        kind="check_checkpoint_delete",
        ok=True,
        checkpoint_id=display_id,
        can_delete=True,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        message=f"Checkpoint delete would remove saved checkpoint {display_id}.",
    )


def checkpoint_delete_observation(root: Path, checkpoint_id: str) -> CheckpointDeleteObservation:
    preview = check_checkpoint_delete_observation(root, checkpoint_id)
    if not preview.ok:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=preview.checkpoint_id,
            deleted=False,
            message=preview.message,
        )
    resolved_id = checkpoint_id.strip()
    display_id = preview.checkpoint_id
    checkpoint_dir = checkpoint_root(root) / resolved_id
    try:
        shutil.rmtree(checkpoint_dir)
    except OSError as error:
        return CheckpointDeleteObservation(
            kind="checkpoint_delete",
            ok=False,
            checkpoint_id=display_id,
            deleted=False,
            message=f"Failed to delete checkpoint {display_id}: {error}",
        )
    return CheckpointDeleteObservation(
        kind="checkpoint_delete",
        ok=True,
        checkpoint_id=display_id,
        deleted=True,
        message=f"Deleted checkpoint {display_id}.",
    )


def check_checkpoint_prune_observation(root: Path, keep_last: int) -> CheckCheckpointPruneObservation:
    checkpoints = read_checkpoint_infos(root)
    to_delete = checkpoints[keep_last:] if keep_last < len(checkpoints) else []
    kept = len(checkpoints) - len(to_delete)
    return CheckCheckpointPruneObservation(
        kind="check_checkpoint_prune",
        ok=True,
        keep_last=keep_last,
        total=len(checkpoints),
        kept=kept,
        delete_count=len(to_delete),
        checkpoints=to_delete,
        message=(
            f"Checkpoint prune would delete {len(to_delete)} saved checkpoint(s)."
            if to_delete
            else "No checkpoints need pruning."
        ),
    )


def checkpoint_prune_observation(root: Path, keep_last: int) -> CheckpointPruneObservation:
    preview = check_checkpoint_prune_observation(root, keep_last)
    deleted = 0
    for checkpoint in preview.checkpoints:
        checkpoint_dir = checkpoint_root(root) / checkpoint.checkpoint_id
        try:
            shutil.rmtree(checkpoint_dir)
        except OSError as error:
            return CheckpointPruneObservation(
                kind="checkpoint_prune",
                ok=False,
                keep_last=keep_last,
                total=preview.total,
                kept=preview.kept,
                deleted=deleted,
                checkpoints=preview.checkpoints,
                message=f"Failed to prune checkpoint {checkpoint.checkpoint_id}: {error}",
            )
        deleted += 1
    return CheckpointPruneObservation(
        kind="checkpoint_prune",
        ok=True,
        keep_last=keep_last,
        total=preview.total,
        kept=preview.kept,
        deleted=deleted,
        checkpoints=preview.checkpoints,
        message=(
            f"Pruned {deleted} saved checkpoint(s)."
            if deleted
            else "No checkpoints needed pruning."
        ),
    )


def run_checkpoint_git_command(root: Path, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def checkpoint_root(root: Path) -> Path:
    return root / ".vibeagent" / "checkpoints"


def make_checkpoint_id() -> str:
    stamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return f"{stamp.replace(':', '-').replace('.', '-')}-{uuid.uuid4().hex[:8]}"


def normalize_checkpoint_label(label: str | None) -> str:
    return " ".join((label or "").strip().split())[:120]


def checkpoint_info_to_metadata(
    info: CheckpointInfo,
    project_root: str,
    git_status: str,
    staged_patch_chars: int,
    unstaged_patch_chars: int,
) -> dict[str, object]:
    return {
        "id": info.checkpoint_id,
        "label": info.label,
        "created_at": info.created_at,
        "project_root": project_root,
        "head": info.head,
        "git_status": git_status,
        "changed_files": info.changed_files,
        "staged_files": info.staged_files,
        "unstaged_files": info.unstaged_files,
        "untracked_files": info.untracked_files,
        "staged_diff_chars": staged_patch_chars,
        "unstaged_diff_chars": unstaged_patch_chars,
    }


def read_checkpoint_infos(root: Path) -> list[CheckpointInfo]:
    base = checkpoint_root(root)
    if not base.is_dir():
        return []
    infos: list[CheckpointInfo] = []
    for path in base.iterdir():
        metadata_path = path / "metadata.json"
        if not path.is_dir() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        info = checkpoint_info_from_metadata(metadata)
        if info is not None:
            infos.append(info)
    infos.sort(key=lambda item: (item.created_at, item.checkpoint_id), reverse=True)
    return infos


def checkpoint_info_from_metadata(metadata: object) -> CheckpointInfo | None:
    if not isinstance(metadata, dict):
        return None
    checkpoint_id = metadata.get("id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        return None
    return CheckpointInfo(
        checkpoint_id=checkpoint_id,
        label=str(metadata.get("label") or ""),
        created_at=str(metadata.get("created_at") or ""),
        head=str(metadata.get("head") or ""),
        changed_files=int(metadata.get("changed_files") or 0),
        staged_files=int(metadata.get("staged_files") or 0),
        unstaged_files=int(metadata.get("unstaged_files") or 0),
        untracked_files=int(metadata.get("untracked_files") or 0),
    )


def read_checkpoint_metadata(root: Path, checkpoint_id: str) -> tuple[dict[str, object] | None, str]:
    normalized = checkpoint_id.strip()
    if not normalized or Path(normalized).name != normalized:
        return None, f"Invalid checkpoint id: {checkpoint_id}"
    metadata_path = checkpoint_root(root) / normalized / "metadata.json"
    if not metadata_path.is_file():
        return None, f"Checkpoint not found: {checkpoint_id}"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, f"Checkpoint metadata is unreadable: {checkpoint_id}"
    if not isinstance(metadata, dict):
        return None, f"Checkpoint metadata is invalid: {checkpoint_id}"
    return metadata, "ok"


def read_checkpoint_patch(root: Path, checkpoint_id: str, name: str) -> str:
    try:
        return (checkpoint_root(root) / checkpoint_id / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def save_checkpoint_untracked_files(root: Path, checkpoint_dir: Path, status: str) -> tuple[int, int]:
    paths = checkpoint_untracked_paths(status)
    saved = 0
    skipped = 0
    manifest: list[dict[str, object]] = []
    storage_root = checkpoint_dir / "untracked_files"
    for path_text in paths:
        path = root / path_text
        if not path.is_file() or path.is_symlink():
            skipped += 1
            continue
        if not is_safe_checkpoint_relative_path(path_text):
            skipped += 1
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            skipped += 1
            continue
        destination = storage_root / relative
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            manifest.append({"path": relative.as_posix(), "size_bytes": path.stat().st_size})
            saved += 1
        except OSError:
            skipped += 1
    if manifest:
        (checkpoint_dir / "untracked_manifest.json").write_text(
            json.dumps({"files": manifest}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return saved, skipped


def checkpoint_untracked_paths(status: str) -> list[str]:
    paths: list[str] = []
    for raw_line in status.splitlines():
        if not raw_line.startswith("?? "):
            continue
        path_text = raw_line[3:].strip()
        if path_text and not is_runtime_checkpoint_path(path_text):
            paths.append(path_text)
    return paths


def read_checkpoint_untracked_paths(root: Path, checkpoint_id: str) -> set[str]:
    return {item["path"] for item in read_checkpoint_untracked_manifest(root, checkpoint_id)}


def clip_checkpoint_untracked_paths(paths: list[str]) -> tuple[list[str], bool]:
    return paths[:CHECKPOINT_UNTRACKED_SHOW_LIMIT], len(paths) > CHECKPOINT_UNTRACKED_SHOW_LIMIT


def read_checkpoint_untracked_manifest(root: Path, checkpoint_id: str) -> list[dict[str, str]]:
    manifest_path = checkpoint_root(root) / checkpoint_id / "untracked_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        return []
    items: list[dict[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str) and is_safe_checkpoint_relative_path(path):
            items.append({"path": path})
    return items


def is_safe_checkpoint_relative_path(path: str) -> bool:
    candidate = Path(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts


def checkpoint_untracked_files_match(root: Path, checkpoint_id: str, saved_untracked: int) -> bool:
    manifest = read_checkpoint_untracked_manifest(root, checkpoint_id)
    if saved_untracked == 0:
        return True
    if len(manifest) != saved_untracked:
        return False
    storage_root = checkpoint_root(root) / checkpoint_id / "untracked_files"
    for item in manifest:
        relative = item["path"]
        if not is_safe_checkpoint_relative_path(relative):
            return False
        source = storage_root / relative
        target = root / relative
        try:
            if not target.is_file() or source.read_bytes() != target.read_bytes():
                return False
        except OSError:
            return False
    return True


def restore_checkpoint_untracked_files(root: Path, checkpoint_id: str) -> str | None:
    manifest = read_checkpoint_untracked_manifest(root, checkpoint_id)
    storage_root = checkpoint_root(root) / checkpoint_id / "untracked_files"
    for item in manifest:
        relative = item["path"]
        if not is_safe_checkpoint_relative_path(relative):
            return f"Refusing to restore unsafe untracked file path: {relative}"
        source = storage_root / relative
        destination = root / relative
        try:
            destination.relative_to(root)
        except ValueError:
            return f"Refusing to restore untracked file outside project: {relative}"
        if not source.is_file():
            return f"Saved untracked file is missing from checkpoint: {relative}"
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        except OSError as error:
            return f"Failed to restore untracked file {relative}: {error}"
    return None


def clip_text_with_flag(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    return value[:max_chars], True


def read_checkpoint_git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def filter_checkpoint_status(status: str) -> str:
    lines: list[str] = []
    for raw_line in status.splitlines():
        path_text = raw_line[3:] if len(raw_line) > 3 else raw_line.strip()
        paths = path_text.split(" -> ") if " -> " in path_text else [path_text]
        if any(is_runtime_checkpoint_path(path.strip()) for path in paths):
            continue
        lines.append(raw_line)
    return "\n".join(lines)


def is_runtime_checkpoint_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return normalized == ".git" or normalized.startswith(".git/") or normalized == ".vibeagent" or normalized.startswith(".vibeagent/")


def count_checkpoint_status_kinds(status: str) -> dict[str, int]:
    changed = staged = unstaged = untracked = 0
    for line in status.splitlines():
        if len(line) < 2:
            continue
        code = line[:2]
        changed += 1
        if code == "??":
            untracked += 1
            continue
        if code[0] != " ":
            staged += 1
        if code[1] != " ":
            unstaged += 1
    return {
        "changed_files": changed,
        "staged_files": staged,
        "unstaged_files": unstaged,
        "untracked_files": untracked,
    }


def empty_checkpoint_status(checkpoint_id: str, message: str) -> CheckpointStatusObservation:
    return CheckpointStatusObservation(
        kind="checkpoint_status",
        ok=False,
        checkpoint_id=checkpoint_id,
        matches=False,
        status_matches=False,
        staged_patch_matches=False,
        unstaged_patch_matches=False,
        untracked_file_matches=False,
        saved_changed_files=0,
        saved_staged_files=0,
        saved_unstaged_files=0,
        saved_untracked_files=0,
        current_changed_files=0,
        current_staged_files=0,
        current_unstaged_files=0,
        current_untracked_files=0,
        message=message,
    )


def empty_check_checkpoint_restore(checkpoint_id: str, message: str) -> CheckCheckpointRestoreObservation:
    return CheckCheckpointRestoreObservation(
        kind="check_checkpoint_restore",
        ok=False,
        checkpoint_id=checkpoint_id,
        can_restore=False,
        saved_head="",
        current_head="",
        saved_untracked_files=0,
        current_untracked_files=0,
        staged_patch_chars=0,
        unstaged_patch_chars=0,
        message=message,
    )


def short_checkpoint_head(value: str) -> str:
    return value[:12] if value else "."


def run_command(
    cwd: str | Path,
    command: str,
    timeout_ms: int = 30_000,
    project_root: str | Path | None = None,
    max_output_chars: int = 12_000,
) -> CommandResult:
    # Run shell command in controlled cwd, capture stdout/stderr, and enforce execution timeout.
    timed_out = False
    process = subprocess.Popen(
        command,
        cwd=Path(cwd),
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        stdout, stderr = process.communicate()

    stdout_value, stdout_truncated = truncate_command_output(stdout or "", max_output_chars)
    stderr_value, stderr_truncated = truncate_command_output(stderr or "", max_output_chars)
    return CommandResult(
        command=command,
        exit_code=process.returncode,
        stdout=stdout_value,
        stderr=stderr_value,
        timed_out=timed_out,
        signal=_signal_name(process.returncode) if process.returncode and process.returncode < 0 else None,
        timeout_ms=timeout_ms,
        cwd=relative_cwd(Path(cwd), project_root),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        max_output_chars=max_output_chars,
    )


def execute_run_command_item(
    workspace: RunWorkspace,
    action: RunCommandAction | RunCommandItem,
    command_timeout_ms: int,
) -> CommandResult:
    timeout_ms = action.timeout_ms or command_timeout_ms
    max_output_chars = action.max_output_chars or 12_000
    blocked = get_blocked_command_reason(action.command)
    if blocked:
        return CommandResult(
            command=action.command,
            exit_code=None,
            stdout="",
            stderr=f"Command blocked: {blocked}",
            timed_out=False,
            signal=None,
            timeout_ms=timeout_ms,
            cwd=action.cwd or ".",
            max_output_chars=max_output_chars,
        )
    try:
        command_cwd = resolve_command_cwd(workspace, action.cwd)
    except ValueError as error:
        return CommandResult(
            command=action.command,
            exit_code=None,
            stdout="",
            stderr=str(error),
            timed_out=False,
            signal=None,
            timeout_ms=timeout_ms,
            cwd=action.cwd or ".",
            max_output_chars=max_output_chars,
        )
    result = run_command(
        command_cwd,
        action.command,
        timeout_ms,
        workspace.root,
        max_output_chars=max_output_chars,
    )
    return attach_output_analysis_to_command_result(workspace, action, result)


def attach_output_analysis_to_command_result(
    workspace: RunWorkspace,
    action: RunCommandAction | RunCommandItem,
    result: CommandResult,
) -> CommandResult:
    auto_extract_diagnostics = (
        not action.extract_output_contexts
        and not action.extract_output_diagnostics
        and command_result_failed(result)
    )
    if not action.extract_output_contexts and not action.extract_output_diagnostics and not auto_extract_diagnostics:
        return result
    text = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if not text.strip():
        return result
    if action.extract_output_diagnostics or auto_extract_diagnostics:
        try:
            diagnostics_result = read_output_diagnostics_result(
                workspace,
                text,
                context_lines=action.context_lines,
                max_diagnostics=action.max_diagnostics,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
        except ValueError:
            return result
        return replace(
            result,
            output_contexts=output_context_results_from_dicts(diagnostics_result["contexts"]),
            output_context_total_refs=int(diagnostics_result["total_refs"]),
            output_contexts_truncated=bool(diagnostics_result["contexts_truncated"]),
            output_diagnostics=output_diagnostics_from_dicts(diagnostics_result["diagnostics"]),
            output_diagnostic_total=int(diagnostics_result["total_diagnostics"]),
            output_diagnostics_truncated=bool(diagnostics_result["diagnostics_truncated"]),
        )
    if action.extract_output_contexts:
        try:
            contexts_result = read_output_contexts_result(
                workspace,
                text,
                context_lines=action.context_lines,
                max_contexts=action.max_contexts,
                max_bytes_per_context=action.max_bytes_per_context,
            )
        except ValueError:
            return result
        return replace(
            result,
            output_contexts=output_context_results_from_dicts(contexts_result["contexts"]),
            output_context_total_refs=int(contexts_result["total_refs"]),
            output_contexts_truncated=bool(contexts_result["truncated"]),
        )


def command_result_failed(result: CommandResult) -> bool:
    if result.timed_out:
        return True
    if result.exit_code is None:
        return True
    return result.exit_code != 0


def attach_output_analysis_to_process_observation(
    workspace: RunWorkspace,
    observation: ReadProcessObservation | WaitProcessObservation,
) -> ReadProcessObservation | WaitProcessObservation:
    if not process_observation_failed(observation):
        return observation
    text = "\n".join(part for part in [observation.stdout, observation.stderr] if part)
    if not text.strip():
        return observation
    try:
        diagnostics_result = read_output_diagnostics_result(
            workspace,
            text,
            context_lines=2,
            max_diagnostics=50,
            max_contexts=20,
            max_bytes_per_context=20_000,
        )
    except ValueError:
        return observation
    return replace(
        observation,
        output_contexts=output_context_results_from_dicts(diagnostics_result["contexts"]),
        output_context_total_refs=int(diagnostics_result["total_refs"]),
        output_contexts_truncated=bool(diagnostics_result["contexts_truncated"]),
        output_diagnostics=output_diagnostics_from_dicts(diagnostics_result["diagnostics"]),
        output_diagnostic_total=int(diagnostics_result["total_diagnostics"]),
        output_diagnostics_truncated=bool(diagnostics_result["diagnostics_truncated"]),
    )


def process_observation_failed(observation: ReadProcessObservation | WaitProcessObservation) -> bool:
    if not observation.ok:
        return False
    if observation.running:
        return False
    if observation.exit_code is None:
        return True
    return observation.exit_code != 0


def start_background_command(workspace: RunWorkspace, command: str, cwd: str | None = None) -> StartCommandObservation:
    blocked = get_blocked_command_reason(command)
    if blocked:
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=cwd or ".",
            ok=False,
            message=f"Command blocked: {blocked}",
            stdout_path="",
            stderr_path="",
        )

    try:
        command_cwd = resolve_command_cwd(workspace, cwd)
    except ValueError as error:
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=cwd or ".",
            ok=False,
            message=str(error),
            stdout_path="",
            stderr_path="",
        )

    process_id = uuid.uuid4().hex[:12]
    process_dir = workspace.session_dir / "processes"
    process_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = process_dir / f"{process_id}.stdout.log"
    stderr_path = process_dir / f"{process_id}.stderr.log"
    exit_code_path = process_dir / f"{process_id}.exitcode"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            wrap_background_command(command, exit_code_path),
            cwd=command_cwd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=os.name != "nt",
        )
    except OSError as error:
        stdout_handle.close()
        stderr_handle.close()
        return StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command=command,
            cwd=relative_cwd(command_cwd, workspace.root),
            ok=False,
            message=str(error),
            stdout_path=stdout_path.as_posix(),
            stderr_path=stderr_path.as_posix(),
        )

    BACKGROUND_PROCESSES[process_id] = BackgroundProcess(
        id=process_id,
        command=command,
        cwd=relative_cwd(command_cwd, workspace.root),
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        stdout_handle=stdout_handle,
        stderr_handle=stderr_handle,
    )
    write_persistent_process_record(
        workspace,
        PersistentProcessRecord(
            id=process_id,
            command=command,
            cwd=relative_cwd(command_cwd, workspace.root),
            pid=process.pid,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            exit_code_path=exit_code_path,
            start_ticks=read_process_start_ticks(process.pid),
        ),
    )
    return StartCommandObservation(
        kind="start_command",
        process_id=process_id,
        pid=process.pid,
        command=command,
        cwd=relative_cwd(command_cwd, workspace.root),
        ok=True,
        message=f"Started process {process_id}.",
        stdout_path=stdout_path.as_posix(),
        stderr_path=stderr_path.as_posix(),
    )


def wrap_background_command(command: str, exit_code_path: Path) -> str:
    if os.name == "nt":
        escaped_exit_code_path = str(exit_code_path).replace('"', '""')
        quoted_exit_code_path = f'"{escaped_exit_code_path}"'
        return (
            f"{command}\r\n"
            "set __vibeagent_exit_code=%ERRORLEVEL%\r\n"
            f"echo %__vibeagent_exit_code%> {quoted_exit_code_path}\r\n"
            "exit /b %__vibeagent_exit_code%"
        )
    quoted_exit_code_path = shlex.quote(exit_code_path.as_posix())
    return (
        f"{command}\n"
        "__vibeagent_exit_code=$?\n"
        f"printf '%s\\n' \"$__vibeagent_exit_code\" > {quoted_exit_code_path}\n"
        "exit \"$__vibeagent_exit_code\""
    )


def process_registry_dir(root: Path) -> Path:
    return root / ".vibeagent" / "processes"


def process_record_path(root: Path, process_id: str) -> Path | None:
    if not process_id or Path(process_id).name != process_id:
        return None
    return process_registry_dir(root) / f"{process_id}.json"


def write_persistent_process_record(workspace: RunWorkspace, record: PersistentProcessRecord) -> None:
    path = process_record_path(workspace.root, record.id)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": record.id,
        "command": record.command,
        "cwd": record.cwd,
        "pid": record.pid,
        "stdout_path": relative_process_log_path(workspace.root, record.stdout_path),
        "stderr_path": relative_process_log_path(workspace.root, record.stderr_path),
        "exit_code_path": relative_process_log_path(workspace.root, record.exit_code_path) if record.exit_code_path else None,
        "start_ticks": record.start_ticks,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_process_log_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def remove_persistent_process_record(root: Path, process_id: str) -> None:
    path = process_record_path(root, process_id)
    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def read_persistent_process_record(root: Path, process_id: str) -> PersistentProcessRecord | None:
    path = process_record_path(root, process_id)
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parse_persistent_process_record(root, payload)


def read_persistent_process_records(root: Path) -> list[PersistentProcessRecord]:
    directory = process_registry_dir(root)
    if not directory.is_dir():
        return []
    records: list[PersistentProcessRecord] = []
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        record = parse_persistent_process_record(root, payload)
        if record is not None:
            records.append(record)
    return records


def parse_persistent_process_record(root: Path, payload: object) -> PersistentProcessRecord | None:
    if not isinstance(payload, dict):
        return None
    process_id = payload.get("id")
    command = payload.get("command")
    cwd = payload.get("cwd")
    pid = payload.get("pid")
    stdout_text = payload.get("stdout_path")
    stderr_text = payload.get("stderr_path")
    exit_code_text = payload.get("exit_code_path")
    start_ticks = payload.get("start_ticks")
    if not isinstance(process_id, str) or not process_id.strip() or Path(process_id).name != process_id:
        return None
    if not isinstance(command, str) or not isinstance(cwd, str):
        return None
    if not isinstance(pid, int) or pid <= 0:
        return None
    if not isinstance(stdout_text, str) or not isinstance(stderr_text, str):
        return None
    stdout_path = resolve_process_log_path(root, stdout_text)
    stderr_path = resolve_process_log_path(root, stderr_text)
    if stdout_path is None or stderr_path is None:
        return None
    exit_code_path = resolve_process_log_path(root, exit_code_text) if isinstance(exit_code_text, str) else None
    return PersistentProcessRecord(
        id=process_id,
        command=command,
        cwd=cwd,
        pid=pid,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        start_ticks=start_ticks if isinstance(start_ticks, int) else None,
    )


def resolve_process_log_path(root: Path, value: str) -> Path | None:
    candidate = Path(value)
    path = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved_root = root.resolve()
        resolved_path = path.resolve()
    except OSError:
        return None
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        return None
    return resolved_path


def read_process_start_ticks(pid: int) -> int | None:
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        stat = stat_path.read_text(encoding="utf-8")
    except OSError:
        return None
    parts = stat.rsplit(") ", 1)
    if len(parts) != 2:
        return None
    fields = parts[1].split()
    if len(fields) < 20:
        return None
    try:
        return int(fields[19])
    except ValueError:
        return None


def persistent_process_running(record: PersistentProcessRecord) -> bool:
    try:
        os.kill(record.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    if record.start_ticks is None:
        return True
    return read_process_start_ticks(record.pid) == record.start_ticks


def read_persistent_process_exit_code(record: PersistentProcessRecord) -> int | None:
    if record.exit_code_path is None:
        return None
    try:
        text = record.exit_code_path.read_text(encoding="utf-8").strip().splitlines()[0]
    except (OSError, IndexError):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def process_signal_name(exit_code: int | None) -> str | None:
    if exit_code is None:
        return None
    if exit_code < 0:
        return _signal_name(exit_code)
    if exit_code > 128:
        try:
            return signal.Signals(exit_code - 128).name
        except ValueError:
            return None
    return None


def terminate_persistent_process(record: PersistentProcessRecord) -> None:
    if not persistent_process_running(record):
        return
    if os.name != "nt":
        try:
            os.killpg(record.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except OSError:
            try:
                os.kill(record.pid, signal.SIGTERM)
            except OSError:
                return
    else:
        try:
            os.kill(record.pid, signal.SIGTERM)
        except OSError:
            return
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        if not persistent_process_running(record):
            return
        time.sleep(0.05)
    if os.name != "nt":
        try:
            os.killpg(record.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except OSError:
            try:
                os.kill(record.pid, signal.SIGKILL)
            except OSError:
                return
    else:
        try:
            os.kill(record.pid, signal.SIGKILL)
        except OSError:
            return


def read_background_process(root: Path, process_id: str, max_output_chars: int = 4_000) -> ReadProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            exit_code = None if running else read_persistent_process_exit_code(record)
            stdout = read_text_tail(record.stdout_path, max_output_chars)
            stderr = read_text_tail(record.stderr_path, max_output_chars)
            state = "running" if running else "exited or unavailable"
            return ReadProcessObservation(
                kind="read_process",
                process_id=process_id,
                pid=record.pid,
                ok=True,
                running=running,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {process_id} is {state}.",
            )
        return ReadProcessObservation(
            kind="read_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=max_output_chars,
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    if not running:
        _close_background_handles(background)
    stdout = read_text_tail(background.stdout_path, max_output_chars)
    stderr = read_text_tail(background.stderr_path, max_output_chars)
    return ReadProcessObservation(
        kind="read_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=running,
        exit_code=exit_code,
        signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
        stdout=stdout,
        stderr=stderr,
        max_output_chars=max_output_chars,
        message=f"Process {process_id} is {'running' if running else 'exited'}.",
    )


def read_background_process_output_contexts(
    workspace: RunWorkspace,
    action: ProcessOutputContextsAction,
) -> ProcessOutputContextsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no file:line references.",
        )

    try:
        result = read_output_contexts_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputContextsObservation(
            kind="process_output_contexts",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            contexts=[],
            total_refs=0,
            truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    contexts = output_context_results_from_dicts(result["contexts"])
    total_refs = int(result["total_refs"])
    return ProcessOutputContextsObservation(
        kind="process_output_contexts",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        contexts=contexts,
        total_refs=total_refs,
        truncated=bool(result["truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=f"Extracted {len(contexts)}/{total_refs} output context(s) from process {action.process_id}.",
    )


def read_background_process_output_diagnostics(
    workspace: RunWorkspace,
    action: ProcessOutputDiagnosticsAction,
) -> ProcessOutputDiagnosticsObservation:
    process = read_background_process(
        workspace.root,
        action.process_id,
        max_output_chars=action.max_output_chars,
    )
    if not process.ok:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=False,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=0,
            stderr_chars=0,
            max_output_chars=action.max_output_chars,
            message=process.message,
        )

    text = "\n".join(part for part in [process.stdout, process.stderr] if part)
    if not text.strip():
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=True,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=f"Process {action.process_id} output contained no diagnostic lines.",
        )

    try:
        result = read_output_diagnostics_result(
            workspace,
            text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
    except ValueError as error:
        return ProcessOutputDiagnosticsObservation(
            kind="process_output_diagnostics",
            process_id=action.process_id,
            pid=process.pid,
            ok=False,
            running=process.running,
            exit_code=process.exit_code,
            signal=process.signal,
            diagnostics=[],
            contexts=[],
            total_diagnostics=0,
            total_refs=0,
            diagnostics_truncated=False,
            contexts_truncated=False,
            stdout_chars=len(process.stdout),
            stderr_chars=len(process.stderr),
            max_output_chars=action.max_output_chars,
            message=str(error),
        )

    diagnostics = output_diagnostics_from_dicts(result["diagnostics"])
    contexts = output_context_results_from_dicts(result["contexts"])
    total_diagnostics = int(result["total_diagnostics"])
    total_refs = int(result["total_refs"])
    return ProcessOutputDiagnosticsObservation(
        kind="process_output_diagnostics",
        process_id=action.process_id,
        pid=process.pid,
        ok=True,
        running=process.running,
        exit_code=process.exit_code,
        signal=process.signal,
        diagnostics=diagnostics,
        contexts=contexts,
        total_diagnostics=total_diagnostics,
        total_refs=total_refs,
        diagnostics_truncated=bool(result["diagnostics_truncated"]),
        contexts_truncated=bool(result["contexts_truncated"]),
        stdout_chars=len(process.stdout),
        stderr_chars=len(process.stderr),
        max_output_chars=action.max_output_chars,
        message=(
            f"Extracted {len(diagnostics)}/{total_diagnostics} diagnostic(s) "
            f"and {len(contexts)}/{total_refs} source context(s) from process {action.process_id}."
        ),
    )


def wait_background_process(
    root: Path,
    process_id: str,
    timeout_ms: int = 5_000,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
    max_output_chars: int = 4_000,
) -> WaitProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            return wait_persistent_process(
                record,
                timeout_ms=timeout_ms,
                stdout_contains=stdout_contains,
                stderr_contains=stderr_contains,
                regex=regex,
                max_output_chars=max_output_chars,
            )
        return WaitProcessObservation(
            kind="wait_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            timed_out=False,
            matched=False,
            matched_stream=None,
            matched_pattern=None,
            timeout_ms=timeout_ms,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=max_output_chars,
            message="Unknown background process id.",
        )

    wait_for_output = stdout_contains is not None or stderr_contains is not None
    if wait_for_output:
        return wait_background_process_output(
            background,
            timeout_ms=timeout_ms,
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=max_output_chars,
        )

    timed_out = False
    try:
        exit_code = background.process.wait(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = background.process.poll()

    running = exit_code is None
    if not running:
        _close_background_handles(background)
    stdout = read_text_tail(background.stdout_path, max_output_chars)
    stderr = read_text_tail(background.stderr_path, max_output_chars)
    state = "still running" if running else "exited"
    timeout_note = " after timeout" if timed_out else ""
    return WaitProcessObservation(
        kind="wait_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=running,
        timed_out=timed_out,
        matched=False,
        matched_stream=None,
        matched_pattern=None,
        timeout_ms=timeout_ms,
        exit_code=exit_code,
        signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
        stdout=stdout,
        stderr=stderr,
        max_output_chars=max_output_chars,
        message=f"Process {process_id} is {state}{timeout_note}.",
    )


def check_write_background_process(root: Path, process_id: str, content: str) -> CheckWriteProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            message = (
                f"Cannot write to process {process_id}; stdin is only available in the runtime that started it."
                if running
                else f"Cannot write to process {process_id}; process has exited."
            )
            return CheckWriteProcessObservation(
                kind="check_write_process",
                process_id=process_id,
                pid=record.pid,
                ok=False,
                running=running,
                command=record.command,
                cwd=record.cwd,
                content_chars=len(content),
                message=message,
            )
        return CheckWriteProcessObservation(
            kind="check_write_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            command=None,
            cwd=None,
            content_chars=len(content),
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    stdin = background.process.stdin
    writable = running and stdin is not None and not stdin.closed
    if not running:
        _close_background_handles(background)
    message = (
        f"Can write {len(content)} character(s) to process {process_id}."
        if writable
        else f"Cannot write to process {process_id}; stdin is closed or the process has exited."
    )
    return CheckWriteProcessObservation(
        kind="check_write_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=writable,
        running=running,
        command=background.command,
        cwd=background.cwd,
        content_chars=len(content),
        message=message,
    )


def write_background_process(root: Path, process_id: str, content: str) -> WriteProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            message = (
                f"Cannot write to process {process_id}; stdin is only available in the runtime that started it."
                if running
                else f"Cannot write to process {process_id}; process has exited."
            )
            return WriteProcessObservation(
                kind="write_process",
                process_id=process_id,
                pid=record.pid,
                ok=False,
                running=running,
                command=record.command,
                cwd=record.cwd,
                content_chars=len(content),
                message=message,
            )
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=None,
            ok=False,
            running=False,
            command=None,
            cwd=None,
            content_chars=len(content),
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    stdin = background.process.stdin
    if not running:
        _close_background_handles(background)
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=False,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Cannot write to process {process_id}; process has exited.",
        )
    if stdin is None or stdin.closed:
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=True,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Cannot write to process {process_id}; stdin is closed.",
        )

    try:
        stdin.write(content)
        stdin.flush()
    except (BrokenPipeError, OSError, ValueError) as error:
        return WriteProcessObservation(
            kind="write_process",
            process_id=process_id,
            pid=background.process.pid,
            ok=False,
            running=background.process.poll() is None,
            command=background.command,
            cwd=background.cwd,
            content_chars=len(content),
            message=f"Failed to write to process {process_id}: {error}.",
        )

    return WriteProcessObservation(
        kind="write_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        running=background.process.poll() is None,
        command=background.command,
        cwd=background.cwd,
        content_chars=len(content),
        message=f"Wrote {len(content)} character(s) to process {process_id}.",
    )


def wait_persistent_process(
    record: PersistentProcessRecord,
    *,
    timeout_ms: int,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
    max_output_chars: int,
) -> WaitProcessObservation:
    deadline = time.monotonic() + (timeout_ms / 1000)
    wait_for_output = stdout_contains is not None or stderr_contains is not None
    timed_out = False
    while True:
        running = persistent_process_running(record)
        exit_code = None if running else read_persistent_process_exit_code(record)
        stdout = read_text_tail(record.stdout_path, max_output_chars)
        stderr = read_text_tail(record.stderr_path, max_output_chars)
        if wait_for_output:
            try:
                matched, matched_stream, matched_pattern = match_process_output(
                    stdout,
                    stderr,
                    stdout_contains=stdout_contains,
                    stderr_contains=stderr_contains,
                    regex=regex,
                )
            except re.error as error:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=False,
                    running=running,
                    timed_out=False,
                    matched=False,
                    matched_stream=None,
                    matched_pattern=None,
                    timeout_ms=timeout_ms,
                    exit_code=exit_code,
                    signal=process_signal_name(exit_code),
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Invalid wait_process regex: {error}.",
                )
            if matched:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=True,
                    running=running,
                    timed_out=False,
                    matched=True,
                    matched_stream=matched_stream,
                    matched_pattern=matched_pattern,
                    timeout_ms=timeout_ms,
                    exit_code=exit_code,
                    signal=process_signal_name(exit_code),
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Process {record.id} matched {matched_stream} output pattern.",
                )
            if not running:
                return WaitProcessObservation(
                    kind="wait_process",
                    process_id=record.id,
                    pid=record.pid,
                    ok=True,
                    running=False,
                    timed_out=False,
                    matched=False,
                    matched_stream=None,
                    matched_pattern=None,
                    timeout_ms=timeout_ms,
                    exit_code=None,
                    signal=None,
                    stdout=stdout,
                    stderr=stderr,
                    max_output_chars=max_output_chars,
                    message=f"Process {record.id} exited before output pattern matched.",
                )
        elif not running:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=record.id,
                pid=record.pid,
                ok=True,
                running=False,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {record.id} exited.",
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
        if timed_out:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=record.id,
                pid=record.pid,
                ok=True,
                running=running,
                timed_out=True,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=(
                    f"Process {record.id} is still running after timeout; no output pattern matched."
                    if wait_for_output
                    else f"Process {record.id} is still running after timeout."
                ),
            )
        time.sleep(min(0.1, remaining))


def wait_background_process_output(
    background: BackgroundProcess,
    *,
    timeout_ms: int,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
    max_output_chars: int,
) -> WaitProcessObservation:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while True:
        exit_code = background.process.poll()
        running = exit_code is None
        if not running:
            _close_background_handles(background)
        stdout = read_text_tail(background.stdout_path, max_output_chars)
        stderr = read_text_tail(background.stderr_path, max_output_chars)
        try:
            matched, matched_stream, matched_pattern = match_process_output(
                stdout,
                stderr,
                stdout_contains=stdout_contains,
                stderr_contains=stderr_contains,
                regex=regex,
            )
        except re.error as error:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=False,
                running=running,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Invalid wait_process regex: {error}.",
            )

        if matched:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=running,
                timed_out=False,
                matched=True,
                matched_stream=matched_stream,
                matched_pattern=matched_pattern,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} matched {matched_stream} output pattern.",
            )

        if not running:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=False,
                timed_out=False,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} exited before output pattern matched.",
            )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return WaitProcessObservation(
                kind="wait_process",
                process_id=background.id,
                pid=background.process.pid,
                ok=True,
                running=True,
                timed_out=True,
                matched=False,
                matched_stream=None,
                matched_pattern=None,
                timeout_ms=timeout_ms,
                exit_code=None,
                signal=None,
                stdout=stdout,
                stderr=stderr,
                max_output_chars=max_output_chars,
                message=f"Process {background.id} is still running after timeout; no output pattern matched.",
            )
        time.sleep(min(0.1, remaining))


def match_process_output(
    stdout: str,
    stderr: str,
    *,
    stdout_contains: str | None,
    stderr_contains: str | None,
    regex: bool,
) -> tuple[bool, str | None, str | None]:
    patterns = (("stdout", stdout, stdout_contains), ("stderr", stderr, stderr_contains))
    for stream, text, pattern in patterns:
        if pattern is None:
            continue
        if regex:
            if re.search(pattern, text):
                return True, stream, pattern
        elif pattern in text:
            return True, stream, pattern
    return False, None, None


def list_background_processes(root: Path) -> ListProcessesObservation:
    processes_by_id: dict[str, ProcessInfo] = {}
    for process_id, background in sorted(BACKGROUND_PROCESSES.items()):
        exit_code = background.process.poll()
        running = exit_code is None
        if not running:
            _close_background_handles(background)
        processes_by_id[process_id] = (
            ProcessInfo(
                process_id=process_id,
                pid=background.process.pid,
                command=background.command,
                cwd=background.cwd,
                running=running,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
            )
        )
    for record in read_persistent_process_records(root):
        if record.id in processes_by_id:
            continue
        running = persistent_process_running(record)
        exit_code = None if running else read_persistent_process_exit_code(record)
        processes_by_id[record.id] = ProcessInfo(
            process_id=record.id,
            pid=record.pid,
            command=record.command,
            cwd=record.cwd,
            running=running,
            exit_code=exit_code,
            signal=process_signal_name(exit_code),
        )

    processes = [processes_by_id[process_id] for process_id in sorted(processes_by_id)]
    return ListProcessesObservation(
        kind="list_processes",
        processes=processes,
        message=f"Found {len(processes)} background process(es).",
    )


def check_stop_all_background_processes(root: Path) -> CheckStopAllProcessesObservation:
    listed = list_background_processes(root)
    running_count = sum(1 for process in listed.processes if process.running)
    return CheckStopAllProcessesObservation(
        kind="check_stop_all_processes",
        ok=True,
        processes=listed.processes,
        running_count=running_count,
        message=f"stop_all_processes would stop {len(listed.processes)} background process(es), {running_count} still running.",
    )


def check_stop_background_process(root: Path, process_id: str) -> CheckStopProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            running = persistent_process_running(record)
            exit_code = None if running else read_persistent_process_exit_code(record)
            state = "running and can be stopped" if running else "already exited or unavailable"
            return CheckStopProcessObservation(
                kind="check_stop_process",
                process_id=process_id,
                pid=record.pid,
                ok=True,
                command=record.command,
                cwd=record.cwd,
                running=running,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                message=f"Process {process_id} is {state}.",
            )
        return CheckStopProcessObservation(
            kind="check_stop_process",
            process_id=process_id,
            pid=None,
            ok=False,
            command=None,
            cwd=None,
            running=False,
            exit_code=None,
            signal=None,
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    signal = _signal_name(exit_code) if exit_code and exit_code < 0 else None
    state = "running and can be stopped" if running else "already exited"
    return CheckStopProcessObservation(
        kind="check_stop_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        command=background.command,
        cwd=background.cwd,
        running=running,
        exit_code=exit_code,
        signal=signal,
        message=f"Process {process_id} is {state}.",
    )


def stop_all_background_processes(root: Path) -> StopAllProcessesObservation:
    stopped: list[StoppedProcessInfo] = []
    stopped_ids: set[str] = set()
    for process_id, background in sorted(list(BACKGROUND_PROCESSES.items())):
        if background.process.poll() is None:
            _terminate_process(background.process)
        exit_code = background.process.poll()
        _close_background_handles(background)
        BACKGROUND_PROCESSES.pop(process_id, None)
        remove_persistent_process_record(root, process_id)
        stopped_ids.add(process_id)
        stopped.append(
            StoppedProcessInfo(
                process_id=process_id,
                pid=background.process.pid,
                command=background.command,
                cwd=background.cwd,
                ok=True,
                exit_code=exit_code,
                signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
                message=f"Stopped process {process_id}.",
            )
        )
    for record in read_persistent_process_records(root):
        if record.id in stopped_ids:
            continue
        was_running = persistent_process_running(record)
        if was_running:
            terminate_persistent_process(record)
        exit_code = read_persistent_process_exit_code(record)
        remove_persistent_process_record(root, record.id)
        stopped.append(
            StoppedProcessInfo(
                process_id=record.id,
                pid=record.pid,
                command=record.command,
                cwd=record.cwd,
                ok=True,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                message=f"Stopped process {record.id}." if was_running else f"Removed exited process {record.id}.",
            )
        )

    return StopAllProcessesObservation(
        kind="stop_all_processes",
        ok=True,
        stopped=stopped,
        message=f"Stopped {len(stopped)} background process(es).",
    )


def stop_background_process(root: Path, process_id: str) -> StopProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        record = read_persistent_process_record(root, process_id)
        if record is not None:
            was_running = persistent_process_running(record)
            if was_running:
                terminate_persistent_process(record)
            exit_code = read_persistent_process_exit_code(record)
            remove_persistent_process_record(root, process_id)
            return StopProcessObservation(
                kind="stop_process",
                process_id=process_id,
                pid=record.pid,
                ok=True,
                exit_code=exit_code,
                signal=process_signal_name(exit_code),
                message=f"Stopped process {process_id}." if was_running else f"Removed exited process {process_id}.",
            )
        return StopProcessObservation(
            kind="stop_process",
            process_id=process_id,
            pid=None,
            ok=False,
            exit_code=None,
            signal=None,
            message="Unknown background process id.",
        )

    if background.process.poll() is None:
        _terminate_process(background.process)
    exit_code = background.process.poll()
    _close_background_handles(background)
    BACKGROUND_PROCESSES.pop(process_id, None)
    remove_persistent_process_record(root, process_id)
    return StopProcessObservation(
        kind="stop_process",
        process_id=process_id,
        pid=background.process.pid,
        ok=True,
        exit_code=exit_code,
        signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
        message=f"Stopped process {process_id}.",
    )


def read_text_tail(path: Path, max_bytes: int = 4_000) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes), os.SEEK_SET)
        return handle.read().decode("utf-8", errors="replace")


def relative_cwd(cwd: Path, project_root: str | Path | None) -> str:
    if project_root is None:
        return "."
    try:
        relative = cwd.resolve().relative_to(Path(project_root).resolve())
    except ValueError:
        return cwd.as_posix()
    return relative.as_posix() or "."


def truncate_command_output(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    marker = f"\n[truncated to {max_chars} chars: showing head and tail]\n"
    if max_chars <= len(marker) + 2:
        return value[:max_chars], True
    keep = max_chars - len(marker)
    head = keep // 2
    tail = keep - head
    return f"{value[:head]}{marker}{value[-tail:]}", True


def build_python_rename_preview_files(preview: dict[str, object]) -> list[PythonRenamePreviewFile]:
    return [
        PythonRenamePreviewFile(
            path=str(file["path"]),
            replacements=[
                PythonRenameReplacement(**replacement)
                for replacement in list(file["replacements"])
            ],
            diff=str(file["diff"]),
            truncated=bool(file["truncated"]),
        )
        for file in list(preview["files"])
    ]


def build_code_rename_preview_files(preview: dict[str, object]) -> list[CodeRenamePreviewFile]:
    return [
        CodeRenamePreviewFile(
            path=str(file["path"]),
            language=str(file["language"]),
            replacements=[
                CodeRenameReplacement(**replacement)
                for replacement in list(file["replacements"])
            ],
            diff=str(file["diff"]),
            truncated=bool(file["truncated"]),
        )
        for file in list(preview["files"])
    ]


def parse_code_rename_input(
    value: dict[str, Any],
    raw: str,
    action_name: str,
    default_max_replacements: int,
) -> tuple[str, str, str | None, int, int]:
    symbol = value.get("symbol")
    new_name = value.get("new_name")
    path = value.get("path")
    max_files = value.get("max_files", 100)
    max_replacements = value.get("max_replacements", default_max_replacements)
    if not isinstance(symbol, str) or not symbol.strip():
        raise ActionParseError(f"{action_name} action requires a non-empty symbol.", raw)
    if not isinstance(new_name, str) or not new_name.strip():
        raise ActionParseError(f"{action_name} action requires a non-empty new_name.", raw)
    if "\n" in symbol or "\r" in symbol or "\n" in new_name or "\r" in new_name:
        raise ActionParseError(f"{action_name} action symbol and new_name must be single-line strings.", raw)
    if path is not None and not isinstance(path, str):
        raise ActionParseError(f"{action_name} action path must be a string when provided.", raw)
    max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
    max_replacements = parse_optional_positive_int(max_replacements, "max_replacements", raw, maximum=2000) or default_max_replacements
    return symbol.strip(), new_name.strip(), path, max_files, max_replacements


def parse_action(value: Any, raw: str) -> AgentAction:
    # Validate action shape against the small, finite action schema.
    if not isinstance(value, dict):
        raise ActionParseError("Model output must include an action object.", raw)

    action_type = value.get("type")
    if action_type == "list_files":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("list_files action path must be a string when provided.", raw)
        return ListFilesAction(type="list_files", path=path)

    if action_type == "list_tree":
        path = value.get("path")
        max_depth = value.get("max_depth", 3)
        max_entries = value.get("max_entries", 200)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("list_tree action path must be a string when provided.", raw)
        max_depth = parse_optional_positive_int(max_depth, "max_depth", raw, maximum=10) or 3
        max_entries = parse_optional_positive_int(max_entries, "max_entries", raw, maximum=1000) or 200
        return ListTreeAction(type="list_tree", path=path, max_depth=max_depth, max_entries=max_entries)

    if action_type == "repo_map":
        path = value.get("path")
        max_depth = value.get("max_depth", 3)
        max_files = value.get("max_files", 80)
        max_symbols = value.get("max_symbols", 120)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("repo_map action path must be a string when provided.", raw)
        max_depth = parse_optional_positive_int(max_depth, "max_depth", raw, maximum=10) or 3
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 80
        max_symbols = parse_optional_positive_int(max_symbols, "max_symbols", raw, maximum=500) or 120
        return RepoMapAction(
            type="repo_map",
            path=path,
            max_depth=max_depth,
            max_files=max_files,
            max_symbols=max_symbols,
        )

    if action_type == "read_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("read_file action requires a string path.", raw)
        start_line = parse_optional_positive_int(value.get("start_line"), "start_line", raw, maximum=None)
        line_count = parse_optional_positive_int(value.get("line_count"), "line_count", raw, maximum=1000)
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        if line_count is not None and start_line is None:
            raise ActionParseError("read_file action line_count requires start_line.", raw)
        return ReadFileAction(type="read_file", path=path, start_line=start_line, line_count=line_count, max_bytes=max_bytes)

    if action_type == "read_file_context":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("read_file_context action requires a string path.", raw)
        line = parse_optional_positive_int(value.get("line"), "line", raw, maximum=None)
        if line is None:
            raise ActionParseError("read_file_context action requires line.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 20), "context_lines", raw, maximum=500)
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        return ReadFileContextAction(
            type="read_file_context",
            path=path,
            line=line,
            context_lines=context_lines,
            max_bytes=max_bytes,
        )

    if action_type == "read_file_contexts":
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return ReadFileContextsAction(
            type="read_file_contexts",
            contexts=parse_read_file_contexts(value.get("contexts"), raw),
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "output_contexts":
        text = value.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ActionParseError("output_contexts action requires non-empty text.", raw)
        if len(text) > 200_000:
            raise ActionParseError("output_contexts text must be at most 200000 characters.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return OutputContextsAction(
            type="output_contexts",
            text=text,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type in {"output_diagnostics", "python_traceback"}:
        label = "python_traceback" if action_type == "python_traceback" else "output_diagnostics"
        text = value.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ActionParseError(f"{label} action requires non-empty text.", raw)
        if len(text) > 200_000:
            raise ActionParseError(f"{label} text must be at most 200000 characters.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 2), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return OutputDiagnosticsAction(
            type="output_diagnostics",
            text=text,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "tail_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("tail_file action requires a string path.", raw)
        line_count = parse_optional_positive_int(value.get("line_count", 80), "line_count", raw, maximum=1000) or 80
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=200_000) or 20_000
        if max_bytes < 1000:
            raise ActionParseError("max_bytes must be at least 1000.", raw)
        return TailFileAction(type="tail_file", path=path, line_count=line_count, max_bytes=max_bytes)

    if action_type == "read_files":
        max_bytes_per_file = parse_optional_positive_int(
            value.get("max_bytes_per_file", 20_000),
            "max_bytes_per_file",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_file < 1000:
            raise ActionParseError("max_bytes_per_file must be at least 1000.", raw)
        return ReadFilesAction(
            type="read_files",
            paths=parse_read_file_paths(value.get("paths"), raw),
            max_bytes_per_file=max_bytes_per_file,
        )

    if action_type == "read_file_ranges":
        max_bytes_per_range = parse_optional_positive_int(
            value.get("max_bytes_per_range", 20_000),
            "max_bytes_per_range",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_range < 1000:
            raise ActionParseError("max_bytes_per_range must be at least 1000.", raw)
        return ReadFileRangesAction(
            type="read_file_ranges",
            ranges=parse_read_file_ranges(value.get("ranges"), raw),
            max_bytes_per_range=max_bytes_per_range,
        )

    if action_type == "file_info":
        return FileInfoAction(type="file_info", paths=parse_path_list(value.get("paths"), raw, "file_info", maximum=50))

    if action_type == "image_info":
        return ImageInfoAction(type="image_info", paths=parse_path_list(value.get("paths"), raw, "image_info", maximum=20))

    if action_type == "python_symbols":
        return PythonSymbolsAction(
            type="python_symbols",
            paths=parse_path_list(value.get("paths"), raw, "python_symbols", maximum=20),
        )

    if action_type == "code_outline":
        max_symbols = parse_optional_positive_int(value.get("max_symbols", 200), "max_symbols", raw, maximum=1000) or 200
        return CodeOutlineAction(
            type="code_outline",
            paths=parse_path_list(value.get("paths"), raw, "code_outline", maximum=20),
            max_symbols=max_symbols,
        )

    if action_type == "python_check":
        path = value.get("path")
        max_files = value.get("max_files", 200)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_check action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 200
        return PythonCheckAction(type="python_check", path=path, max_files=max_files)

    if action_type == "config_check":
        path = value.get("path")
        max_files = value.get("max_files", 200)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("config_check action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 200
        return ConfigCheckAction(type="config_check", path=path, max_files=max_files)

    if action_type == "check_json_set":
        path, pointer, json_value, create_missing = parse_json_set_input(value, raw, "check_json_set")
        return CheckJsonSetAction(
            type="check_json_set",
            path=path,
            pointer=pointer,
            value=json_value,
            create_missing=create_missing,
        )

    if action_type == "json_set":
        path, pointer, json_value, create_missing = parse_json_set_input(value, raw, "json_set")
        return JsonSetAction(
            type="json_set",
            path=path,
            pointer=pointer,
            value=json_value,
            create_missing=create_missing,
        )

    if action_type == "check_json_remove":
        path, pointer = parse_json_pointer_action_input(value, raw, "check_json_remove")
        return CheckJsonRemoveAction(type="check_json_remove", path=path, pointer=pointer)

    if action_type == "json_remove":
        path, pointer = parse_json_pointer_action_input(value, raw, "json_remove")
        return JsonRemoveAction(type="json_remove", path=path, pointer=pointer)

    if action_type == "check_json_patch":
        path, operations = parse_json_patch_input(value, raw, "check_json_patch")
        return CheckJsonPatchAction(type="check_json_patch", path=path, operations=operations)

    if action_type == "json_patch":
        path, operations = parse_json_patch_input(value, raw, "json_patch")
        return JsonPatchAction(type="json_patch", path=path, operations=operations)

    if action_type == "python_dependencies":
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_imports = value.get("max_imports", 500)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_dependencies action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_imports = parse_optional_positive_int(max_imports, "max_imports", raw, maximum=2000) or 500
        return PythonDependenciesAction(
            type="python_dependencies",
            path=path,
            max_files=max_files,
            max_imports=max_imports,
        )

    if action_type == "code_dependencies":
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_imports = value.get("max_imports", 500)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_dependencies action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_imports = parse_optional_positive_int(max_imports, "max_imports", raw, maximum=2000) or 500
        return CodeDependenciesAction(
            type="code_dependencies",
            path=path,
            max_files=max_files,
            max_imports=max_imports,
        )

    if action_type == "code_references":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 200)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("code_references action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_references action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return CodeReferencesAction(
            type="code_references",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
        )

    if action_type == "code_reference_contexts":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        context_lines = value.get("context_lines", 3)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("code_reference_contexts action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_reference_contexts action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=100) or 50
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200_000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return CodeReferenceContextsAction(
            type="code_reference_contexts",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "code_definitions":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        max_lines = value.get("max_lines", 80)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("code_definitions action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("code_definitions action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=200) or 50
        max_lines = parse_optional_positive_int(max_lines, "max_lines", raw, maximum=500) or 80
        return CodeDefinitionsAction(
            type="code_definitions",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )

    if action_type == "code_rename_preview":
        symbol, new_name, path, max_files, max_replacements = parse_code_rename_input(
            value,
            raw,
            "code_rename_preview",
            default_max_replacements=500,
        )
        return CodeRenamePreviewAction(
            type="code_rename_preview",
            symbol=symbol,
            new_name=new_name,
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )

    if action_type == "code_rename":
        symbol, new_name, path, max_files, max_replacements = parse_code_rename_input(
            value,
            raw,
            "code_rename",
            default_max_replacements=2000,
        )
        return CodeRenameAction(
            type="code_rename",
            symbol=symbol,
            new_name=new_name,
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )

    if action_type == "python_definitions":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        max_lines = value.get("max_lines", 120)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_definitions action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_definitions action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=200) or 50
        max_lines = parse_optional_positive_int(max_lines, "max_lines", raw, maximum=1000) or 120
        return PythonDefinitionsAction(
            type="python_definitions",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            max_lines=max_lines,
        )

    if action_type == "python_calls":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 200)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_calls action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_calls action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return PythonCallsAction(
            type="python_calls",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
        )

    if action_type == "check_replace_python_definition":
        symbol = value.get("symbol")
        content = value.get("content")
        path = value.get("path")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("check_replace_python_definition action requires a non-empty symbol.", raw)
        if not isinstance(content, str) or not content.strip():
            raise ActionParseError("check_replace_python_definition action requires non-empty string content.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("check_replace_python_definition action path must be a string when provided.", raw)
        return CheckReplacePythonDefinitionAction(
            type="check_replace_python_definition",
            symbol=symbol.strip(),
            content=content,
            path=path,
        )

    if action_type == "replace_python_definition":
        symbol = value.get("symbol")
        content = value.get("content")
        path = value.get("path")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("replace_python_definition action requires a non-empty symbol.", raw)
        if not isinstance(content, str) or not content.strip():
            raise ActionParseError("replace_python_definition action requires non-empty string content.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("replace_python_definition action path must be a string when provided.", raw)
        return ReplacePythonDefinitionAction(
            type="replace_python_definition",
            symbol=symbol.strip(),
            content=content,
            path=path,
        )

    if action_type == "python_call_graph":
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_edges = value.get("max_edges", 500)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_call_graph action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_edges = parse_optional_positive_int(max_edges, "max_edges", raw, maximum=2000) or 500
        return PythonCallGraphAction(
            type="python_call_graph",
            path=path,
            max_files=max_files,
            max_edges=max_edges,
        )

    if action_type == "python_references":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 200)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_references action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_references action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return PythonReferencesAction(type="python_references", symbol=symbol.strip(), path=path, max_matches=max_matches)

    if action_type == "python_reference_contexts":
        symbol = value.get("symbol")
        path = value.get("path")
        max_matches = value.get("max_matches", 50)
        context_lines = value.get("context_lines", 3)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_reference_contexts action requires a non-empty symbol.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_reference_contexts action path must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=100) or 50
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200_000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return PythonReferenceContextsAction(
            type="python_reference_contexts",
            symbol=symbol.strip(),
            path=path,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "python_rename_preview":
        symbol = value.get("symbol")
        new_name = value.get("new_name")
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_replacements = value.get("max_replacements", 500)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_rename_preview action requires a non-empty symbol.", raw)
        if not isinstance(new_name, str) or not new_name.strip():
            raise ActionParseError("python_rename_preview action requires a non-empty new_name.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_rename_preview action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_replacements = parse_optional_positive_int(max_replacements, "max_replacements", raw, maximum=2000) or 500
        return PythonRenamePreviewAction(
            type="python_rename_preview",
            symbol=symbol.strip(),
            new_name=new_name.strip(),
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )

    if action_type == "python_rename":
        symbol = value.get("symbol")
        new_name = value.get("new_name")
        path = value.get("path")
        max_files = value.get("max_files", 100)
        max_replacements = value.get("max_replacements", 2000)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ActionParseError("python_rename action requires a non-empty symbol.", raw)
        if not isinstance(new_name, str) or not new_name.strip():
            raise ActionParseError("python_rename action requires a non-empty new_name.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_rename action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        max_replacements = parse_optional_positive_int(max_replacements, "max_replacements", raw, maximum=2000) or 2000
        return PythonRenameAction(
            type="python_rename",
            symbol=symbol.strip(),
            new_name=new_name.strip(),
            path=path,
            max_files=max_files,
            max_replacements=max_replacements,
        )

    if action_type == "search":
        query = value.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("search action requires a non-empty query.", raw)
        path = value.get("path")
        regex = value.get("regex", False)
        case_sensitive = value.get("case_sensitive", True)
        max_matches = value.get("max_matches", 80)
        context_lines = value.get("context_lines", 0)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("search action path must be a string when provided.", raw)
        if type(regex) is not bool:
            raise ActionParseError("search action regex must be a boolean when provided.", raw)
        if type(case_sensitive) is not bool:
            raise ActionParseError("search action case_sensitive must be a boolean when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 80
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=5)
        return SearchAction(
            type="search",
            query=query,
            path=path,
            regex=regex,
            case_sensitive=case_sensitive,
            max_matches=max_matches,
            context_lines=context_lines,
        )

    if action_type == "search_contexts":
        query = value.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("search_contexts action requires a non-empty query.", raw)
        path = value.get("path")
        regex = value.get("regex", False)
        case_sensitive = value.get("case_sensitive", True)
        max_matches = value.get("max_matches", 20)
        context_lines = value.get("context_lines", 3)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("search_contexts action path must be a string when provided.", raw)
        if type(regex) is not bool:
            raise ActionParseError("search_contexts action regex must be a boolean when provided.", raw)
        if type(case_sensitive) is not bool:
            raise ActionParseError("search_contexts action case_sensitive must be a boolean when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=100) or 20
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200_000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return SearchContextsAction(
            type="search_contexts",
            query=query,
            path=path,
            regex=regex,
            case_sensitive=case_sensitive,
            max_matches=max_matches,
            context_lines=context_lines,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "glob":
        pattern = value.get("pattern")
        max_matches = value.get("max_matches", 200)
        if not isinstance(pattern, str) or not pattern.strip():
            raise ActionParseError("glob action requires a non-empty pattern.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return GlobAction(type="glob", pattern=pattern, max_matches=max_matches)

    if action_type == "git_status":
        return GitStatusAction(type="git_status")

    if action_type == "git_conflicts":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_conflicts action path must be a string when provided.", raw)
        max_markers = parse_optional_positive_int(value.get("max_markers", 200), "max_markers", raw, maximum=1000) or 200
        max_files = parse_optional_positive_int(value.get("max_files", 5000), "max_files", raw, maximum=10000) or 5000
        return GitConflictsAction(
            type="git_conflicts",
            path=path,
            max_markers=max_markers,
            max_files=max_files,
        )

    if action_type == "git_info":
        return GitInfoAction(type="git_info")

    if action_type == "git_changes":
        return GitChangesAction(type="git_changes")

    if action_type == "git_branches":
        max_branches = parse_optional_positive_int(value.get("max_branches", 100), "max_branches", raw, maximum=500) or 100
        return GitBranchesAction(type="git_branches", max_branches=max_branches)

    if action_type == "check_git_fetch":
        remote = value.get("remote")
        if remote is not None and not isinstance(remote, str):
            raise ActionParseError("check_git_fetch action remote must be a string when provided.", raw)
        if isinstance(remote, str) and not remote.strip():
            raise ActionParseError("check_git_fetch action remote must be non-empty when provided.", raw)
        return CheckGitFetchAction(type="check_git_fetch", remote=remote.strip() if isinstance(remote, str) else None)

    if action_type == "git_fetch":
        remote = value.get("remote")
        if remote is not None and not isinstance(remote, str):
            raise ActionParseError("git_fetch action remote must be a string when provided.", raw)
        if isinstance(remote, str) and not remote.strip():
            raise ActionParseError("git_fetch action remote must be non-empty when provided.", raw)
        return GitFetchAction(type="git_fetch", remote=remote.strip() if isinstance(remote, str) else None)

    if action_type == "check_git_pull":
        return CheckGitPullAction(type="check_git_pull")

    if action_type == "git_pull":
        return GitPullAction(type="git_pull")

    if action_type == "check_git_push":
        return CheckGitPushAction(type="check_git_push")

    if action_type == "git_push":
        return GitPushAction(type="git_push")

    if action_type == "check_git_switch":
        branch = value.get("branch")
        create = value.get("create", False)
        if not isinstance(branch, str) or not branch.strip():
            raise ActionParseError("check_git_switch action requires a non-empty branch.", raw)
        if type(create) is not bool:
            raise ActionParseError("check_git_switch action create must be a boolean when provided.", raw)
        return CheckGitSwitchAction(type="check_git_switch", branch=branch.strip(), create=create)

    if action_type == "git_switch":
        branch = value.get("branch")
        create = value.get("create", False)
        if not isinstance(branch, str) or not branch.strip():
            raise ActionParseError("git_switch action requires a non-empty branch.", raw)
        if type(create) is not bool:
            raise ActionParseError("git_switch action create must be a boolean when provided.", raw)
        return GitSwitchAction(type="git_switch", branch=branch.strip(), create=create)

    if action_type == "check_git_stage":
        return CheckGitStageAction(type="check_git_stage", paths=parse_path_list(value.get("paths"), raw, "check_git_stage", maximum=100))

    if action_type == "git_stage":
        return GitStageAction(type="git_stage", paths=parse_path_list(value.get("paths"), raw, "git_stage", maximum=100))

    if action_type == "check_git_unstage":
        return CheckGitUnstageAction(type="check_git_unstage", paths=parse_path_list(value.get("paths"), raw, "check_git_unstage", maximum=100))

    if action_type == "git_unstage":
        return GitUnstageAction(type="git_unstage", paths=parse_path_list(value.get("paths"), raw, "git_unstage", maximum=100))

    if action_type == "check_git_restore":
        return CheckGitRestoreAction(type="check_git_restore", paths=parse_path_list(value.get("paths"), raw, "check_git_restore", maximum=100))

    if action_type == "git_restore":
        return GitRestoreAction(type="git_restore", paths=parse_path_list(value.get("paths"), raw, "git_restore", maximum=100))

    if action_type == "git_stashes":
        max_entries = parse_optional_positive_int(value.get("max_entries", 20), "max_entries", raw, maximum=100) or 20
        return GitStashesAction(type="git_stashes", max_entries=max_entries)

    if action_type == "check_git_stash":
        message = value.get("message")
        include_untracked = value.get("include_untracked", False)
        if message is not None and not isinstance(message, str):
            raise ActionParseError("check_git_stash action message must be a string when provided.", raw)
        if not isinstance(include_untracked, bool):
            raise ActionParseError("check_git_stash action include_untracked must be a boolean when provided.", raw)
        return CheckGitStashAction(type="check_git_stash", message=message, include_untracked=include_untracked)

    if action_type == "git_stash":
        message = value.get("message")
        include_untracked = value.get("include_untracked", False)
        if message is not None and not isinstance(message, str):
            raise ActionParseError("git_stash action message must be a string when provided.", raw)
        if not isinstance(include_untracked, bool):
            raise ActionParseError("git_stash action include_untracked must be a boolean when provided.", raw)
        return GitStashAction(type="git_stash", message=message, include_untracked=include_untracked)

    if action_type == "check_git_stash_apply":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("check_git_stash_apply action requires a non-empty stash_ref.", raw)
        return CheckGitStashApplyAction(type="check_git_stash_apply", stash_ref=stash_ref.strip())

    if action_type == "git_stash_apply":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("git_stash_apply action requires a non-empty stash_ref.", raw)
        return GitStashApplyAction(type="git_stash_apply", stash_ref=stash_ref.strip())

    if action_type == "check_git_stash_drop":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("check_git_stash_drop action requires a non-empty stash_ref.", raw)
        return CheckGitStashDropAction(type="check_git_stash_drop", stash_ref=stash_ref.strip())

    if action_type == "git_stash_drop":
        stash_ref = value.get("stash_ref")
        if not isinstance(stash_ref, str) or not stash_ref.strip():
            raise ActionParseError("git_stash_drop action requires a non-empty stash_ref.", raw)
        return GitStashDropAction(type="git_stash_drop", stash_ref=stash_ref.strip())

    if action_type == "check_git_commit":
        message = value.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ActionParseError("check_git_commit action requires a non-empty string message.", raw)
        if len(message.strip()) > 500:
            raise ActionParseError("check_git_commit action message must be at most 500 characters.", raw)
        return CheckGitCommitAction(type="check_git_commit", message=message.strip())

    if action_type == "git_commit":
        message = value.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ActionParseError("git_commit action requires a non-empty string message.", raw)
        if len(message.strip()) > 500:
            raise ActionParseError("git_commit action message must be at most 500 characters.", raw)
        return GitCommitAction(type="git_commit", message=message.strip())

    if action_type == "review_changes":
        max_files = parse_optional_positive_int(value.get("max_files", 200), "max_files", raw, maximum=500) or 200
        return ReviewChangesAction(type="review_changes", max_files=max_files)

    if action_type == "final_review":
        max_files = parse_optional_positive_int(value.get("max_files", 200), "max_files", raw, maximum=500) or 200
        max_checks = parse_optional_positive_int(value.get("max_checks", 10), "max_checks", raw, maximum=50) or 10
        return FinalReviewAction(type="final_review", max_files=max_files, max_checks=max_checks)

    if action_type == "suggest_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
        return SuggestChecksAction(type="suggest_checks", max_commands=max_commands)

    if action_type == "check_suggested_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=10) or 10
        return CheckSuggestedChecksAction(type="check_suggested_checks", max_commands=max_commands)

    if action_type == "run_suggested_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=10) or 10
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=600_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(value.get("max_output_chars"), "max_output_chars", raw, maximum=50_000)
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        stop_on_failure = value.get("stop_on_failure", True)
        if not isinstance(stop_on_failure, bool):
            raise ActionParseError("run_suggested_checks action stop_on_failure must be a boolean when provided.", raw)
        extract_output_contexts = value.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError("run_suggested_checks action extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = value.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError("run_suggested_checks action extract_output_diagnostics must be a boolean.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1_000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return RunSuggestedChecksAction(
            type="run_suggested_checks",
            max_commands=max_commands,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "project_commands":
        max_commands = parse_optional_positive_int(value.get("max_commands", 100), "max_commands", raw, maximum=500) or 100
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        return ProjectCommandsAction(type="project_commands", max_commands=max_commands, max_files=max_files)

    if action_type == "related_tests":
        raw_paths = value.get("paths")
        if raw_paths is not None:
            if not isinstance(raw_paths, list) or any(not isinstance(item, str) or not item.strip() for item in raw_paths):
                raise ActionParseError("related_tests action paths must be a list of non-empty strings when provided.", raw)
            paths = [item.strip() for item in raw_paths]
        else:
            paths = None
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        return RelatedTestsAction(
            type="related_tests",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
        )

    if action_type == "focused_test_commands":
        raw_paths = value.get("paths")
        if raw_paths is not None:
            if not isinstance(raw_paths, list) or any(not isinstance(item, str) or not item.strip() for item in raw_paths):
                raise ActionParseError("focused_test_commands action paths must be a list of non-empty strings when provided.", raw)
            paths = [item.strip() for item in raw_paths]
        else:
            paths = None
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 50), "max_commands", raw, maximum=500) or 50
        return FocusedTestCommandsAction(
            type="focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )

    if action_type == "check_focused_test_commands":
        raw_paths = value.get("paths")
        if raw_paths is not None:
            if not isinstance(raw_paths, list) or any(not isinstance(item, str) or not item.strip() for item in raw_paths):
                raise ActionParseError("check_focused_test_commands action paths must be a list of non-empty strings when provided.", raw)
            paths = [item.strip() for item in raw_paths]
        else:
            paths = None
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=50) or 10
        return CheckFocusedTestCommandsAction(
            type="check_focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )

    if action_type == "run_focused_test_commands":
        raw_paths = value.get("paths")
        if raw_paths is not None:
            if not isinstance(raw_paths, list) or any(not isinstance(item, str) or not item.strip() for item in raw_paths):
                raise ActionParseError("run_focused_test_commands action paths must be a list of non-empty strings when provided.", raw)
            paths = [item.strip() for item in raw_paths]
        else:
            paths = None
        max_paths = parse_optional_positive_int(value.get("max_paths", 100), "max_paths", raw, maximum=500) or 100
        max_candidates = parse_optional_positive_int(value.get("max_candidates", 200), "max_candidates", raw, maximum=1000) or 200
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=50) or 10
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=600_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(value.get("max_output_chars"), "max_output_chars", raw, maximum=50_000)
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        stop_on_failure = value.get("stop_on_failure", True)
        if not isinstance(stop_on_failure, bool):
            raise ActionParseError("run_focused_test_commands action stop_on_failure must be a boolean when provided.", raw)
        extract_output_contexts = value.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError("run_focused_test_commands action extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = value.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError("run_focused_test_commands action extract_output_diagnostics must be a boolean.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1_000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return RunFocusedTestCommandsAction(
            type="run_focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "project_manifests":
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        max_items = parse_optional_positive_int(value.get("max_items", 500), "max_items", raw, maximum=2000) or 500
        return ProjectManifestsAction(type="project_manifests", max_files=max_files, max_items=max_items)

    if action_type == "project_instructions":
        max_files = parse_optional_positive_int(value.get("max_files", 20), "max_files", raw, maximum=200) or 20
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 12_000), "max_bytes", raw, maximum=50_000) or 12_000
        if max_bytes < 200:
            raise ActionParseError("max_bytes must be at least 200.", raw)
        return ProjectInstructionsAction(type="project_instructions", max_files=max_files, max_bytes=max_bytes)

    if action_type == "project_todos":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("project_todos action path must be a string when provided.", raw)
        max_items = parse_optional_positive_int(value.get("max_items", 100), "max_items", raw, maximum=500) or 100
        max_files = parse_optional_positive_int(value.get("max_files", 1000), "max_files", raw, maximum=5000) or 1000
        return ProjectTodosAction(
            type="project_todos",
            path=path.strip() if isinstance(path, str) and path.strip() else None,
            max_items=max_items,
            max_files=max_files,
        )

    if action_type == "project_overview":
        max_files = parse_optional_positive_int(value.get("max_files", 80), "max_files", raw, maximum=200) or 80
        max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
        max_checks = parse_optional_positive_int(value.get("max_checks", 10), "max_checks", raw, maximum=50) or 10
        max_manifests = parse_optional_positive_int(value.get("max_manifests", 10), "max_manifests", raw, maximum=50) or 10
        return ProjectOverviewAction(
            type="project_overview",
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_manifests=max_manifests,
        )

    if action_type == "command_check":
        command = value.get("command")
        cwd = value.get("cwd")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError("command_check action requires a non-empty command.", raw)
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("command_check action cwd must be a string when provided.", raw)
        return CommandCheckAction(type="command_check", command=command, cwd=cwd)

    if action_type == "check_run_commands":
        return CheckRunCommandsAction(
            type="check_run_commands",
            commands=parse_run_command_items(value.get("commands"), raw, "check_run_commands"),
        )

    if action_type == "port_check":
        port = parse_optional_positive_int(value.get("port"), "port", raw, maximum=65_535)
        if port is None:
            raise ActionParseError("port_check action requires port.", raw)
        host = value.get("host", "127.0.0.1")
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=10_000)
        if port < 1:
            raise ActionParseError("port must be at least 1.", raw)
        if not isinstance(host, str) or not host.strip():
            raise ActionParseError("port_check action host must be a non-empty string when provided.", raw)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        return PortCheckAction(type="port_check", host=host, port=port, timeout_ms=timeout_ms)

    if action_type == "http_check":
        url = value.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ActionParseError("http_check action requires a non-empty url.", raw)
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ActionParseError("http_check action url must be an http or https URL.", raw)
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=10_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        max_body_chars = parse_optional_nonnegative_int(
            value.get("max_body_chars"),
            "max_body_chars",
            raw,
            maximum=50_000,
        )
        contains = value.get("contains")
        if contains is not None and (not isinstance(contains, str) or not contains.strip()):
            raise ActionParseError("http_check action contains must be a non-empty string when provided.", raw)
        regex = value.get("regex", False)
        if not isinstance(regex, bool):
            raise ActionParseError("http_check action regex must be a boolean when provided.", raw)
        return HttpCheckAction(
            type="http_check",
            url=url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            contains=contains,
            regex=regex,
        )

    if action_type == "http_fetch":
        url = value.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ActionParseError("http_fetch action requires a non-empty url.", raw)
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ActionParseError("http_fetch action url must be an http or https URL.", raw)
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=10_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        max_body_chars = parse_optional_positive_int(value.get("max_body_chars"), "max_body_chars", raw, maximum=100_000)
        return HttpFetchAction(
            type="http_fetch",
            url=url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
        )

    if action_type == "environment_info":
        return EnvironmentInfoAction(type="environment_info")

    if action_type == "git_diff":
        path = value.get("path")
        staged = value.get("staged", False)
        max_output_chars = value.get("max_output_chars", 12000)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_diff action path must be a string when provided.", raw)
        if type(staged) is not bool:
            raise ActionParseError("git_diff action staged must be a boolean when provided.", raw)
        max_output_chars = parse_optional_positive_int(max_output_chars, "max_output_chars", raw, maximum=50000) or 12000
        if max_output_chars < 1000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        return GitDiffAction(type="git_diff", path=path, staged=staged, max_output_chars=max_output_chars)

    if action_type == "git_diff_hunks":
        path = value.get("path")
        staged = value.get("staged", False)
        max_hunks = value.get("max_hunks", 80)
        max_lines_per_hunk = value.get("max_lines_per_hunk", 80)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_diff_hunks action path must be a string when provided.", raw)
        if type(staged) is not bool:
            raise ActionParseError("git_diff_hunks action staged must be a boolean when provided.", raw)
        max_hunks = parse_optional_positive_int(max_hunks, "max_hunks", raw, maximum=500) or 80
        max_lines_per_hunk = parse_optional_positive_int(max_lines_per_hunk, "max_lines_per_hunk", raw, maximum=500) or 80
        return GitDiffHunksAction(
            type="git_diff_hunks",
            path=path,
            staged=staged,
            max_hunks=max_hunks,
            max_lines_per_hunk=max_lines_per_hunk,
        )

    if action_type == "git_diff_contexts":
        path = value.get("path")
        staged = value.get("staged", False)
        context_lines = value.get("context_lines", 5)
        max_hunks = value.get("max_hunks", 80)
        max_bytes_per_context = value.get("max_bytes_per_context", 20_000)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_diff_contexts action path must be a string when provided.", raw)
        if type(staged) is not bool:
            raise ActionParseError("git_diff_contexts action staged must be a boolean when provided.", raw)
        context_lines = parse_nonnegative_int(context_lines, "context_lines", raw, maximum=50)
        max_hunks = parse_optional_positive_int(max_hunks, "max_hunks", raw, maximum=500) or 80
        max_bytes_per_context = parse_optional_positive_int(max_bytes_per_context, "max_bytes_per_context", raw, maximum=200000) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return GitDiffContextsAction(
            type="git_diff_contexts",
            path=path,
            staged=staged,
            context_lines=context_lines,
            max_hunks=max_hunks,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "git_log":
        path = value.get("path")
        max_count = value.get("max_count", 5)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_log action path must be a string when provided.", raw)
        max_count = parse_optional_positive_int(max_count, "max_count", raw, maximum=50) or 5
        return GitLogAction(type="git_log", path=path, max_count=max_count)

    if action_type == "git_show":
        rev = value.get("rev", "HEAD")
        path = value.get("path")
        max_output_chars = value.get("max_output_chars", 12000)
        if not isinstance(rev, str) or not rev.strip():
            raise ActionParseError("git_show action rev must be a non-empty string.", raw)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("git_show action path must be a string when provided.", raw)
        max_output_chars = parse_optional_positive_int(max_output_chars, "max_output_chars", raw, maximum=50000) or 12000
        if max_output_chars < 1000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        return GitShowAction(type="git_show", rev=rev.strip(), path=path, max_output_chars=max_output_chars)

    if action_type == "git_blame":
        path = value.get("path")
        start_line = value.get("start_line")
        line_count = value.get("line_count")
        max_output_chars = value.get("max_output_chars", 12000)
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError("git_blame action path must be a non-empty string.", raw)
        if start_line is not None:
            start_line = parse_optional_positive_int(start_line, "start_line", raw, maximum=None)
        if line_count is not None:
            line_count = parse_optional_positive_int(line_count, "line_count", raw, maximum=1000)
        max_output_chars = parse_optional_positive_int(max_output_chars, "max_output_chars", raw, maximum=50000) or 12000
        if max_output_chars < 1000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        return GitBlameAction(
            type="git_blame",
            path=path.strip(),
            start_line=start_line,
            line_count=line_count,
            max_output_chars=max_output_chars,
        )

    if action_type == "session_summary":
        run_id = value.get("run_id")
        recent_limit = value.get("recent_limit", 5)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_summary action run_id must be a string when provided.", raw)
        recent_limit = parse_optional_positive_int(recent_limit, "recent_limit", raw, maximum=20) or 5
        return SessionSummaryAction(type="session_summary", run_id=run_id, recent_limit=recent_limit)

    if action_type == "session_plan":
        run_id = value.get("run_id")
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_plan action run_id must be a string when provided.", raw)
        return SessionPlanAction(type="session_plan", run_id=run_id)

    if action_type == "session_transcript":
        run_id = value.get("run_id")
        max_events = value.get("max_events", 80)
        max_text = value.get("max_text", 500)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_transcript action run_id must be a string when provided.", raw)
        max_events = parse_optional_positive_int(max_events, "max_events", raw, maximum=500) or 80
        max_text = parse_optional_positive_int(max_text, "max_text", raw, maximum=5000) or 500
        if max_text < 80:
            raise ActionParseError("max_text must be at least 80.", raw)
        return SessionTranscriptAction(
            type="session_transcript",
            run_id=run_id,
            max_events=max_events,
            max_text=max_text,
        )

    if action_type == "session_search":
        query = value.get("query")
        run_id = value.get("run_id")
        max_matches = value.get("max_matches", 20)
        max_text = value.get("max_text", 500)
        case_sensitive = value.get("case_sensitive", False)
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("session_search action query must be a non-empty string.", raw)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_search action run_id must be a string when provided.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=100) or 20
        max_text = parse_optional_positive_int(max_text, "max_text", raw, maximum=5000) or 500
        if max_text < 80:
            raise ActionParseError("max_text must be at least 80.", raw)
        if not isinstance(case_sensitive, bool):
            raise ActionParseError("session_search action case_sensitive must be a boolean.", raw)
        return SessionSearchAction(
            type="session_search",
            query=query,
            run_id=run_id,
            max_matches=max_matches,
            max_text=max_text,
            case_sensitive=case_sensitive,
        )

    if action_type == "session_commands":
        run_id = value.get("run_id")
        max_commands = value.get("max_commands", 20)
        max_output_chars = value.get("max_output_chars", 2_000)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_commands action run_id must be a string when provided.", raw)
        max_commands = parse_optional_positive_int(max_commands, "max_commands", raw, maximum=100) or 20
        if not isinstance(max_output_chars, int):
            raise ActionParseError("max_output_chars must be an integer.", raw)
        if max_output_chars < 0:
            raise ActionParseError("max_output_chars must be at least 0.", raw)
        if max_output_chars > 20_000:
            raise ActionParseError("max_output_chars must be at most 20000.", raw)
        return SessionCommandsAction(
            type="session_commands",
            run_id=run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )

    if action_type == "session_output_contexts":
        run_id = value.get("run_id")
        max_commands = value.get("max_commands", 20)
        max_output_chars = value.get("max_output_chars", 20_000)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_output_contexts action run_id must be a string when provided.", raw)
        max_commands = parse_optional_positive_int(max_commands, "max_commands", raw, maximum=100) or 20
        if not isinstance(max_output_chars, int):
            raise ActionParseError("max_output_chars must be an integer.", raw)
        if max_output_chars < 0:
            raise ActionParseError("max_output_chars must be at least 0.", raw)
        if max_output_chars > 20_000:
            raise ActionParseError("max_output_chars must be at most 20000.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return SessionOutputContextsAction(
            type="session_output_contexts",
            run_id=run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "session_output_diagnostics":
        run_id = value.get("run_id")
        max_commands = value.get("max_commands", 20)
        max_output_chars = value.get("max_output_chars", 20_000)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_output_diagnostics action run_id must be a string when provided.", raw)
        max_commands = parse_optional_positive_int(max_commands, "max_commands", raw, maximum=100) or 20
        if not isinstance(max_output_chars, int):
            raise ActionParseError("max_output_chars must be an integer.", raw)
        if max_output_chars < 0:
            raise ActionParseError("max_output_chars must be at least 0.", raw)
        if max_output_chars > 20_000:
            raise ActionParseError("max_output_chars must be at most 20000.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 2), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return SessionOutputDiagnosticsAction(
            type="session_output_diagnostics",
            run_id=run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "session_files":
        run_id = value.get("run_id")
        max_files = value.get("max_files", 100)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_files action run_id must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 100
        return SessionFilesAction(type="session_files", run_id=run_id, max_files=max_files)

    if action_type == "session_failures":
        run_id = value.get("run_id")
        max_failures = value.get("max_failures", 50)
        max_text = value.get("max_text", 500)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_failures action run_id must be a string when provided.", raw)
        max_failures = parse_optional_positive_int(max_failures, "max_failures", raw, maximum=200) or 50
        max_text = parse_optional_positive_int(max_text, "max_text", raw, maximum=5000) or 500
        if max_text < 80:
            raise ActionParseError("max_text must be at least 80.", raw)
        return SessionFailuresAction(
            type="session_failures",
            run_id=run_id,
            max_failures=max_failures,
            max_text=max_text,
        )

    if action_type == "session_verification":
        run_id = value.get("run_id")
        max_checks = parse_optional_positive_int(value.get("max_checks", 50), "max_checks", raw, maximum=500) or 50
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_verification action run_id must be a string when provided.", raw)
        return SessionVerificationAction(type="session_verification", run_id=run_id, max_checks=max_checks)

    if action_type == "session_audit":
        run_id = value.get("run_id")
        max_failures = value.get("max_failures", 10)
        max_files = value.get("max_files", 20)
        max_commands = value.get("max_commands", 10)
        max_checks = value.get("max_checks", 50)
        max_text = value.get("max_text", 300)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_audit action run_id must be a string when provided.", raw)
        max_failures = parse_optional_positive_int(max_failures, "max_failures", raw, maximum=200) or 10
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 20
        max_commands = parse_optional_positive_int(max_commands, "max_commands", raw, maximum=100) or 10
        max_checks = parse_optional_positive_int(max_checks, "max_checks", raw, maximum=500) or 50
        max_text = parse_optional_positive_int(max_text, "max_text", raw, maximum=5000) or 300
        if max_text < 80:
            raise ActionParseError("max_text must be at least 80.", raw)
        return SessionAuditAction(
            type="session_audit",
            run_id=run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )

    if action_type == "session_handoff":
        run_id = value.get("run_id")
        max_failures = value.get("max_failures", 20)
        max_files = value.get("max_files", 50)
        max_commands = value.get("max_commands", 10)
        max_checks = value.get("max_checks", 50)
        max_output_chars = value.get("max_output_chars", 1_000)
        max_text = value.get("max_text", 500)
        if run_id is not None and not isinstance(run_id, str):
            raise ActionParseError("session_handoff action run_id must be a string when provided.", raw)
        max_failures = parse_optional_positive_int(max_failures, "max_failures", raw, maximum=200) or 20
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 50
        max_commands = parse_optional_positive_int(max_commands, "max_commands", raw, maximum=100) or 10
        max_checks = parse_optional_positive_int(max_checks, "max_checks", raw, maximum=500) or 50
        if not isinstance(max_output_chars, int):
            raise ActionParseError("max_output_chars must be an integer.", raw)
        if max_output_chars < 0:
            raise ActionParseError("max_output_chars must be at least 0.", raw)
        if max_output_chars > 20_000:
            raise ActionParseError("max_output_chars must be at most 20000.", raw)
        max_text = parse_optional_positive_int(max_text, "max_text", raw, maximum=5000) or 500
        if max_text < 80:
            raise ActionParseError("max_text must be at least 80.", raw)
        return SessionHandoffAction(
            type="session_handoff",
            run_id=run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )

    if action_type == "checkpoint_create":
        label = value.get("label")
        if label is not None and not isinstance(label, str):
            raise ActionParseError("checkpoint_create action label must be a string when provided.", raw)
        return CheckpointCreateAction(type="checkpoint_create", label=label)

    if action_type == "checkpoint_list":
        max_entries = parse_optional_positive_int(value.get("max_entries", 20), "max_entries", raw, maximum=100) or 20
        return CheckpointListAction(type="checkpoint_list", max_entries=max_entries)

    if action_type == "checkpoint_show":
        checkpoint_id = value.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
            raise ActionParseError("checkpoint_show action requires a non-empty checkpoint_id.", raw)
        return CheckpointShowAction(type="checkpoint_show", checkpoint_id=checkpoint_id.strip())

    if action_type == "checkpoint_diff":
        checkpoint_id = value.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
            raise ActionParseError("checkpoint_diff action requires a non-empty checkpoint_id.", raw)
        max_chars = parse_optional_positive_int(value.get("max_chars", 40_000), "max_chars", raw, maximum=200_000) or 40_000
        if max_chars < 100:
            raise ActionParseError("max_chars must be at least 100.", raw)
        return CheckpointDiffAction(type="checkpoint_diff", checkpoint_id=checkpoint_id.strip(), max_chars=max_chars)

    if action_type == "checkpoint_status":
        checkpoint_id = value.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
            raise ActionParseError("checkpoint_status action requires a non-empty checkpoint_id.", raw)
        return CheckpointStatusAction(type="checkpoint_status", checkpoint_id=checkpoint_id.strip())

    if action_type == "check_checkpoint_restore":
        checkpoint_id = value.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
            raise ActionParseError("check_checkpoint_restore action requires a non-empty checkpoint_id.", raw)
        return CheckCheckpointRestoreAction(type="check_checkpoint_restore", checkpoint_id=checkpoint_id.strip())

    if action_type == "checkpoint_restore":
        checkpoint_id = value.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
            raise ActionParseError("checkpoint_restore action requires a non-empty checkpoint_id.", raw)
        return CheckpointRestoreAction(type="checkpoint_restore", checkpoint_id=checkpoint_id.strip())

    if action_type == "check_checkpoint_delete":
        checkpoint_id = value.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
            raise ActionParseError("check_checkpoint_delete action requires a non-empty checkpoint_id.", raw)
        return CheckCheckpointDeleteAction(type="check_checkpoint_delete", checkpoint_id=checkpoint_id.strip())

    if action_type == "checkpoint_delete":
        checkpoint_id = value.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
            raise ActionParseError("checkpoint_delete action requires a non-empty checkpoint_id.", raw)
        return CheckpointDeleteAction(type="checkpoint_delete", checkpoint_id=checkpoint_id.strip())

    if action_type == "check_checkpoint_prune":
        keep_last = parse_optional_nonnegative_int(value.get("keep_last"), "keep_last", raw, maximum=1000)
        if keep_last is None:
            raise ActionParseError("check_checkpoint_prune action requires keep_last.", raw)
        return CheckCheckpointPruneAction(type="check_checkpoint_prune", keep_last=keep_last)

    if action_type == "checkpoint_prune":
        keep_last = parse_optional_nonnegative_int(value.get("keep_last"), "keep_last", raw, maximum=1000)
        if keep_last is None:
            raise ActionParseError("checkpoint_prune action requires keep_last.", raw)
        return CheckpointPruneAction(type="checkpoint_prune", keep_last=keep_last)

    if action_type == "check_edit_file":
        path = value.get("path")
        old = value.get("old")
        new = value.get("new")
        if not isinstance(path, str):
            raise ActionParseError("check_edit_file action requires a string path.", raw)
        if not isinstance(old, str):
            raise ActionParseError("check_edit_file action requires string old.", raw)
        if not isinstance(new, str):
            raise ActionParseError("check_edit_file action requires string new.", raw)
        return CheckEditFileAction(type="check_edit_file", path=path, old=old, new=new)

    if action_type == "edit_file":
        path = value.get("path")
        old = value.get("old")
        new = value.get("new")
        if not isinstance(path, str):
            raise ActionParseError("edit_file action requires a string path.", raw)
        if not isinstance(old, str):
            raise ActionParseError("edit_file action requires string old.", raw)
        if not isinstance(new, str):
            raise ActionParseError("edit_file action requires string new.", raw)
        return EditFileAction(type="edit_file", path=path, old=old, new=new)

    if action_type == "check_multi_edit_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("check_multi_edit_file action requires a string path.", raw)
        return CheckMultiEditAction(
            type="check_multi_edit_file",
            path=path,
            edits=parse_edit_operations(value.get("edits"), raw, action_type="check_multi_edit_file"),
        )

    if action_type == "multi_edit_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("multi_edit_file action requires a string path.", raw)
        return MultiEditAction(type="multi_edit_file", path=path, edits=parse_edit_operations(value.get("edits"), raw))

    if action_type == "check_replace_lines":
        path = value.get("path")
        start_line = value.get("start_line")
        end_line = value.get("end_line")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("check_replace_lines action requires a string path.", raw)
        start_line = parse_optional_positive_int(start_line, "start_line", raw, maximum=None)
        end_line = parse_optional_positive_int(end_line, "end_line", raw, maximum=None)
        if start_line is None:
            raise ActionParseError("check_replace_lines action requires start_line.", raw)
        if end_line is None:
            raise ActionParseError("check_replace_lines action requires end_line.", raw)
        if end_line < start_line:
            raise ActionParseError("end_line must be greater than or equal to start_line.", raw)
        if not isinstance(content, str):
            raise ActionParseError("check_replace_lines action requires string content.", raw)
        return CheckReplaceLinesAction(
            type="check_replace_lines",
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
        )

    if action_type == "replace_lines":
        path = value.get("path")
        start_line = value.get("start_line")
        end_line = value.get("end_line")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("replace_lines action requires a string path.", raw)
        start_line = parse_optional_positive_int(start_line, "start_line", raw, maximum=None)
        end_line = parse_optional_positive_int(end_line, "end_line", raw, maximum=None)
        if start_line is None:
            raise ActionParseError("replace_lines action requires start_line.", raw)
        if end_line is None:
            raise ActionParseError("replace_lines action requires end_line.", raw)
        if end_line < start_line:
            raise ActionParseError("end_line must be greater than or equal to start_line.", raw)
        if not isinstance(content, str):
            raise ActionParseError("replace_lines action requires string content.", raw)
        return ReplaceLinesAction(
            type="replace_lines",
            path=path,
            start_line=start_line,
            end_line=end_line,
            content=content,
        )

    if action_type == "check_insert_lines":
        path = value.get("path")
        line = value.get("line")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("check_insert_lines action requires a string path.", raw)
        line = parse_optional_positive_int(line, "line", raw, maximum=None)
        if line is None:
            raise ActionParseError("check_insert_lines action requires line.", raw)
        if not isinstance(content, str) or content == "":
            raise ActionParseError("check_insert_lines action requires non-empty string content.", raw)
        return CheckInsertLinesAction(type="check_insert_lines", path=path, line=line, content=content)

    if action_type == "insert_lines":
        path = value.get("path")
        line = value.get("line")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("insert_lines action requires a string path.", raw)
        line = parse_optional_positive_int(line, "line", raw, maximum=None)
        if line is None:
            raise ActionParseError("insert_lines action requires line.", raw)
        if not isinstance(content, str) or content == "":
            raise ActionParseError("insert_lines action requires non-empty string content.", raw)
        return InsertLinesAction(type="insert_lines", path=path, line=line, content=content)

    if action_type == "check_append_file":
        path = value.get("path")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("check_append_file action requires a string path.", raw)
        if not isinstance(content, str) or content == "":
            raise ActionParseError("check_append_file action requires non-empty string content.", raw)
        return CheckAppendFileAction(type="check_append_file", path=path, content=content)

    if action_type == "append_file":
        path = value.get("path")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("append_file action requires a string path.", raw)
        if not isinstance(content, str) or content == "":
            raise ActionParseError("append_file action requires non-empty string content.", raw)
        return AppendFileAction(type="append_file", path=path, content=content)

    if action_type == "check_regex_replace":
        path = value.get("path")
        pattern = value.get("pattern")
        replacement = value.get("replacement")
        if not isinstance(path, str):
            raise ActionParseError("check_regex_replace action requires a string path.", raw)
        if not isinstance(pattern, str) or pattern == "":
            raise ActionParseError("check_regex_replace action requires a non-empty string pattern.", raw)
        if not isinstance(replacement, str):
            raise ActionParseError("check_regex_replace action requires string replacement.", raw)
        count = parse_optional_nonnegative_int(value.get("count", 0), "count", raw, maximum=1000)
        max_replacements = parse_optional_positive_int(value.get("max_replacements", 100), "max_replacements", raw, maximum=1000)
        case_sensitive = value.get("case_sensitive", True)
        multiline = value.get("multiline", False)
        if type(case_sensitive) is not bool:
            raise ActionParseError("check_regex_replace action case_sensitive must be a boolean.", raw)
        if type(multiline) is not bool:
            raise ActionParseError("check_regex_replace action multiline must be a boolean.", raw)
        return CheckRegexReplaceAction(
            type="check_regex_replace",
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count if count is not None else 0,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements if max_replacements is not None else 100,
        )

    if action_type == "regex_replace":
        path = value.get("path")
        pattern = value.get("pattern")
        replacement = value.get("replacement")
        if not isinstance(path, str):
            raise ActionParseError("regex_replace action requires a string path.", raw)
        if not isinstance(pattern, str) or pattern == "":
            raise ActionParseError("regex_replace action requires a non-empty string pattern.", raw)
        if not isinstance(replacement, str):
            raise ActionParseError("regex_replace action requires string replacement.", raw)
        count = parse_optional_nonnegative_int(value.get("count", 0), "count", raw, maximum=1000)
        max_replacements = parse_optional_positive_int(value.get("max_replacements", 100), "max_replacements", raw, maximum=1000)
        case_sensitive = value.get("case_sensitive", True)
        multiline = value.get("multiline", False)
        if type(case_sensitive) is not bool:
            raise ActionParseError("regex_replace action case_sensitive must be a boolean.", raw)
        if type(multiline) is not bool:
            raise ActionParseError("regex_replace action multiline must be a boolean.", raw)
        return RegexReplaceAction(
            type="regex_replace",
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count if count is not None else 0,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements if max_replacements is not None else 100,
        )

    if action_type == "check_patch":
        path = value.get("path")
        patch = value.get("patch")
        if not isinstance(path, str):
            raise ActionParseError("check_patch action requires a string path.", raw)
        if not isinstance(patch, str):
            raise ActionParseError("check_patch action requires string patch.", raw)
        return CheckPatchAction(type="check_patch", path=path, patch=patch)

    if action_type == "check_patches":
        patch = value.get("patch")
        if not isinstance(patch, str):
            raise ActionParseError("check_patches action requires string patch.", raw)
        return CheckPatchesAction(type="check_patches", patch=patch)

    if action_type == "patch_file":
        path = value.get("path")
        patch = value.get("patch")
        if not isinstance(path, str):
            raise ActionParseError("patch_file action requires a string path.", raw)
        if not isinstance(patch, str):
            raise ActionParseError("patch_file action requires string patch.", raw)
        return PatchFileAction(type="patch_file", path=path, patch=patch)

    if action_type == "patch_files":
        patch = value.get("patch")
        if not isinstance(patch, str):
            raise ActionParseError("patch_files action requires string patch.", raw)
        return PatchFilesAction(type="patch_files", patch=patch)

    if action_type == "check_write_file":
        path = value.get("path")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("check_write_file action requires a string path.", raw)
        if not isinstance(content, str):
            raise ActionParseError("check_write_file action requires string content.", raw)
        return CheckWriteFileAction(type="check_write_file", path=path, content=content)

    if action_type == "write_file":
        path = value.get("path")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("write_file action requires a string path.", raw)
        if not isinstance(content, str):
            raise ActionParseError("write_file action requires string content.", raw)
        return WriteFileAction(type="write_file", path=path, content=content)

    if action_type == "check_write_files":
        return CheckWriteFilesAction(
            type="check_write_files",
            files=parse_write_file_items(value.get("files"), raw, action_type="check_write_files"),
        )

    if action_type == "write_files":
        return WriteFilesAction(type="write_files", files=parse_write_file_items(value.get("files"), raw))

    if action_type == "check_delete_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("check_delete_file action requires a string path.", raw)
        return CheckDeleteFileAction(type="check_delete_file", path=path)

    if action_type == "delete_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("delete_file action requires a string path.", raw)
        return DeleteFileAction(type="delete_file", path=path)

    if action_type == "check_delete_files":
        return CheckDeleteFilesAction(
            type="check_delete_files",
            paths=parse_path_list(value.get("paths"), raw, "check_delete_files", maximum=100),
        )

    if action_type == "delete_files":
        return DeleteFilesAction(
            type="delete_files",
            paths=parse_path_list(value.get("paths"), raw, "delete_files", maximum=100),
        )

    if action_type == "check_move_file":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("check_move_file action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("check_move_file action requires string destination.", raw)
        return CheckMoveFileAction(type="check_move_file", source=source, destination=destination)

    if action_type == "move_file":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("move_file action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("move_file action requires string destination.", raw)
        return MoveFileAction(type="move_file", source=source, destination=destination)

    if action_type == "check_move_files":
        return CheckMoveFilesAction(
            type="check_move_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "check_move_files"),
        )

    if action_type == "move_files":
        return MoveFilesAction(
            type="move_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "move_files"),
        )

    if action_type == "check_copy_file":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("check_copy_file action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("check_copy_file action requires string destination.", raw)
        return CheckCopyFileAction(type="check_copy_file", source=source, destination=destination)

    if action_type == "copy_file":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("copy_file action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("copy_file action requires string destination.", raw)
        return CopyFileAction(type="copy_file", source=source, destination=destination)

    if action_type == "check_copy_files":
        return CheckCopyFilesAction(
            type="check_copy_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "check_copy_files"),
        )

    if action_type == "copy_files":
        return CopyFilesAction(
            type="copy_files",
            transfers=parse_move_file_transfers(value.get("transfers"), raw, "copy_files"),
        )

    if action_type == "check_move_dir":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("check_move_dir action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("check_move_dir action requires string destination.", raw)
        return CheckMoveDirectoryAction(type="check_move_dir", source=source, destination=destination)

    if action_type == "move_dir":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("move_dir action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("move_dir action requires string destination.", raw)
        return MoveDirectoryAction(type="move_dir", source=source, destination=destination)

    if action_type == "check_move_dirs":
        return CheckMoveDirectoriesAction(
            type="check_move_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "check_move_dirs"),
        )

    if action_type == "move_dirs":
        return MoveDirectoriesAction(
            type="move_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "move_dirs"),
        )

    if action_type == "check_copy_dir":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("check_copy_dir action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("check_copy_dir action requires string destination.", raw)
        return CheckCopyDirectoryAction(type="check_copy_dir", source=source, destination=destination)

    if action_type == "check_copy_dirs":
        return CheckCopyDirectoriesAction(
            type="check_copy_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "check_copy_dirs"),
        )

    if action_type == "copy_dir":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("copy_dir action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("copy_dir action requires string destination.", raw)
        return CopyDirectoryAction(type="copy_dir", source=source, destination=destination)

    if action_type == "copy_dirs":
        return CopyDirectoriesAction(
            type="copy_dirs",
            transfers=parse_directory_transfers(value.get("transfers"), raw, "copy_dirs"),
        )

    if action_type == "check_create_dir":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("check_create_dir action requires a string path.", raw)
        return CheckCreateDirectoryAction(type="check_create_dir", path=path)

    if action_type == "check_create_dirs":
        return CheckCreateDirectoriesAction(
            type="check_create_dirs",
            paths=parse_path_list(value.get("paths"), raw, "check_create_dirs", maximum=100),
        )

    if action_type == "create_dir":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("create_dir action requires a string path.", raw)
        return CreateDirectoryAction(type="create_dir", path=path)

    if action_type == "create_dirs":
        return CreateDirectoriesAction(
            type="create_dirs",
            paths=parse_path_list(value.get("paths"), raw, "create_dirs", maximum=100),
        )

    if action_type == "check_delete_empty_dir":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("check_delete_empty_dir action requires a string path.", raw)
        return CheckDeleteEmptyDirectoryAction(type="check_delete_empty_dir", path=path)

    if action_type == "check_delete_empty_dirs":
        return CheckDeleteEmptyDirectoriesAction(
            type="check_delete_empty_dirs",
            paths=parse_path_list(value.get("paths"), raw, "check_delete_empty_dirs", maximum=100),
        )

    if action_type == "delete_empty_dir":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("delete_empty_dir action requires a string path.", raw)
        return DeleteEmptyDirectoryAction(type="delete_empty_dir", path=path)

    if action_type == "delete_empty_dirs":
        return DeleteEmptyDirectoriesAction(
            type="delete_empty_dirs",
            paths=parse_path_list(value.get("paths"), raw, "delete_empty_dirs", maximum=100),
        )

    if action_type == "check_set_executable":
        path = value.get("path")
        executable = value.get("executable", True)
        if not isinstance(path, str):
            raise ActionParseError("check_set_executable action requires a string path.", raw)
        if not isinstance(executable, bool):
            raise ActionParseError("check_set_executable action executable must be a boolean.", raw)
        return CheckSetExecutableAction(type="check_set_executable", path=path, executable=executable)

    if action_type == "set_executable":
        path = value.get("path")
        executable = value.get("executable", True)
        if not isinstance(path, str):
            raise ActionParseError("set_executable action requires a string path.", raw)
        if not isinstance(executable, bool):
            raise ActionParseError("set_executable action executable must be a boolean.", raw)
        return SetExecutableAction(type="set_executable", path=path, executable=executable)

    if action_type == "run_command":
        command = value.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError("run_command action requires a non-empty command.", raw)
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=600_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(
            value.get("max_output_chars"),
            "max_output_chars",
            raw,
            maximum=50_000,
        )
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("run_command action cwd must be a string when provided.", raw)
        extract_output_contexts = value.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError("run_command action extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = value.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError("run_command action extract_output_diagnostics must be a boolean.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1_000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return RunCommandAction(
            type="run_command",
            command=command,
            timeout_ms=timeout_ms,
            cwd=cwd,
            max_output_chars=max_output_chars,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "run_commands":
        stop_on_failure = value.get("stop_on_failure", True)
        if not isinstance(stop_on_failure, bool):
            raise ActionParseError("run_commands action stop_on_failure must be a boolean when provided.", raw)
        return RunCommandsAction(
            type="run_commands",
            commands=parse_run_command_items(value.get("commands"), raw, "run_commands"),
            stop_on_failure=stop_on_failure,
        )

    if action_type == "check_start_command":
        command = value.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError("check_start_command action requires a non-empty command.", raw)
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("check_start_command action cwd must be a string when provided.", raw)
        return CheckStartCommandAction(type="check_start_command", command=command, cwd=cwd)

    if action_type == "start_command":
        command = value.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError("start_command action requires a non-empty command.", raw)
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("start_command action cwd must be a string when provided.", raw)
        return StartCommandAction(type="start_command", command=command, cwd=cwd)

    if action_type == "read_process":
        process_id = value.get("process_id")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("read_process action requires a non-empty process_id.", raw)
        max_output_chars = parse_optional_positive_int(
            value.get("max_output_chars"),
            "max_output_chars",
            raw,
            maximum=50_000,
        )
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        return ReadProcessAction(type="read_process", process_id=process_id, max_output_chars=max_output_chars)

    if action_type == "process_output_contexts":
        process_id = value.get("process_id")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("process_output_contexts action requires a non-empty process_id.", raw)
        max_output_chars = value.get("max_output_chars", 20_000)
        if not isinstance(max_output_chars, int):
            raise ActionParseError("max_output_chars must be an integer.", raw)
        if max_output_chars < 0:
            raise ActionParseError("max_output_chars must be at least 0.", raw)
        if max_output_chars > 50_000:
            raise ActionParseError("max_output_chars must be at most 50000.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=500)
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return ProcessOutputContextsAction(
            type="process_output_contexts",
            process_id=process_id,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "process_output_diagnostics":
        process_id = value.get("process_id")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("process_output_diagnostics action requires a non-empty process_id.", raw)
        max_output_chars = value.get("max_output_chars", 20_000)
        if not isinstance(max_output_chars, int):
            raise ActionParseError("max_output_chars must be an integer.", raw)
        if max_output_chars < 0:
            raise ActionParseError("max_output_chars must be at least 0.", raw)
        if max_output_chars > 50_000:
            raise ActionParseError("max_output_chars must be at most 50000.", raw)
        context_lines = parse_nonnegative_int(value.get("context_lines", 2), "context_lines", raw, maximum=500)
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=100) or 20
        max_bytes_per_context = parse_optional_positive_int(
            value.get("max_bytes_per_context", 20_000),
            "max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1000:
            raise ActionParseError("max_bytes_per_context must be at least 1000.", raw)
        return ProcessOutputDiagnosticsAction(
            type="process_output_diagnostics",
            process_id=process_id,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "wait_process":
        process_id = value.get("process_id")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("wait_process action requires a non-empty process_id.", raw)
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms"), "timeout_ms", raw, maximum=600_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(
            value.get("max_output_chars"),
            "max_output_chars",
            raw,
            maximum=50_000,
        )
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        stdout_contains = value.get("stdout_contains")
        stderr_contains = value.get("stderr_contains")
        regex = value.get("regex", False)
        if stdout_contains is not None and (not isinstance(stdout_contains, str) or not stdout_contains.strip()):
            raise ActionParseError("wait_process action stdout_contains must be a non-empty string when provided.", raw)
        if stderr_contains is not None and (not isinstance(stderr_contains, str) or not stderr_contains.strip()):
            raise ActionParseError("wait_process action stderr_contains must be a non-empty string when provided.", raw)
        if not isinstance(regex, bool):
            raise ActionParseError("wait_process action regex must be a boolean when provided.", raw)
        return WaitProcessAction(
            type="wait_process",
            process_id=process_id,
            timeout_ms=timeout_ms,
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=max_output_chars,
        )

    if action_type == "check_write_process":
        process_id = value.get("process_id")
        content = value.get("content")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("check_write_process action requires a non-empty process_id.", raw)
        if not isinstance(content, str) or content == "":
            raise ActionParseError("check_write_process action requires non-empty content.", raw)
        return CheckWriteProcessAction(type="check_write_process", process_id=process_id, content=content)

    if action_type == "write_process":
        process_id = value.get("process_id")
        content = value.get("content")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("write_process action requires a non-empty process_id.", raw)
        if not isinstance(content, str) or content == "":
            raise ActionParseError("write_process action requires non-empty content.", raw)
        return WriteProcessAction(type="write_process", process_id=process_id, content=content)

    if action_type == "list_processes":
        return ListProcessesAction(type="list_processes")

    if action_type == "check_stop_all_processes":
        return CheckStopAllProcessesAction(type="check_stop_all_processes")

    if action_type == "check_stop_process":
        process_id = value.get("process_id")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("check_stop_process action requires a non-empty process_id.", raw)
        return CheckStopProcessAction(type="check_stop_process", process_id=process_id)

    if action_type == "stop_all_processes":
        return StopAllProcessesAction(type="stop_all_processes")

    if action_type == "stop_process":
        process_id = value.get("process_id")
        if not isinstance(process_id, str) or not process_id.strip():
            raise ActionParseError("stop_process action requires a non-empty process_id.", raw)
        return StopProcessAction(type="stop_process", process_id=process_id)

    if action_type == "update_plan":
        explanation = value.get("explanation")
        if explanation is not None and not isinstance(explanation, str):
            raise ActionParseError("update_plan action explanation must be a string when provided.", raw)
        return UpdatePlanAction(
            type="update_plan",
            explanation=explanation,
            plan=parse_plan_items(value.get("plan"), raw),
        )

    if action_type == "finish":
        message = value.get("message")
        if not isinstance(message, str):
            raise ActionParseError("finish action requires a string message.", raw)
        return FinishAction(type="finish", message=message)

    raise ActionParseError("Unsupported action type.", raw)


def parse_tool_action(name: str, tool_input: Any) -> AgentAction:
    if not isinstance(tool_input, dict):
        raise ActionParseError(f"{name} tool input must be an object.", json.dumps(tool_input))
    return parse_action({"type": name, **tool_input}, json.dumps({"name": name, "input": tool_input}))


def parse_plan_items(value: Any, raw: str) -> list[PlanItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("update_plan action requires a non-empty plan list.", raw)
    if len(value) > 20:
        raise ActionParseError("update_plan action plan must contain at most 20 items.", raw)

    items: list[PlanItem] = []
    in_progress_count = 0
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"update_plan item {index} must be an object.", raw)
        step = item.get("step")
        status = item.get("status")
        if not isinstance(step, str) or not step.strip():
            raise ActionParseError(f"update_plan item {index} requires a non-empty step.", raw)
        if status not in {"pending", "in_progress", "completed"}:
            raise ActionParseError(f"update_plan item {index} has an invalid status.", raw)
        if status == "in_progress":
            in_progress_count += 1
        items.append(PlanItem(step=step.strip(), status=status))

    if in_progress_count > 1:
        raise ActionParseError("update_plan action allows at most one in_progress item.", raw)
    return items


def parse_read_file_paths(value: Any, raw: str) -> list[str]:
    return parse_path_list(value, raw, "read_files", maximum=20)


def parse_read_file_contexts(value: Any, raw: str) -> list[ReadFileContextItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("read_file_contexts action requires a non-empty contexts list.", raw)
    if len(value) > 20:
        raise ActionParseError("read_file_contexts action contexts must contain at most 20 items.", raw)

    contexts: list[ReadFileContextItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"read_file_contexts context {index} must be an object.", raw)
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"read_file_contexts context {index} requires a non-empty path.", raw)
        line = parse_optional_positive_int(item.get("line"), f"read_file_contexts context {index} line", raw, maximum=None)
        if line is None:
            raise ActionParseError(f"read_file_contexts context {index} requires line.", raw)
        context_lines = parse_nonnegative_int(
            item.get("context_lines", 20),
            f"read_file_contexts context {index} context_lines",
            raw,
            maximum=500,
        )
        contexts.append(ReadFileContextItem(path=path.strip(), line=line, context_lines=context_lines))
    return contexts


def parse_read_file_ranges(value: Any, raw: str) -> list[ReadFileRangeItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("read_file_ranges action requires a non-empty ranges list.", raw)
    if len(value) > 20:
        raise ActionParseError("read_file_ranges action ranges must contain at most 20 items.", raw)

    ranges: list[ReadFileRangeItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"read_file_ranges range {index} must be an object.", raw)
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"read_file_ranges range {index} requires a non-empty path.", raw)
        start_line = parse_optional_positive_int(item.get("start_line"), f"read_file_ranges range {index} start_line", raw, maximum=None)
        if start_line is None:
            raise ActionParseError(f"read_file_ranges range {index} requires start_line.", raw)
        line_count = parse_optional_positive_int(item.get("line_count", 120), f"read_file_ranges range {index} line_count", raw, maximum=1000) or 120
        ranges.append(ReadFileRangeItem(path=path.strip(), start_line=start_line, line_count=line_count))
    return ranges


def parse_path_list(value: Any, raw: str, action_name: str, maximum: int) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_name} action requires a non-empty paths list.", raw)
    if len(value) > maximum:
        raise ActionParseError(f"{action_name} action paths must contain at most {maximum} items.", raw)
    paths: list[str] = []
    for index, path in enumerate(value, start=1):
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"{action_name} path {index} must be a non-empty string.", raw)
        paths.append(path.strip())
    return paths


def parse_json_set_input(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str, Any, bool]:
    path, pointer = parse_json_pointer_action_input(value, raw, action_type)
    create_missing = value.get("create_missing", False)
    if "value" not in value:
        raise ActionParseError(f"{action_type} action requires value.", raw)
    if not isinstance(create_missing, bool):
        raise ActionParseError(f"{action_type} action create_missing must be a boolean.", raw)
    return path, pointer, value["value"], create_missing


def parse_json_pointer_action_input(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, str]:
    path = value.get("path")
    pointer = value.get("pointer")
    if not isinstance(path, str) or not path.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty string path.", raw)
    if not isinstance(pointer, str) or not pointer.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty string pointer.", raw)
    return path.strip(), pointer.strip()


def parse_json_patch_input(value: dict[str, Any], raw: str, action_type: str) -> tuple[str, list[JsonPatchOperation]]:
    path = value.get("path")
    operations = value.get("operations")
    if not isinstance(path, str) or not path.strip():
        raise ActionParseError(f"{action_type} action requires a non-empty string path.", raw)
    if not isinstance(operations, list) or not operations:
        raise ActionParseError(f"{action_type} action requires a non-empty operations list.", raw)
    if len(operations) > 50:
        raise ActionParseError(f"{action_type} action operations must contain at most 50 items.", raw)

    parsed: list[JsonPatchOperation] = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            raise ActionParseError(f"{action_type} operation {index} must be an object.", raw)
        op = operation.get("op")
        pointer = operation.get("path")
        if op not in {"add", "replace", "remove"}:
            raise ActionParseError(f"{action_type} operation {index} has an unsupported op.", raw)
        if not isinstance(pointer, str) or not pointer.strip():
            raise ActionParseError(f"{action_type} operation {index} requires a non-empty path.", raw)
        if op in {"add", "replace"} and "value" not in operation:
            raise ActionParseError(f"{action_type} operation {index} requires value.", raw)
        parsed.append(JsonPatchOperation(op=op, path=pointer.strip(), value=operation.get("value")))
    return path.strip(), parsed


def parse_run_command_items(value: Any, raw: str, action_type: str) -> list[RunCommandItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty commands list.", raw)
    if len(value) > 10:
        raise ActionParseError(f"{action_type} action commands must contain at most 10 items.", raw)

    commands: list[RunCommandItem] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} command {index} must be an object.", raw)
        command = item.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError(f"{action_type} command {index} requires a non-empty command.", raw)
        cwd = item.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError(f"{action_type} command {index} cwd must be a string when provided.", raw)
        timeout_ms = parse_optional_positive_int(item.get("timeout_ms"), f"{action_type} command {index} timeout_ms", raw, maximum=600_000)
        if timeout_ms is not None and timeout_ms < 100:
            raise ActionParseError(f"{action_type} command {index} timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(
            item.get("max_output_chars"),
            f"{action_type} command {index} max_output_chars",
            raw,
            maximum=50_000,
        )
        if max_output_chars is not None and max_output_chars < 1_000:
            raise ActionParseError(f"{action_type} command {index} max_output_chars must be at least 1000.", raw)
        extract_output_contexts = item.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError(f"{action_type} command {index} extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = item.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError(f"{action_type} command {index} extract_output_diagnostics must be a boolean.", raw)
        context_lines = parse_nonnegative_int(
            item.get("context_lines", 5),
            f"{action_type} command {index} context_lines",
            raw,
            maximum=500,
        )
        max_diagnostics = parse_optional_positive_int(
            item.get("max_diagnostics", 50),
            f"{action_type} command {index} max_diagnostics",
            raw,
            maximum=200,
        ) or 50
        max_contexts = parse_optional_positive_int(
            item.get("max_contexts", 20),
            f"{action_type} command {index} max_contexts",
            raw,
            maximum=100,
        ) or 20
        max_bytes_per_context = parse_optional_positive_int(
            item.get("max_bytes_per_context", 20_000),
            f"{action_type} command {index} max_bytes_per_context",
            raw,
            maximum=200_000,
        ) or 20_000
        if max_bytes_per_context < 1_000:
            raise ActionParseError(f"{action_type} command {index} max_bytes_per_context must be at least 1000.", raw)
        commands.append(
            RunCommandItem(
                command=command.strip(),
                timeout_ms=timeout_ms,
                cwd=cwd,
                max_output_chars=max_output_chars,
                extract_output_contexts=extract_output_contexts,
                extract_output_diagnostics=extract_output_diagnostics,
                context_lines=context_lines,
                max_diagnostics=max_diagnostics,
                max_contexts=max_contexts,
                max_bytes_per_context=max_bytes_per_context,
            )
        )
    return commands


def parse_move_file_transfers(value: Any, raw: str, action_type: str) -> list[MoveFileTransfer]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty transfers list.", raw)
    if len(value) > 100:
        raise ActionParseError(f"{action_type} action transfers must contain at most 100 items.", raw)

    transfers: list[MoveFileTransfer] = []
    seen_sources: set[str] = set()
    seen_destinations: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} transfer {index} must be an object.", raw)
        source = item.get("source")
        destination = item.get("destination")
        if not isinstance(source, str) or not source.strip():
            raise ActionParseError(f"{action_type} transfer {index} requires a non-empty source.", raw)
        if not isinstance(destination, str) or not destination.strip():
            raise ActionParseError(f"{action_type} transfer {index} requires a non-empty destination.", raw)
        normalized_source = source.strip()
        normalized_destination = destination.strip()
        if normalized_source in seen_sources:
            raise ActionParseError(f"{action_type} transfer {index} duplicates source {normalized_source}.", raw)
        if normalized_destination in seen_destinations:
            raise ActionParseError(f"{action_type} transfer {index} duplicates destination {normalized_destination}.", raw)
        seen_sources.add(normalized_source)
        seen_destinations.add(normalized_destination)
        transfers.append(MoveFileTransfer(source=normalized_source, destination=normalized_destination))
    return transfers


def parse_directory_transfers(value: Any, raw: str, action_type: str) -> list[DirectoryTransfer]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty transfers list.", raw)
    if len(value) > 100:
        raise ActionParseError(f"{action_type} action transfers must contain at most 100 items.", raw)

    transfers: list[DirectoryTransfer] = []
    seen_sources: set[str] = set()
    seen_destinations: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} transfer {index} must be an object.", raw)
        source = item.get("source")
        destination = item.get("destination")
        if not isinstance(source, str) or not source.strip():
            raise ActionParseError(f"{action_type} transfer {index} requires a non-empty source.", raw)
        if not isinstance(destination, str) or not destination.strip():
            raise ActionParseError(f"{action_type} transfer {index} requires a non-empty destination.", raw)
        normalized_source = source.strip()
        normalized_destination = destination.strip()
        if normalized_source in seen_sources:
            raise ActionParseError(f"{action_type} transfer {index} duplicates source {normalized_source}.", raw)
        if normalized_destination in seen_destinations:
            raise ActionParseError(f"{action_type} transfer {index} duplicates destination {normalized_destination}.", raw)
        seen_sources.add(normalized_source)
        seen_destinations.add(normalized_destination)
        transfers.append(DirectoryTransfer(source=normalized_source, destination=normalized_destination))
    return transfers


def directory_transfer_pairs(transfers: list[DirectoryTransfer]) -> list[tuple[str, str]]:
    return [(transfer.source, transfer.destination) for transfer in transfers]


def parse_write_file_items(value: Any, raw: str, action_type: str = "write_files") -> list[WriteFileItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty files list.", raw)
    if len(value) > 20:
        raise ActionParseError(f"{action_type} action files must contain at most 20 items.", raw)

    files: list[WriteFileItem] = []
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"{action_type} file {index} must be an object.", raw)
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"{action_type} file {index} requires a non-empty path.", raw)
        if not isinstance(content, str):
            raise ActionParseError(f"{action_type} file {index} requires string content.", raw)
        normalized_path = path.strip()
        if normalized_path in seen:
            raise ActionParseError(f"{action_type} file {index} duplicates path {normalized_path}.", raw)
        seen.add(normalized_path)
        files.append(WriteFileItem(path=normalized_path, content=content))
    return files


def format_file_mode(mode: int) -> str:
    return f"{mode:04o}" if mode else ""


def parse_edit_operations(value: Any, raw: str, action_type: str = "multi_edit_file") -> list[EditOperation]:
    if not isinstance(value, list) or not value:
        raise ActionParseError(f"{action_type} action requires a non-empty edits list.", raw)
    if len(value) > 20:
        raise ActionParseError(f"{action_type} action edits must contain at most 20 items.", raw)

    edits: list[EditOperation] = []
    for index, edit in enumerate(value, start=1):
        if not isinstance(edit, dict):
            raise ActionParseError(f"{action_type} edit {index} must be an object.", raw)
        old = edit.get("old")
        new = edit.get("new")
        if not isinstance(old, str) or old == "":
            raise ActionParseError(f"{action_type} edit {index} requires non-empty string old.", raw)
        if not isinstance(new, str):
            raise ActionParseError(f"{action_type} edit {index} requires string new.", raw)
        edits.append(EditOperation(old=old, new=new))
    return edits


def parse_optional_positive_int(value: Any, name: str, raw: str, maximum: int | None) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 1:
        raise ActionParseError(f"{name} must be a positive integer.", raw)
    if maximum is not None and value > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return value


def parse_optional_nonnegative_int(value: Any, name: str, raw: str, maximum: int | None) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ActionParseError(f"{name} must be a non-negative integer.", raw)
    if maximum is not None and value > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return value


def parse_nonnegative_int(value: Any, name: str, raw: str, maximum: int | None) -> int:
    if type(value) is not int or value < 0:
        raise ActionParseError(f"{name} must be a non-negative integer.", raw)
    if maximum is not None and value > maximum:
        raise ActionParseError(f"{name} must be at most {maximum}.", raw)
    return value


def summarize_plan_update(action: UpdatePlanAction) -> str:
    current = next((item.step for item in action.plan if item.status == "in_progress"), None)
    if current:
        return f"Plan updated. Current: {current}"
    if action.explanation and action.explanation.strip():
        return f"Plan updated. {action.explanation.strip()}"
    return "Plan updated."


def get_blocked_command_reason(command: str) -> str | None:
    compact = " ".join(command.strip().split())
    lowered = compact.lower()
    blocked_prefixes = (
        "sudo ",
        "su ",
        "git clean -fd",
        "mkfs",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
    )
    if lowered.startswith(blocked_prefixes):
        return "high-risk command requires an explicit user-controlled approval flow"
    if command_contains_dangerous_rm(lowered):
        return "recursive forced deletion of broad paths is not allowed in project mode"
    if command_writes_to_device(lowered):
        return "raw device writes are not allowed in project mode"
    if command_pipes_network_script_to_shell(lowered):
        return "network script piping is not allowed in project mode"
    if command_launches_gui_application(lowered):
        return "GUI application launch commands are not allowed in project mode"
    if re.search(r"(^|[;&|]\s*)powershell\b.*\b(iwr|irm|invoke-webrequest|invoke-restmethod)\b.*\|\s*(iex|invoke-expression)\b", lowered):
        return "network script execution is not allowed in project mode"
    if ":(){:|:&};:" in lowered.replace(" ", ""):
        return "fork bomb pattern is not allowed in project mode"
    return None


def command_contains_dangerous_rm(lowered_command: str) -> bool:
    rm_pattern = re.compile(r"(^|[;&|]\s*)rm\s+(?P<flags>(?:-[a-z]*[rf][a-z]*\s+)+)(?:--\s+)?(?P<targets>[^;&|]+)")
    dangerous_targets = {
        "/",
        "/*",
        ".",
        "./",
        "*",
        "~",
        "~/",
        "$home",
        "${home}",
        "/home",
        "/home/",
        "/tmp",
        "/tmp/",
        "/var",
        "/var/",
        "/usr",
        "/usr/",
    }
    for match in rm_pattern.finditer(lowered_command):
        flags = match.group("flags")
        if "r" not in flags or "f" not in flags:
            continue
        targets = [target.strip().strip("'\"") for target in match.group("targets").split()]
        for target in targets:
            normalized = target.rstrip("/") if target not in {"/", "./", "~/"} else target
            if target in dangerous_targets or normalized in dangerous_targets:
                return True
    return False


def command_writes_to_device(lowered_command: str) -> bool:
    if not re.search(r"(^|[;&|]\s*)dd\b", lowered_command):
        return False
    return bool(re.search(r"\bof=/dev/|>\s*/dev/", lowered_command))


def command_pipes_network_script_to_shell(lowered_command: str) -> bool:
    network_fetch = r"\b(curl|wget)\b"
    shell_sink = r"\|\s*(?:sh|bash|zsh|fish|dash|ksh|python|python3|ruby|perl|node)\b"
    return bool(re.search(network_fetch, lowered_command) and re.search(shell_sink, lowered_command))


def command_launches_gui_application(lowered_command: str) -> bool:
    segment = r"(^|[;&|]\s*)"
    wrappers = r"(?:nohup\s+|setsid\s+|env\s+(?:[a-z_][a-z0-9_]*=\S+\s+)*)?"
    launcher = (
        r"(?:explorer(?:\.exe)?|xdg-open|wslview|wsl-open|gio\s+open|"
        r"gnome-open|kde-open(?:5)?|open|nautilus|dolphin|thunar|nemo|pcmanfm|caja|konqueror|"
        r"code|code-insiders|cursor|windsurf|subl|mate|gedit|mousepad|kate|"
        r"firefox|google-chrome|google-chrome-stable|chromium|chromium-browser|microsoft-edge)\b"
    )
    windows_start = r"(?:cmd(?:\.exe)?\s+/c\s+start\b|powershell(?:\.exe)?\b.*\bstart-process\b)"
    return bool(
        re.search(segment + wrappers + launcher, lowered_command)
        or re.search(segment + wrappers + windows_start, lowered_command)
    )


def _close_background_handles(background: BackgroundProcess) -> None:
    handles = [background.stdout_handle, background.stderr_handle, background.process.stdin]
    for handle in handles:
        if handle is not None and not handle.closed:
            handle.close()


def _terminate_process(process: subprocess.Popen[str]) -> None:
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return


def _signal_name(returncode: int) -> str | None:
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return None
