from __future__ import annotations

from typing import Any

from .tool_categories import valid_tool_categories


PROJECT_RUNTIME_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
        "name": "tool_search",
        "description": "Search the model tool catalog by tool name, category, description, required inputs, or input property names without executing project actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms such as a rough capability, tool name fragment, input property, or category.",
                },
                "max_matches": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum matching tools to return. Defaults to 20.",
                },
                "category": {
                    "type": "string",
                    "enum": list(valid_tool_categories()),
                    "description": "Optional category filter.",
                },
                "approval_required": {
                    "type": "boolean",
                    "description": "Optional approval filter. True returns approval-gated tools; false returns read-only tools.",
                },
            },
            "required": ["query"],
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
]
