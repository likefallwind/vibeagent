from __future__ import annotations

import argparse
from typing import Any

from .cli_local_result import local_text_or_report


def run_read_local_flag(
    args: argparse.Namespace,
    project_root: Any,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.overview:
        overview_kwargs = {}
        if args.overview_max_files is not None:
            overview_kwargs["max_files"] = args.overview_max_files
        if args.overview_max_commands is not None:
            overview_kwargs["max_commands"] = args.overview_max_commands
        if args.overview_max_checks is not None:
            overview_kwargs["max_checks"] = args.overview_max_checks
        return local_text_or_report(
            args,
            "overview",
            lambda: commands["get_overview_report"](root, **overview_kwargs),
            commands["format_overview_report_text"],
            lambda: commands["get_overview_text"](root, **overview_kwargs),
        )
    if args.repo_map is not None:
        repo_map_kwargs = {}
        if args.repo_map_max_depth is not None:
            repo_map_kwargs["max_depth"] = args.repo_map_max_depth
        if args.repo_map_max_files is not None:
            repo_map_kwargs["max_files"] = args.repo_map_max_files
        if args.repo_map_max_symbols is not None:
            repo_map_kwargs["max_symbols"] = args.repo_map_max_symbols
        return local_text_or_report(
            args,
            "repoMap",
            lambda: commands["get_repo_map_report"](root, args.repo_map or None, **repo_map_kwargs),
            commands["format_repo_map_report_text"],
            lambda: commands["get_repo_map_text"](root, args.repo_map or None, **repo_map_kwargs),
        )
    if args.search is not None:
        search_kwargs = {}
        if args.search_max_matches is not None:
            search_kwargs["max_matches"] = args.search_max_matches
        if args.search_regex:
            search_kwargs["regex"] = True
        if args.search_ignore_case:
            search_kwargs["case_sensitive"] = False
        if args.search_context_lines is not None:
            search_kwargs["context_lines"] = args.search_context_lines
        return local_text_or_report(
            args,
            "search",
            lambda: commands["get_search_report"](root, args.search, args.search_path, **search_kwargs),
            commands["format_search_report_text"],
            lambda: commands["get_search_text"](root, args.search, args.search_path, **search_kwargs),
        )
    if args.search_contexts is not None:
        search_contexts_kwargs = {}
        if args.search_max_matches is not None:
            search_contexts_kwargs["max_matches"] = args.search_max_matches
        if args.search_regex:
            search_contexts_kwargs["regex"] = True
        if args.search_ignore_case:
            search_contexts_kwargs["case_sensitive"] = False
        if args.search_context_lines is not None:
            search_contexts_kwargs["context_lines"] = args.search_context_lines
        if args.search_context_max_bytes is not None:
            search_contexts_kwargs["max_bytes_per_context"] = args.search_context_max_bytes
        return local_text_or_report(
            args,
            "searchContexts",
            lambda: commands["get_search_contexts_report"](
                root,
                args.search_contexts,
                args.search_path,
                **search_contexts_kwargs,
            ),
            commands["format_search_contexts_report_text"],
            lambda: commands["get_search_contexts_text"](
                root,
                args.search_contexts,
                args.search_path,
                **search_contexts_kwargs,
            ),
        )
    if args.find_files is not None:
        find_files_kwargs = {}
        if args.find_files_path:
            find_files_kwargs["path"] = args.find_files_path
        if args.find_files_max_matches is not None:
            find_files_kwargs["max_matches"] = args.find_files_max_matches
        if args.find_files_regex:
            find_files_kwargs["regex"] = True
        if args.find_files_case_sensitive:
            find_files_kwargs["case_sensitive"] = True
        if args.find_files_include_dirs:
            find_files_kwargs["include_dirs"] = True
        return local_text_or_report(
            args,
            "findFiles",
            lambda: commands["get_find_files_report"](root, args.find_files, **find_files_kwargs),
            commands["format_find_files_report_text"],
            lambda: commands["get_find_files_text"](root, args.find_files, **find_files_kwargs),
        )
    if args.glob is not None:
        glob_kwargs = {}
        if args.glob_max_matches is not None:
            glob_kwargs["max_matches"] = args.glob_max_matches
        if args.glob_include_dirs:
            glob_kwargs["include_dirs"] = True
        return local_text_or_report(
            args,
            "glob",
            lambda: commands["get_glob_report"](root, args.glob, **glob_kwargs),
            commands["format_glob_report_text"],
            lambda: commands["get_glob_text"](root, args.glob, **glob_kwargs),
        )
    if args.tree is not None:
        tree_kwargs = {}
        if args.tree_max_depth is not None:
            tree_kwargs["max_depth"] = args.tree_max_depth
        if args.tree_max_entries is not None:
            tree_kwargs["max_entries"] = args.tree_max_entries
        return local_text_or_report(
            args,
            "tree",
            lambda: commands["get_tree_report"](root, args.tree or None, **tree_kwargs),
            commands["format_tree_report_text"],
            lambda: commands["get_tree_text"](root, args.tree or None, **tree_kwargs),
        )
    if args.symbols is not None:
        symbols_kwargs = {}
        if args.symbols_max is not None:
            symbols_kwargs["max_symbols"] = args.symbols_max
        return local_text_or_report(
            args,
            "symbols",
            lambda: commands["get_symbols_report"](root, args.symbols, **symbols_kwargs),
            commands["format_symbols_report_text"],
            lambda: commands["get_symbols_text"](root, args.symbols, **symbols_kwargs),
        )
    if args.file_info is not None:
        return local_text_or_report(
            args,
            "fileInfo",
            lambda: commands["get_file_info_report"](root, args.file_info),
            commands["format_file_info_report_text"],
            lambda: commands["get_file_info_text"](root, args.file_info),
        )
    if args.image_info is not None:
        return local_text_or_report(
            args,
            "imageInfo",
            lambda: commands["get_image_info_report"](root, args.image_info),
            commands["format_image_info_report_text"],
            lambda: commands["get_image_info_text"](root, args.image_info),
        )
    if args.read is not None:
        read_kwargs = {}
        if args.read_max_bytes is not None:
            read_kwargs["max_bytes"] = args.read_max_bytes
        if args.read_line_numbers:
            read_kwargs["show_line_numbers"] = True
        return local_text_or_report(
            args,
            "read",
            lambda: commands["get_read_report"](root, args.read, args.read_lines, **read_kwargs),
            commands["format_read_report_text"],
            lambda: commands["get_read_text"](root, args.read, args.read_lines, **read_kwargs),
        )
    if args.around is not None:
        around_kwargs = {}
        if args.around_max_bytes is not None:
            around_kwargs["max_bytes"] = args.around_max_bytes
        around_argument = f"{args.around[0]} {args.around[1]}"
        return local_text_or_report(
            args,
            "around",
            lambda: commands["get_around_report"](root, around_argument, args.around_lines, **around_kwargs),
            commands["format_around_report_text"],
            lambda: commands["get_around_text"](root, around_argument, args.around_lines, **around_kwargs),
        )
    if args.around_many is not None:
        around_many_kwargs = {}
        if args.around_many_max_bytes is not None:
            around_many_kwargs["max_bytes_per_context"] = args.around_many_max_bytes
        return local_text_or_report(
            args,
            "aroundMany",
            lambda: commands["get_around_many_report"](root, args.around_many, **around_many_kwargs),
            commands["format_around_many_report_text"],
            lambda: commands["get_around_many_text"](root, args.around_many, **around_many_kwargs),
        )
    if args.output_contexts is not None:
        output_context_kwargs = {
            "context_lines": args.output_context_lines,
            "max_contexts": args.output_context_max,
            "max_bytes_per_context": args.output_context_max_bytes,
        }
        return local_text_or_report(
            args,
            "outputContexts",
            lambda: commands["get_output_contexts_report"](root, args.output_contexts, **output_context_kwargs),
            commands["format_output_contexts_report_text"],
            lambda: commands["get_output_contexts_text"](root, args.output_contexts, **output_context_kwargs),
        )
    if args.output_diagnostics is not None:
        output_diagnostic_kwargs = {
            "context_lines": args.output_diagnostic_lines,
            "max_diagnostics": args.output_diagnostic_max,
            "max_contexts": args.output_diagnostic_context_max,
            "max_bytes_per_context": args.output_diagnostic_context_max_bytes,
        }
        return local_text_or_report(
            args,
            "outputDiagnostics",
            lambda: commands["get_output_diagnostics_report"](root, args.output_diagnostics, **output_diagnostic_kwargs),
            commands["format_output_diagnostics_report_text"],
            lambda: commands["get_output_diagnostics_text"](root, args.output_diagnostics, **output_diagnostic_kwargs),
        )
    if args.python_traceback is not None:
        python_traceback_kwargs = {
            "context_lines": args.output_diagnostic_lines,
            "max_diagnostics": args.output_diagnostic_max,
            "max_contexts": args.output_diagnostic_context_max,
            "max_bytes_per_context": args.output_diagnostic_context_max_bytes,
        }
        return local_text_or_report(
            args,
            "pythonTraceback",
            lambda: commands["get_python_traceback_report"](root, args.python_traceback, **python_traceback_kwargs),
            commands["format_python_traceback_report_text"],
            lambda: commands["get_python_traceback_text"](root, args.python_traceback, **python_traceback_kwargs),
        )
    if args.tail is not None:
        tail_kwargs = {}
        if args.tail_max_bytes is not None:
            tail_kwargs["max_bytes"] = args.tail_max_bytes
        return local_text_or_report(
            args,
            "tail",
            lambda: commands["get_tail_report"](root, args.tail, args.tail_lines, **tail_kwargs),
            commands["format_tail_report_text"],
            lambda: commands["get_tail_text"](root, args.tail, args.tail_lines, **tail_kwargs),
        )
    if args.read_files is not None:
        read_files_kwargs = {}
        if args.read_files_max_bytes is not None:
            read_files_kwargs["max_bytes_per_file"] = args.read_files_max_bytes
        if args.read_files_line_numbers:
            read_files_kwargs["show_line_numbers"] = True
        return local_text_or_report(
            args,
            "readFiles",
            lambda: commands["get_read_files_report"](root, args.read_files, **read_files_kwargs),
            commands["format_read_files_report_text"],
            lambda: commands["get_read_files_text"](root, args.read_files, **read_files_kwargs),
        )
    if args.read_ranges is not None:
        read_ranges_kwargs = {}
        if args.read_ranges_max_bytes is not None:
            read_ranges_kwargs["max_bytes_per_range"] = args.read_ranges_max_bytes
        return local_text_or_report(
            args,
            "readRanges",
            lambda: commands["get_read_ranges_report"](root, args.read_ranges, **read_ranges_kwargs),
            commands["format_read_ranges_report_text"],
            lambda: commands["get_read_ranges_text"](root, args.read_ranges, **read_ranges_kwargs),
        )
    return None


def _maybe_option_text(
    command: Any,
    commands: dict[str, Any],
    parser_name: str,
    getter_name: str,
    parsed_name: str,
    original_name: str,
    *parser_args: Any,
    **parser_kwargs: Any,
) -> str:
    parsed, kwargs, error, uses_named_options = commands[parser_name](
        command.argument,
        *parser_args,
        **parser_kwargs,
    )
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](**{parsed_name: parsed}, **kwargs)
    return commands[getter_name](**{original_name: command.argument})


def _output_analysis_text(
    command: Any,
    commands: dict[str, Any],
    usage: str,
    getter_name: str,
    *,
    include_max_diagnostics: bool = False,
) -> str:
    output_text, kwargs, error, uses_named_options = commands["parse_interactive_output_analysis_argument"](
        command.argument,
        usage,
        include_max_diagnostics=include_max_diagnostics,
    )
    if error:
        return error
    if uses_named_options:
        return commands[getter_name](text=output_text, **kwargs)
    return commands[getter_name](text=command.argument)


def run_interactive_read_command(command: Any, commands: dict[str, Any]) -> str | None:
    if command.type == "overview":
        kwargs, error, uses_named_options = commands["parse_interactive_overview_argument"](command.argument)
        if error:
            return error
        return commands["get_overview_text"](**kwargs) if uses_named_options else commands["get_overview_text"]()
    if command.type == "repo_map":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_repo_map_argument",
            "get_repo_map_text",
            "path",
            "path",
        )
    if command.type == "search":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_search_argument",
            "get_search_text",
            "query",
            "query",
            include_max_bytes=False,
        )
    if command.type == "search_contexts":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_search_argument",
            "get_search_contexts_text",
            "query",
            "query",
            include_max_bytes=True,
        )
    if command.type == "find_files":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_find_files_argument",
            "get_find_files_text",
            "query",
            "query",
        )
    if command.type == "glob":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_glob_argument",
            "get_glob_text",
            "pattern",
            "pattern",
        )
    if command.type == "tree":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_tree_argument",
            "get_tree_text",
            "path",
            "path",
        )
    if command.type == "symbols":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_symbols_argument",
            "get_symbols_text",
            "argument",
            "argument",
        )
    if command.type == "file_info":
        return commands["get_file_info_text"](argument=command.argument)
    if command.type == "image_info":
        return commands["get_image_info_text"](argument=command.argument)
    if command.type == "read":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_read_argument",
            "get_read_text",
            "argument",
            "argument",
        )
    if command.type == "around":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_around_argument",
            "get_around_text",
            "argument",
            "argument",
        )
    if command.type == "around_many":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_around_many_argument",
            "get_around_many_text",
            "argument",
            "argument",
        )
    if command.type == "output_contexts":
        return _output_analysis_text(
            command,
            commands,
            "Usage: /output-contexts [--context-lines N] [--max-contexts N] [--max-bytes N] -- <text>",
            "get_output_contexts_text",
        )
    if command.type == "output_diagnostics":
        return _output_analysis_text(
            command,
            commands,
            "Usage: /output-diagnostics [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>",
            "get_output_diagnostics_text",
            include_max_diagnostics=True,
        )
    if command.type == "python_traceback":
        return _output_analysis_text(
            command,
            commands,
            "Usage: /python-traceback [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>",
            "get_python_traceback_text",
            include_max_diagnostics=True,
        )
    if command.type == "tail":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_tail_argument",
            "get_tail_text",
            "argument",
            "argument",
        )
    if command.type == "read_files":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_read_files_argument",
            "get_read_files_text",
            "argument",
            "argument",
        )
    if command.type == "read_ranges":
        return _maybe_option_text(
            command,
            commands,
            "parse_interactive_read_ranges_argument",
            "get_read_ranges_text",
            "argument",
            "argument",
        )
    return None
