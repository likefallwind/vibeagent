from __future__ import annotations

from typing import Any


READING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
                "show_line_numbers": {
                    "type": "boolean",
                    "description": "Prefix returned full-file lines with 1-based line numbers. Line-range reads already include line numbers. Defaults to false.",
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
                "show_line_numbers": {
                    "type": "boolean",
                    "description": "Prefix returned file lines with 1-based line numbers. Defaults to false.",
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
]
