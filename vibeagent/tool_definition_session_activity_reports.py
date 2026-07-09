from __future__ import annotations

from typing import Any


SESSION_ACTIVITY_REPORT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
