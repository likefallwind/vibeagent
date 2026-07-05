from __future__ import annotations

from typing import Any


SESSION_REPORT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
]
