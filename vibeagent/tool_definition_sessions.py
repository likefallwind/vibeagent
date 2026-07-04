from __future__ import annotations

from typing import Any


SESSION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
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
