from __future__ import annotations

from typing import Any


DELEGATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "deep_review",
        "description": "Run parallel read-only review agents over current changes for correctness, security, and test risks, then independently verify, deduplicate, and rank their findings. Reviewers inspect surrounding code, obey root REVIEW.md guidance, and return evidence with file and line references.",
        "input_schema": {
            "type": "object",
            "properties": {
                "perspectives": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["correctness", "security", "tests"]},
                    "minItems": 1,
                    "maxItems": 3,
                    "uniqueItems": True,
                },
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 8},
                "base_ref": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Optional git base ref to compare with the working tree or HEAD.",
                },
                "target": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1000,
                    "description": "Optional local review target such as a file path, branch, ref range, or short scope note. Mutually exclusive with base_ref.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "delegate_task",
        "description": "Delegate one bounded task to a subagent. Use explore for research, code for implementation, and isolation=worktree for parallel-safe edits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "minLength": 1, "maxLength": 4000},
                "context": {
                    "type": "string",
                    "maxLength": 4000,
                },
                "max_iterations": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                },
                "mode": {
                    "type": "string",
                    "enum": ["explore", "code"],
                },
                "agent": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                },
                "run_in_background": {"type": "boolean"},
                "isolation": {"type": "string", "enum": ["worktree"]},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Task",
        "description": "Claude-compatible alias for delegating one bounded task, optionally in an isolated git worktree.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 4000},
                "description": {"type": "string", "maxLength": 4000},
                "subagent_type": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                },
                "mode": {"type": "string", "enum": ["explore", "code"]},
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 8},
                "run_in_background": {"type": "boolean"},
                "isolation": {"type": "string", "enum": ["worktree"]},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Agent",
        "description": "Delegate a bounded task or, when experimental agent teams are enabled, spawn a named in-process teammate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 4000},
                "description": {"type": "string", "maxLength": 4000},
                "subagent_type": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                },
                "mode": {"type": "string", "enum": ["explore", "code"]},
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 8},
                "run_in_background": {"type": "boolean"},
                "isolation": {"type": "string", "enum": ["worktree"]},
                "name": {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
                    "description": "Optional teammate name. Spawns an approved background teammate when provided.",
                },
                "team_name": {
                    "type": "string",
                    "maxLength": 64,
                    "description": "Accepted for Claude compatibility and ignored; teams are session-scoped.",
                },
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ListAgents",
        "description": "List running/resumable subagents and other reachable VibeAgent sessions on this machine. This lists live agent instances, not project profile definitions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_agents": {"type": "integer", "minimum": 1, "maximum": 500},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "SendMessage",
        "description": "Steer or resume a subagent, or send plain-text coordination to a reachable peer session by exact ID or unambiguous name. Messages never grant approval or change configuration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"},
                "message": {"type": "string", "minLength": 1, "maxLength": 4000},
            },
            "required": ["to", "message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TaskOutput",
        "description": "Read the current or final result of a background subagent task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"},
                "block": {"type": "boolean"},
                "timeout_ms": {"type": "integer", "minimum": 0, "maximum": 600000},
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "TaskStop",
        "description": "Request cancellation of a running background subagent task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"},
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
    },
]
