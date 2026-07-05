from __future__ import annotations

from typing import Any


COMMAND_OUTPUT_EXTRACTION_PROPERTIES: dict[str, dict[str, object]] = {
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
}


COMMAND_RUNTIME_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
                            **COMMAND_OUTPUT_EXTRACTION_PROPERTIES,
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
                            **COMMAND_OUTPUT_EXTRACTION_PROPERTIES,
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
]
