from __future__ import annotations

import json
import os
import signal
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .types import (
    AgentAction,
    CheckPatchAction,
    CheckPatchObservation,
    CheckPatchesAction,
    CheckPatchesObservation,
    CommandResult,
    DeleteFileAction,
    DeleteFileObservation,
    EditFileAction,
    EditFileObservation,
    EditOperation,
    FinishAction,
    FinishObservation,
    FileInfoAction,
    FileInfoObservation,
    FileInfoResult,
    GlobAction,
    GlobObservation,
    GitBlameAction,
    GitBlameObservation,
    GitChangeFile,
    GitChangesAction,
    GitChangesObservation,
    GitDiffAction,
    GitDiffObservation,
    GitLogAction,
    GitLogObservation,
    GitShowAction,
    GitShowObservation,
    GitStatusAction,
    GitStatusObservation,
    InsertLinesAction,
    InsertLinesObservation,
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
    ReplaceLinesAction,
    ReplaceLinesObservation,
    ReviewChangesAction,
    ReviewChangesObservation,
    RepoMapAction,
    RepoMapObservation,
    RepoMapPythonFile,
    RunCommandAction,
    RunCommandObservation,
    SearchAction,
    SearchObservation,
    SessionSummaryAction,
    SessionSummaryObservation,
    StartCommandAction,
    StartCommandObservation,
    StopProcessAction,
    StopProcessObservation,
    SuggestedCheck,
    SuggestChecksAction,
    SuggestChecksObservation,
    UpdatePlanAction,
    UpdatePlanObservation,
    WriteFileAction,
    WriteFileItem,
    WriteFileObservation,
    WriteFileResult,
    WriteFilesAction,
    WriteFilesObservation,
    MoveFileAction,
    MoveFileObservation,
)
from .session import format_session_summary, format_sessions, summarize_session
from .workspace import (
    RunWorkspace,
    build_repo_map,
    check_project_patch,
    check_project_patches,
    delete_project_file,
    edit_project_file,
    list_project_files,
    list_project_tree,
    move_project_file,
    multi_edit_project_file,
    patch_project_file,
    patch_project_files,
    read_git_changes,
    read_git_diff,
    find_python_references,
    find_python_definitions,
    find_python_calls,
    inspect_python_call_graph,
    read_git_blame,
    read_git_log,
    read_git_show,
    read_git_status,
    read_project_file_info,
    insert_project_file_lines,
    read_project_file,
    read_python_symbol_outline,
    replace_project_file_lines,
    review_project_changes,
    replace_python_definition,
    resolve_command_cwd,
    glob_project_files,
    inspect_python_dependencies,
    search_project,
    check_python_syntax,
    suggest_project_checks,
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
        "description": "Build a bounded project overview with directory tree, file list, and Python import/symbol outlines.",
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
                }
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
        "name": "git_changes",
        "description": "Read a structured summary of changed git files, including status and staged/unstaged insertion/deletion counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
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
        "name": "suggest_checks",
        "description": "Suggest relevant test, build, lint, and syntax-check commands from project metadata and current changed files without running them.",
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
        "description": "Validate a multi-file unified diff against existing project files without writing changes. Returns the combined diff that would be applied.",
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
        "description": "Apply a multi-file unified diff to existing project files atomically.",
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
            "properties": {"process_id": {"type": "string"}},
            "required": ["process_id"],
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
            return RepoMapObservation(
                kind="repo_map",
                path=str(repo_map["path"]),
                tree=list(repo_map["tree"]),
                files=list(repo_map["files"]),
                python_files=python_files,
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
                total_tree_entries=0,
                total_files=0,
                truncated=False,
                ok=False,
                message=str(error),
            )

    if isinstance(action, ReadFileAction):
        try:
            content = read_project_file(
                workspace,
                action.path,
                start_line=action.start_line,
                line_count=action.line_count,
            )
            if action.start_line is None:
                message = f"Read {action.path}."
            else:
                message = f"Read {action.path} from line {action.start_line}."
        except ValueError as error:
            content = ""
            message = str(error)
        return ReadFileObservation(
            kind="read_file",
            path=action.path,
            content=content,
            message=message,
            start_line=action.start_line,
            line_count=action.line_count,
        )

    if isinstance(action, ReadFilesAction):
        files: list[ReadFileResult] = []
        for path in action.paths:
            try:
                content = read_project_file(workspace, path)
                files.append(ReadFileResult(path=path, ok=True, content=content, message=f"Read {path}."))
            except ValueError as error:
                files.append(ReadFileResult(path=path, ok=False, content="", message=str(error)))
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

    if isinstance(action, SearchAction):
        try:
            matches = search_project(
                workspace,
                action.query,
                max_matches=action.max_matches,
                relative_path=action.path,
                regex=action.regex,
                case_sensitive=action.case_sensitive,
                context_lines=action.context_lines,
            )
            message = f"Found {len(matches)} match(es)."
        except ValueError as error:
            matches = []
            message = str(error)
        return SearchObservation(
            kind="search",
            query=action.query,
            matches=matches,
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
                files=[],
                total_files=0,
                python=[],
                python_total=0,
                python_truncated=False,
                diff_check="",
                staged_diff_check="",
                status="",
                message=str(error),
            )
        files = [GitChangeFile(**item) for item in review["files"]]
        python = [PythonCheckResult(**item) for item in review["python"]]
        return ReviewChangesObservation(
            kind="review_changes",
            ok=bool(review["ok"]),
            changes_ok=bool(review["changes_ok"]),
            diff_check_ok=bool(review["diff_check_ok"]),
            staged_diff_check_ok=bool(review["staged_diff_check_ok"]),
            python_ok=bool(review["python_ok"]),
            files=files,
            total_files=int(review["total_files"]),
            python=python,
            python_total=int(review["python_total"]),
            python_truncated=bool(review["python_truncated"]),
            diff_check=str(review["diff_check"]),
            staged_diff_check=str(review["staged_diff_check"]),
            status=str(review["status"]),
            message=str(review["message"]),
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

    if isinstance(action, WriteFileAction):
        try:
            write_run_file(workspace, action.path, action.content)
            return WriteFileObservation(kind="write_file", path=action.path, ok=True, message=f"Wrote {action.path}")
        except ValueError as error:
            return WriteFileObservation(kind="write_file", path=action.path, ok=False, message=str(error))

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

    if isinstance(action, RunCommandAction):
        blocked = get_blocked_command_reason(action.command)
        if blocked:
            return RunCommandObservation(
                kind="run_command",
                result=CommandResult(
                    command=action.command,
                    exit_code=None,
                    stdout="",
                    stderr=f"Command blocked: {blocked}",
                    timed_out=False,
                    signal=None,
                    timeout_ms=action.timeout_ms or command_timeout_ms,
                    cwd=action.cwd or ".",
                    max_output_chars=action.max_output_chars or 12_000,
                ),
            )
        try:
            command_cwd = resolve_command_cwd(workspace, action.cwd)
        except ValueError as error:
            return RunCommandObservation(
                kind="run_command",
                result=CommandResult(
                    command=action.command,
                    exit_code=None,
                    stdout="",
                    stderr=str(error),
                    timed_out=False,
                    signal=None,
                    timeout_ms=action.timeout_ms or command_timeout_ms,
                    cwd=action.cwd or ".",
                    max_output_chars=action.max_output_chars or 12_000,
                ),
            )
        return RunCommandObservation(
            kind="run_command",
            result=run_command(
                command_cwd,
                action.command,
                action.timeout_ms or command_timeout_ms,
                workspace.root,
                max_output_chars=action.max_output_chars or 12_000,
            ),
        )

    if isinstance(action, StartCommandAction):
        return start_background_command(workspace, action.command, action.cwd)

    if isinstance(action, ReadProcessAction):
        return read_background_process(action.process_id)

    if isinstance(action, ListProcessesAction):
        return list_background_processes()

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


def start_background_command(workspace: RunWorkspace, command: str, cwd: str | None = None) -> StartCommandObservation:
    blocked = get_blocked_command_reason(command)
    if blocked:
        return StartCommandObservation(
            kind="start_command",
            process_id="",
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
            stdin=subprocess.DEVNULL,
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
        command=command,
        cwd=relative_cwd(command_cwd, workspace.root),
        ok=True,
        message=f"Started process {process_id}.",
        stdout_path=stdout_path.as_posix(),
        stderr_path=stderr_path.as_posix(),
    )


def read_background_process(process_id: str) -> ReadProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        return ReadProcessObservation(
            kind="read_process",
            process_id=process_id,
            ok=False,
            running=False,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            message="Unknown background process id.",
        )

    exit_code = background.process.poll()
    running = exit_code is None
    if not running:
        _close_background_handles(background)
    stdout = read_text_tail(background.stdout_path)
    stderr = read_text_tail(background.stderr_path)
    return ReadProcessObservation(
        kind="read_process",
        process_id=process_id,
        ok=True,
        running=running,
        exit_code=exit_code,
        signal=_signal_name(exit_code) if exit_code and exit_code < 0 else None,
        stdout=stdout,
        stderr=stderr,
        message=f"Process {process_id} is {'running' if running else 'exited'}.",
    )


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


def stop_background_process(process_id: str) -> StopProcessObservation:
    background = BACKGROUND_PROCESSES.get(process_id)
    if background is None:
        return StopProcessObservation(
            kind="stop_process",
            process_id=process_id,
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
        if line_count is not None and start_line is None:
            raise ActionParseError("read_file action line_count requires start_line.", raw)
        return ReadFileAction(type="read_file", path=path, start_line=start_line, line_count=line_count)

    if action_type == "read_files":
        return ReadFilesAction(type="read_files", paths=parse_read_file_paths(value.get("paths"), raw))

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

    if action_type == "python_check":
        path = value.get("path")
        max_files = value.get("max_files", 200)
        if path is not None and not isinstance(path, str):
            raise ActionParseError("python_check action path must be a string when provided.", raw)
        max_files = parse_optional_positive_int(max_files, "max_files", raw, maximum=500) or 200
        return PythonCheckAction(type="python_check", path=path, max_files=max_files)

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

    if action_type == "git_changes":
        return GitChangesAction(type="git_changes")

    if action_type == "review_changes":
        max_files = parse_optional_positive_int(value.get("max_files", 200), "max_files", raw, maximum=500) or 200
        return ReviewChangesAction(type="review_changes", max_files=max_files)

    if action_type == "suggest_checks":
        max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
        return SuggestChecksAction(type="suggest_checks", max_commands=max_commands)

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

    if action_type == "multi_edit_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("multi_edit_file action requires a string path.", raw)
        return MultiEditAction(type="multi_edit_file", path=path, edits=parse_edit_operations(value.get("edits"), raw))

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

    if action_type == "write_file":
        path = value.get("path")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("write_file action requires a string path.", raw)
        if not isinstance(content, str):
            raise ActionParseError("write_file action requires string content.", raw)
        return WriteFileAction(type="write_file", path=path, content=content)

    if action_type == "write_files":
        return WriteFilesAction(type="write_files", files=parse_write_file_items(value.get("files"), raw))

    if action_type == "delete_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("delete_file action requires a string path.", raw)
        return DeleteFileAction(type="delete_file", path=path)

    if action_type == "move_file":
        source = value.get("source")
        destination = value.get("destination")
        if not isinstance(source, str):
            raise ActionParseError("move_file action requires string source.", raw)
        if not isinstance(destination, str):
            raise ActionParseError("move_file action requires string destination.", raw)
        return MoveFileAction(type="move_file", source=source, destination=destination)

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
        return ReadProcessAction(type="read_process", process_id=process_id)

    if action_type == "list_processes":
        return ListProcessesAction(type="list_processes")

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


def parse_write_file_items(value: Any, raw: str) -> list[WriteFileItem]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("write_files action requires a non-empty files list.", raw)
    if len(value) > 20:
        raise ActionParseError("write_files action files must contain at most 20 items.", raw)

    files: list[WriteFileItem] = []
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ActionParseError(f"write_files file {index} must be an object.", raw)
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not path.strip():
            raise ActionParseError(f"write_files file {index} requires a non-empty path.", raw)
        if not isinstance(content, str):
            raise ActionParseError(f"write_files file {index} requires string content.", raw)
        normalized_path = path.strip()
        if normalized_path in seen:
            raise ActionParseError(f"write_files file {index} duplicates path {normalized_path}.", raw)
        seen.add(normalized_path)
        files.append(WriteFileItem(path=normalized_path, content=content))
    return files


def parse_edit_operations(value: Any, raw: str) -> list[EditOperation]:
    if not isinstance(value, list) or not value:
        raise ActionParseError("multi_edit_file action requires a non-empty edits list.", raw)
    if len(value) > 20:
        raise ActionParseError("multi_edit_file action edits must contain at most 20 items.", raw)

    edits: list[EditOperation] = []
    for index, edit in enumerate(value, start=1):
        if not isinstance(edit, dict):
            raise ActionParseError(f"multi_edit_file edit {index} must be an object.", raw)
        old = edit.get("old")
        new = edit.get("new")
        if not isinstance(old, str) or old == "":
            raise ActionParseError(f"multi_edit_file edit {index} requires non-empty string old.", raw)
        if not isinstance(new, str):
            raise ActionParseError(f"multi_edit_file edit {index} requires string new.", raw)
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
        "rm -rf /",
        "rm -fr /",
        "rm -rf .",
        "rm -fr .",
        "rm -rf *",
        "rm -fr *",
        "git clean -fd",
        "mkfs",
        "shutdown",
        "reboot",
    )
    if lowered.startswith(blocked_prefixes):
        return "high-risk command requires an explicit user-controlled approval flow"
    if " curl " in f" {lowered} " and " | sh" in lowered:
        return "network script piping is not allowed in project mode"
    if " wget " in f" {lowered} " and " | sh" in lowered:
        return "network script piping is not allowed in project mode"
    return None


def _close_background_handles(background: BackgroundProcess) -> None:
    for handle in (background.stdout_handle, background.stderr_handle):
        if not handle.closed:
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
