from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_process_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--env", action="store_true", help="Show local OS, runtime, and tool availability and exit.")
    local.add_argument("--processes", action="store_true", help="Show VibeAgent-started background processes and exit.")
    local.add_argument("--process-output", metavar="ID", help="Show captured stdout and stderr for one VibeAgent-started background process and exit.")
    local.add_argument("--process-output-contexts", metavar="ID", help="Extract file:line source contexts from one background process output and exit.")
    local.add_argument("--process-output-diagnostics", metavar="ID", help="Summarize diagnostics from one background process output and exit.")
    local.add_argument("--wait-process", metavar="ID", help="Wait briefly for one VibeAgent-started background process and exit.")
    local.add_argument("--check-write-process", metavar="ID", help="Preview writing stdin text to one VibeAgent-started background process and exit.")
    local.add_argument("--write-process", metavar="ID", help="Write stdin text to one VibeAgent-started background process and exit.")
    local.add_argument("--check-stop-process", metavar="ID", help="Preview stopping one VibeAgent-started background process and exit.")
    local.add_argument("--stop-process", metavar="ID", help="Stop one VibeAgent-started background process and exit.")
    local.add_argument("--check-stop-all-processes", action="store_true", help="Preview stopping all VibeAgent-started background processes and exit.")
    local.add_argument("--stop-all-processes", action="store_true", help="Stop all VibeAgent-started background processes and exit.")


def add_process_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    nonnegative_int: IntParser,
    timeout_ms: IntParser,
) -> None:
    parser.add_argument("--process-max-chars", type=positive_int, metavar="N", help="Maximum captured output characters for --process-output, --process-output-contexts, or --process-output-diagnostics.")
    parser.add_argument("--process-output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Context lines around each extracted process output reference.")
    parser.add_argument("--process-output-context-max", type=positive_int, default=20, metavar="N", help="Maximum extracted process output contexts.")
    parser.add_argument("--process-output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per extracted process output context.")
    parser.add_argument("--process-output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --process-output-diagnostics.")
    parser.add_argument("--wait-timeout-ms", type=timeout_ms, default=5_000, metavar="N", help="Maximum milliseconds to wait with --wait-process.")
    parser.add_argument("--wait-max-chars", type=positive_int, metavar="N", help="Maximum captured output characters for --wait-process.")
    parser.add_argument("--wait-stdout", metavar="TEXT", help="Return early when --wait-process stdout contains TEXT.")
    parser.add_argument("--wait-stderr", metavar="TEXT", help="Return early when --wait-process stderr contains TEXT.")
    parser.add_argument("--wait-regex", action="store_true", help="Treat --wait-stdout or --wait-stderr as a regular expression.")
    parser.add_argument("--write-stdin", metavar="TEXT", help="Stdin text for --check-write-process or --write-process. Quote text with spaces; use \\n when pressing Enter is required.")
    parser.add_argument("--write-stdin-file", metavar="PATH", help="Project-relative UTF-8 file to use as stdin text for --check-write-process or --write-process.")
