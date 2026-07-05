from __future__ import annotations

from typing import Any


SESSION_VERIFICATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
        "name": "run_session_verification",
        "description": "Rerun failed and/or pending verification commands recorded in a local VibeAgent session after approval. Defaults to the current run and stops on the first failure.",
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
                    "maximum": 10,
                    "description": "Maximum failed and pending check rows to inspect per group. Defaults to 10.",
                },
                "include_failed": {
                    "type": "boolean",
                    "description": "Whether to rerun failed verification checks. Defaults to true.",
                },
                "include_pending": {
                    "type": "boolean",
                    "description": "Whether to run pending verification checks. Defaults to true.",
                },
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000,
                    "description": "Per-command timeout in milliseconds. Defaults to 30000.",
                },
                "max_output_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 50000,
                    "description": "Maximum stdout/stderr characters per command. Defaults to 12000.",
                },
                "stop_on_failure": {
                    "type": "boolean",
                    "description": "Stop after the first failed command. Defaults to true.",
                },
                "extract_output_contexts": {
                    "type": "boolean",
                    "description": "Extract file:line source contexts from rerun command output. Defaults to false.",
                },
                "extract_output_diagnostics": {
                    "type": "boolean",
                    "description": "Summarize errors, warnings, and failures from rerun command output. Failed commands auto-extract diagnostics even when false.",
                },
                "context_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 50,
                    "description": "Surrounding source lines for extracted output references. Defaults to 5.",
                },
                "max_diagnostics": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum diagnostic lines to extract. Defaults to 50.",
                },
                "max_contexts": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum source contexts to extract. Defaults to 20.",
                },
                "max_bytes_per_context": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200000,
                    "description": "Maximum bytes per extracted source context. Defaults to 20000.",
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
]
