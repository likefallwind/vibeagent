from __future__ import annotations

from typing import Any


CHECKPOINT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "checkpoint_create",
        "description": "Save the current git HEAD, short status, staged patch, and unstaged patch under .vibeagent/checkpoints for later inspection or tracked-file recovery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "description": "Optional short label describing why the checkpoint was created.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_list",
        "description": "List saved local checkpoints for the current project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum checkpoint rows to return. Defaults to 20.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_show",
        "description": "Inspect one saved checkpoint's metadata, saved short git status, and saved untracked file paths without restoring files. Use checkpoint_id='latest' for the newest checkpoint.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string", "description": "Checkpoint id to inspect, or 'latest' for the newest saved checkpoint."}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_diff",
        "description": "Read bounded staged and unstaged patch text saved in one checkpoint without restoring files. Use checkpoint_id='latest' for the newest checkpoint.",
        "input_schema": {
            "type": "object",
            "properties": {
                "checkpoint_id": {"type": "string", "description": "Checkpoint id to inspect, or 'latest' for the newest saved checkpoint."},
                "max_chars": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 200000,
                    "description": "Maximum characters to return for each saved patch. Defaults to 40000.",
                },
            },
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_status",
        "description": "Compare current git status, staged patch, unstaged patch, and saved untracked file contents with one saved checkpoint. Use checkpoint_id='latest' for the newest checkpoint.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string", "description": "Checkpoint id to compare, or 'latest' for the newest saved checkpoint."}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_checkpoint_restore",
        "description": "Preview whether a checkpoint can restore tracked staged/unstaged changes and saved untracked files. Use checkpoint_id='latest' for the newest checkpoint. Does not restore files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string", "description": "Checkpoint id to preview, or 'latest' for the newest saved checkpoint."}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_restore",
        "description": "Restore tracked staged/unstaged changes and saved untracked files from one compatible checkpoint after approval. Use checkpoint_id='latest' for the newest checkpoint. Refuses HEAD mismatches and extra current untracked files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string", "description": "Checkpoint id to restore, or 'latest' for the newest saved checkpoint."}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_checkpoint_delete",
        "description": "Preview deleting one saved checkpoint snapshot. Use checkpoint_id='latest' for the newest checkpoint. Does not delete files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string", "description": "Checkpoint id to preview deleting, or 'latest' for the newest saved checkpoint."}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_delete",
        "description": "Delete one saved checkpoint snapshot from the local runtime directory after approval. Use checkpoint_id='latest' for the newest checkpoint. Does not modify project files.",
        "input_schema": {
            "type": "object",
            "properties": {"checkpoint_id": {"type": "string", "description": "Checkpoint id to delete, or 'latest' for the newest saved checkpoint."}},
            "required": ["checkpoint_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_checkpoint_prune",
        "description": "Preview deleting older saved checkpoint snapshots while keeping the newest N. Does not delete files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keep_last": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 1000,
                    "description": "Number of newest checkpoints to keep. Use 0 to prune all checkpoints.",
                }
            },
            "required": ["keep_last"],
            "additionalProperties": False,
        },
    },
    {
        "name": "checkpoint_prune",
        "description": "Delete older saved checkpoint snapshots after approval while keeping the newest N. Does not modify project files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keep_last": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 1000,
                    "description": "Number of newest checkpoints to keep. Use 0 to prune all checkpoints.",
                }
            },
            "required": ["keep_last"],
            "additionalProperties": False,
        },
    },
]
