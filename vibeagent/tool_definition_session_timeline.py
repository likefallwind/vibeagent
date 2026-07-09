from __future__ import annotations

from typing import Any


SESSION_TIMELINE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
]
