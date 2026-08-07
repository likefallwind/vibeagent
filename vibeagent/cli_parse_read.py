from __future__ import annotations

import shlex

from .cli_parse_read_contexts import (
    parse_interactive_around_argument,
    parse_interactive_around_many_argument,
    parse_interactive_max_bytes_argument,
    parse_interactive_output_analysis_argument,
    parse_interactive_read_ranges_argument,
    parse_interactive_tail_argument,
)
from .cli_parse_read_paths import parse_interactive_read_path_options
from .cli_parse_read_tree_symbols import parse_interactive_symbols_argument, parse_interactive_tree_argument


def parse_interactive_read_argument(
    argument: str | None,
) -> tuple[str | None, dict[str, int | bool], str | None, bool]:
    usage = "Usage: /read [--max-bytes N] [--line-numbers] -- <path> [start[:end]]"
    paths, kwargs, error, handled = parse_interactive_read_path_options(
        argument,
        usage,
        "max_bytes",
        "path is required.",
    )
    if paths is None:
        return None, kwargs, error, handled
    return " ".join(shlex.quote(part) for part in paths), kwargs, None, True


def parse_interactive_read_files_argument(
    argument: str | None,
) -> tuple[list[str] | None, dict[str, int | bool], str | None, bool]:
    usage = "Usage: /read-files [--max-bytes N] [--line-numbers] -- <path...>"
    return parse_interactive_read_path_options(
        argument,
        usage,
        "max_bytes_per_file",
        "at least one path is required.",
    )
