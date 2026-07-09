from __future__ import annotations

from typing import Any


SESSION_READINESS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
