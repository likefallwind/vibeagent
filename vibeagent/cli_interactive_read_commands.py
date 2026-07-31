from __future__ import annotations

from typing import Any


def maybe_option_text(
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


def output_analysis_text(
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
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_repo_map_argument",
            "get_repo_map_text",
            "path",
            "path",
        )
    if command.type == "search":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_search_argument",
            "get_search_text",
            "query",
            "query",
            include_max_bytes=False,
        )
    if command.type == "search_contexts":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_search_argument",
            "get_search_contexts_text",
            "query",
            "query",
            include_max_bytes=True,
        )
    if command.type == "find_files":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_find_files_argument",
            "get_find_files_text",
            "query",
            "query",
        )
    if command.type == "glob":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_glob_argument",
            "get_glob_text",
            "pattern",
            "pattern",
        )
    if command.type == "tree":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_tree_argument",
            "get_tree_text",
            "path",
            "path",
        )
    if command.type == "symbols":
        return maybe_option_text(
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
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_read_argument",
            "get_read_text",
            "argument",
            "argument",
        )
    if command.type == "around":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_around_argument",
            "get_around_text",
            "argument",
            "argument",
        )
    if command.type == "around_many":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_around_many_argument",
            "get_around_many_text",
            "argument",
            "argument",
        )
    if command.type == "output_contexts":
        return output_analysis_text(
            command,
            commands,
            "Usage: /output-contexts [--context-lines N] [--max-contexts N] [--max-bytes N] -- <text>",
            "get_output_contexts_text",
        )
    if command.type == "output_diagnostics":
        return output_analysis_text(
            command,
            commands,
            "Usage: /output-diagnostics [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>",
            "get_output_diagnostics_text",
            include_max_diagnostics=True,
        )
    if command.type == "python_traceback":
        return output_analysis_text(
            command,
            commands,
            "Usage: /python-traceback [--context-lines N] [--max-diagnostics N] [--max-contexts N] [--max-bytes N] -- <text>",
            "get_python_traceback_text",
            include_max_diagnostics=True,
        )
    if command.type == "tail":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_tail_argument",
            "get_tail_text",
            "argument",
            "argument",
        )
    if command.type == "read_files":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_read_files_argument",
            "get_read_files_text",
            "argument",
            "argument",
        )
    if command.type == "read_ranges":
        return maybe_option_text(
            command,
            commands,
            "parse_interactive_read_ranges_argument",
            "get_read_ranges_text",
            "argument",
            "argument",
        )
    return None
