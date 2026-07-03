from __future__ import annotations

from typing import Any


PROCESS_CONTROL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
        "description": "Stop all background commands started by start_command for the current project after approval.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
{
        "name": "stop_process",
        "description": "Stop a background command started by start_command after approval.",
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
