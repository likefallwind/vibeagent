from __future__ import annotations

from typing import Any


def build_overview_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(
        args,
        {
            "overview_max_files": "max_files",
            "overview_max_commands": "max_commands",
            "overview_max_checks": "max_checks",
        },
    )


def build_repo_map_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(
        args,
        {
            "repo_map_max_depth": "max_depth",
            "repo_map_max_files": "max_files",
            "repo_map_max_symbols": "max_symbols",
        },
    )


def build_search_kwargs(args: Any, *, include_context_bytes: bool = False) -> dict[str, object]:
    kwargs = _include_not_none(args, {"search_max_matches": "max_matches", "search_context_lines": "context_lines"})
    if getattr(args, "search_regex"):
        kwargs["regex"] = True
    if getattr(args, "search_ignore_case"):
        kwargs["case_sensitive"] = False
    if include_context_bytes and getattr(args, "search_context_max_bytes") is not None:
        kwargs["max_bytes_per_context"] = args.search_context_max_bytes
    return kwargs


def build_find_files_kwargs(args: Any) -> dict[str, object]:
    kwargs = _include_not_none(args, {"find_files_max_matches": "max_matches"})
    if getattr(args, "find_files_path"):
        kwargs["path"] = args.find_files_path
    if getattr(args, "find_files_regex"):
        kwargs["regex"] = True
    if getattr(args, "find_files_case_sensitive"):
        kwargs["case_sensitive"] = True
    if getattr(args, "find_files_include_dirs"):
        kwargs["include_dirs"] = True
    return kwargs


def build_glob_kwargs(args: Any) -> dict[str, object]:
    kwargs = _include_not_none(args, {"glob_max_matches": "max_matches"})
    if getattr(args, "glob_include_dirs"):
        kwargs["include_dirs"] = True
    return kwargs


def build_tree_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(args, {"tree_max_depth": "max_depth", "tree_max_entries": "max_entries"})


def build_symbols_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(args, {"symbols_max": "max_symbols"})


def build_read_kwargs(args: Any) -> dict[str, object]:
    kwargs = _include_not_none(args, {"read_max_bytes": "max_bytes"})
    if getattr(args, "read_line_numbers"):
        kwargs["show_line_numbers"] = True
    return kwargs


def build_around_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(args, {"around_max_bytes": "max_bytes"})


def build_around_many_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(args, {"around_many_max_bytes": "max_bytes_per_context"})


def build_output_context_kwargs(args: Any) -> dict[str, object]:
    return {
        "context_lines": args.output_context_lines,
        "max_contexts": args.output_context_max,
        "max_bytes_per_context": args.output_context_max_bytes,
    }


def build_output_diagnostic_kwargs(args: Any) -> dict[str, object]:
    return {
        "context_lines": args.output_diagnostic_lines,
        "max_diagnostics": args.output_diagnostic_max,
        "max_contexts": args.output_diagnostic_context_max,
        "max_bytes_per_context": args.output_diagnostic_context_max_bytes,
    }


def build_tail_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(args, {"tail_max_bytes": "max_bytes"})


def build_read_files_kwargs(args: Any) -> dict[str, object]:
    kwargs = _include_not_none(args, {"read_files_max_bytes": "max_bytes_per_file"})
    if getattr(args, "read_files_line_numbers"):
        kwargs["show_line_numbers"] = True
    return kwargs


def build_read_ranges_kwargs(args: Any) -> dict[str, object]:
    return _include_not_none(args, {"read_ranges_max_bytes": "max_bytes_per_range"})


def _include_not_none(args: Any, mapping: dict[str, str]) -> dict[str, object]:
    return {target: value for source, target in mapping.items() if (value := getattr(args, source)) is not None}
