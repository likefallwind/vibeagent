from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .types import (
    AgentAction,
    AppendFileAction,
    AppendFileObservation,
    CheckAppendFileAction,
    CheckAppendFileObservation,
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
    CodeReferencesAction,
    CodeReferencesObservation,
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
    GitCommitAction,
    GitCommitObservation,
    GitDiffAction,
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
    PatchFileAction,
    PatchFileObservation,
    PatchFilesAction,
    PatchFilesObservation,
    PlanItem,
    PortCheckAction,
    PortCheckObservation,
    ProcessInfo,
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
    PythonReferencesObservation,
    PythonRenameAction,
    PythonRenameObservation,
    PythonRenamePreviewAction,
    PythonRenamePreviewFile,
    PythonRenamePreviewObservation,
    PythonRenameReplacement,
    ProjectCommand,
    ProjectCommandsAction,
    ProjectCommandsObservation,
    ProjectOverviewAction,
    ProjectOverviewObservation,
    ProjectManifest,
    ProjectManifestItem,
    ProjectManifestsAction,
    ProjectManifestsObservation,
    ReadFileAction,
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
    RunCommandAction,
    RunCommandObservation,
    RunCommandItem,
    RunCommandsAction,
    RunCommandsObservation,
    RuntimeToolInfo,
    SearchAction,
    SearchObservation,
    SessionSummaryAction,
    SessionSummaryObservation,
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
from .session import format_session_summary, format_sessions, summarize_session
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
    apply_python_rename,
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
    set_project_file_executable,
    preview_set_project_file_executable,
    insert_project_file_lines,
    read_project_file,
    read_project_file_result,
    regex_replace_project_file,
    read_project_commands,
    read_project_manifests,
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
    stdout_handle: Any
    stderr_handle: Any


BACKGROUND_PROCESSES: dict[str, BackgroundProcess] = {}


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
                }
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
                        "properties": {
                            "op": {"type": "string", "enum": ["add", "replace", "remove"]},
                            "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                            "value": {
                                "description": "JSON value for add or replace operations.",
                                "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                            },
                        },
                        "required": ["op", "path"],
                        "additionalProperties": False,
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
                        "properties": {
                            "op": {"type": "string", "enum": ["add", "replace", "remove"]},
                            "path": {"type": "string", "description": "JSON Pointer path for this operation."},
                            "value": {
                                "description": "JSON value for add or replace operations.",
                                "type": ["string", "number", "integer", "boolean", "object", "array", "null"],
                            },
                        },
                        "required": ["op", "path"],
                        "additionalProperties": False,
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
        "description": "List background commands started by start_command in the current runtime.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "check_stop_all_processes",
        "description": "Preview all background commands in the current runtime that stop_all_processes would stop.",
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
        "description": "Stop all background commands started by start_command in the current runtime.",
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
                content = read_project_file(
                    workspace,
                    item.path,
                    start_line=item.start_line,
                    line_count=item.line_count,
                )
                ranges.append(
                    ReadFileRangeResult(
                        path=item.path,
                        start_line=item.start_line,
                        line_count=item.line_count,
                        ok=True,
                        content=content,
                        message=f"Read {item.path}:{item.start_line}+{item.line_count}.",
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
        all_suggested_checks = [SuggestedCheck(**item) for item in review["suggested_checks"]]
        suggested_checks = all_suggested_checks[: action.max_checks]
        suggested_checks_total = int(review["suggested_checks_total"])
        suggested_checks_truncated = (
            bool(review["suggested_checks_truncated"])
            or len(all_suggested_checks) > len(suggested_checks)
            or suggested_checks_total > len(suggested_checks)
        )
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
            files=files,
            total_files=total_files,
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
        return read_background_process(action.process_id, max_output_chars=action.max_output_chars or 4_000)

    if isinstance(action, WaitProcessAction):
        return wait_background_process(
            action.process_id,
            timeout_ms=action.timeout_ms or 5_000,
            stdout_contains=action.stdout_contains,
            stderr_contains=action.stderr_contains,
            regex=action.regex,
            max_output_chars=action.max_output_chars or 4_000,
        )

    if isinstance(action, CheckWriteProcessAction):
        return check_write_background_process(action.process_id, action.content)

    if isinstance(action, WriteProcessAction):
        return write_background_process(action.process_id, action.content)

    if isinstance(action, ListProcessesAction):
        return list_background_processes()

    if isinstance(action, CheckStopAllProcessesAction):
        return check_stop_all_background_processes()

    if isinstance(action, CheckStopProcessAction):
        return check_stop_background_process(action.process_id)

    if isinstance(action, StopAllProcessesAction):
        return stop_all_background_processes()

    if isinstance(action, StopProcessAction):
        return stop_background_process(action.process_id)

    if isinstance(action, UpdatePlanAction):
        return UpdatePlanObservation(
            kind="update_plan",
            plan=action.plan,
            message=summarize_plan_update(action),
        )

    return FinishObservation(kind="finish", message=action.message)


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
    return run_command(
        command_cwd,
        action.command,
        timeout_ms,
        workspace.root,
        max_output_chars=max_output_chars,
    )


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
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            command,
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
        stdout_handle=stdout_handle,
        stderr_handle=stderr_handle,
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


def read_background_process(process_id: str, max_output_chars: int = 4_000) -> ReadProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
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


def wait_background_process(
    process_id: str,
    timeout_ms: int = 5_000,
    stdout_contains: str | None = None,
    stderr_contains: str | None = None,
    regex: bool = False,
    max_output_chars: int = 4_000,
) -> WaitProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
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


def check_write_background_process(process_id: str, content: str) -> CheckWriteProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
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


def write_background_process(process_id: str, content: str) -> WriteProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
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


def list_background_processes() -> ListProcessesObservation:
    processes: list[ProcessInfo] = []
    for process_id, background in sorted(BACKGROUND_PROCESSES.items()):
        exit_code = background.process.poll()
        running = exit_code is None
        if not running:
            _close_background_handles(background)
        processes.append(
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

    return ListProcessesObservation(
        kind="list_processes",
        processes=processes,
        message=f"Found {len(processes)} background process(es).",
    )


def check_stop_all_background_processes() -> CheckStopAllProcessesObservation:
    listed = list_background_processes()
    running_count = sum(1 for process in listed.processes if process.running)
    return CheckStopAllProcessesObservation(
        kind="check_stop_all_processes",
        ok=True,
        processes=listed.processes,
        running_count=running_count,
        message=f"stop_all_processes would stop {len(listed.processes)} background process(es), {running_count} still running.",
    )


def check_stop_background_process(process_id: str) -> CheckStopProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
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


def stop_all_background_processes() -> StopAllProcessesObservation:
    stopped: list[StoppedProcessInfo] = []
    for process_id, background in sorted(list(BACKGROUND_PROCESSES.items())):
        if background.process.poll() is None:
            _terminate_process(background.process)
        exit_code = background.process.poll()
        _close_background_handles(background)
        BACKGROUND_PROCESSES.pop(process_id, None)
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

    return StopAllProcessesObservation(
        kind="stop_all_processes",
        ok=True,
        stopped=stopped,
        message=f"Stopped {len(stopped)} background process(es).",
    )


def stop_background_process(process_id: str) -> StopProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
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
        return ReadFileRangesAction(
            type="read_file_ranges",
            ranges=parse_read_file_ranges(value.get("ranges"), raw),
        )

    if action_type == "file_info":
        return FileInfoAction(type="file_info", paths=parse_path_list(value.get("paths"), raw, "file_info", maximum=50))

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

    if action_type == "glob":
        pattern = value.get("pattern")
        max_matches = value.get("max_matches", 200)
        if not isinstance(pattern, str) or not pattern.strip():
            raise ActionParseError("glob action requires a non-empty pattern.", raw)
        max_matches = parse_optional_positive_int(max_matches, "max_matches", raw, maximum=500) or 200
        return GlobAction(type="glob", pattern=pattern, max_matches=max_matches)

    if action_type == "git_status":
        return GitStatusAction(type="git_status")

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

    if action_type == "project_commands":
        max_commands = parse_optional_positive_int(value.get("max_commands", 100), "max_commands", raw, maximum=500) or 100
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        return ProjectCommandsAction(type="project_commands", max_commands=max_commands, max_files=max_files)

    if action_type == "project_manifests":
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        max_items = parse_optional_positive_int(value.get("max_items", 500), "max_items", raw, maximum=2000) or 500
        return ProjectManifestsAction(type="project_manifests", max_files=max_files, max_items=max_items)

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
        return RunCommandAction(
            type="run_command",
            command=command,
            timeout_ms=timeout_ms,
            cwd=cwd,
            max_output_chars=max_output_chars,
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
        commands.append(
            RunCommandItem(
                command=command.strip(),
                timeout_ms=timeout_ms,
                cwd=cwd,
                max_output_chars=max_output_chars,
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
