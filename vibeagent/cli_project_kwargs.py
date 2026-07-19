from __future__ import annotations

import argparse
import shlex

from .cli_parse_core import build_focused_tests_kwargs
from .tool_search_options import tool_search_approval_filter


def build_config_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "max_iterations": args.max_iterations,
        "command_timeout_ms": args.command_timeout_ms,
        "max_output_tokens": args.max_output_tokens,
        "model_retries": args.model_retries,
        "model_retry_delay_ms": args.model_retry_delay_ms,
        "model_timeout_ms": args.model_timeout_ms,
    }


def build_tool_search_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "max_matches": args.tool_search_max,
        "category": args.tool_search_category,
        "approval_required": tool_search_approval_filter(args.tool_search_approval),
    }


def build_check_suggested_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "argument": args.check_suggested_checks or None,
        "max_checks": args.check_suggested_checks_max,
    }


def build_run_suggested_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "argument": args.run_suggested_checks or None,
        "max_checks": args.run_suggested_checks_max,
        "timeout_ms": args.run_timeout_ms,
        "max_output_chars": args.run_max_chars,
        "stop_on_failure": not args.run_continue_on_failure,
        "extract_output_contexts": args.run_output_contexts,
        "extract_output_diagnostics": args.run_output_diagnostics,
        "context_lines": args.run_output_context_lines,
        "max_diagnostics": args.run_output_diagnostic_max,
        "max_contexts": args.run_output_context_max,
        "max_bytes_per_context": args.run_output_context_max_bytes,
    }


def kwargs_without_keys(kwargs: dict[str, object], *excluded: str) -> dict[str, object]:
    excluded_keys = set(excluded)
    return {key: value for key, value in kwargs.items() if key not in excluded_keys}


def kwargs_without_argument(kwargs: dict[str, object]) -> dict[str, object]:
    return kwargs_without_keys(kwargs, "argument")


def build_focused_tests_local_kwargs(args: argparse.Namespace, values: list[str]) -> dict[str, object]:
    return build_focused_tests_kwargs(args) | {"argument": shlex.join(values) if values else None}


def build_run_focused_tests_kwargs(args: argparse.Namespace) -> dict[str, object]:
    focused_kwargs = build_focused_tests_local_kwargs(args, args.run_focused_tests)
    focused_kwargs.update(
        {
            "timeout_ms": args.run_timeout_ms,
            "max_output_chars": args.run_max_chars,
            "stop_on_failure": not args.run_continue_on_failure,
            "extract_output_contexts": args.run_output_contexts,
            "extract_output_diagnostics": args.run_output_diagnostics,
            "context_lines": args.run_output_context_lines,
            "max_diagnostics": args.run_output_diagnostic_max,
            "max_contexts": args.run_output_context_max,
            "max_bytes_per_context": args.run_output_context_max_bytes,
        }
    )
    return focused_kwargs


def build_project_commands_kwargs(args: argparse.Namespace) -> dict[str, int]:
    kwargs: dict[str, int] = {}
    if args.commands_max_commands is not None:
        kwargs["max_commands"] = args.commands_max_commands
    if args.commands_max_files is not None:
        kwargs["max_files"] = args.commands_max_files
    return kwargs


def build_related_tests_local_kwargs(args: argparse.Namespace) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if args.related_tests_max_paths is not None:
        kwargs["max_paths"] = args.related_tests_max_paths
    if args.related_tests_max_candidates is not None:
        kwargs["max_candidates"] = args.related_tests_max_candidates
    kwargs["argument"] = shlex.join(args.related_tests) if args.related_tests else None
    return kwargs


def build_manifests_kwargs(args: argparse.Namespace) -> dict[str, int]:
    kwargs: dict[str, int] = {}
    if args.manifests_max_files is not None:
        kwargs["max_files"] = args.manifests_max_files
    if args.manifests_max_items is not None:
        kwargs["max_items"] = args.manifests_max_items
    return kwargs


def build_instructions_kwargs(args: argparse.Namespace) -> dict[str, int]:
    kwargs: dict[str, int] = {}
    if args.instructions_max_files is not None:
        kwargs["max_files"] = args.instructions_max_files
    if args.instructions_max_bytes is not None:
        kwargs["max_bytes"] = args.instructions_max_bytes
    return kwargs


def build_todos_kwargs(args: argparse.Namespace) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if args.todos_max_items is not None:
        kwargs["max_items"] = args.todos_max_items
    if args.todos_max_files is not None:
        kwargs["max_files"] = args.todos_max_files
    kwargs["path"] = args.todos or None
    return kwargs
