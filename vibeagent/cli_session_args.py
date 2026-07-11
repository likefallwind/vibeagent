from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_session_limit_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    nonnegative_int: IntParser,
) -> None:
    parser.add_argument("--session-output-command-max", type=positive_int, default=20, metavar="N", help="Maximum session command outputs to scan with --session-output-contexts or --session-output-diagnostics.")
    parser.add_argument("--session-output-max-chars", type=positive_int, default=20_000, metavar="N", help="Maximum characters to read per session command output.")
    parser.add_argument("--session-output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Surrounding line count for --session-output-contexts or --session-output-diagnostics.")
    parser.add_argument("--session-output-context-max", type=positive_int, default=20, metavar="N", help="Maximum contexts to read with --session-output-contexts or --session-output-diagnostics.")
    parser.add_argument("--session-output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per session output source context.")
    parser.add_argument("--session-output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --session-output-diagnostics.")
    parser.add_argument("--session-transcript-event-max", type=positive_int, metavar="N", help="Maximum timeline events to show with --transcript.")
    parser.add_argument("--session-search-match-max", type=positive_int, metavar="N", help="Maximum matching timeline events to show with --session-search.")
    parser.add_argument("--session-search-case-sensitive", action="store_true", help="Use case-sensitive matching with --session-search.")
    parser.add_argument("--session-max-checks", type=positive_int, metavar="N", help="Maximum check rows per group to show with --session-verification, --run-session-verification, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-commands", type=positive_int, metavar="N", help="Maximum command results to show with --session-commands, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-output-chars", type=nonnegative_int, metavar="N", help="Maximum stdout/stderr tail characters per command with --session-commands or --session-handoff.")
    parser.add_argument("--session-max-files", type=positive_int, metavar="N", help="Maximum file references to show with --session-files, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-failures", type=positive_int, metavar="N", help="Maximum failure entries to show with --session-failures, --session-audit, or --session-handoff.")
    parser.add_argument("--session-max-text", type=positive_int, metavar="N", help="Maximum text characters per timeline, search, failure, or readiness entry.")


def add_session_local_arguments(
    parser: argparse.ArgumentParser,
    local: argparse._MutuallyExclusiveGroup,
) -> None:
    local.add_argument("--sessions", action="store_true", help="List recent local sessions and exit.")
    local.add_argument("--last", action="store_true", help="Show the newest session summary and exit.")
    local.add_argument("--session", metavar="RUN_ID", help="Show one compact session summary and exit.")
    local.add_argument("--plan", nargs="?", const="", metavar="RUN_ID", help="Show the newest or selected session task plan and exit.")
    local.add_argument("--transcript", nargs="?", const="", metavar="RUN_ID", help="Show a safe timeline of the newest or selected session and exit.")
    local.add_argument("--session-search", metavar="QUERY", help="Search the newest or selected safe session timeline and exit.")
    parser.add_argument("--session-search-run", metavar="RUN_ID", help="Session id for --session-search.")
    local.add_argument("--session-commands", nargs="?", const="", metavar="RUN_ID", help="Show bounded stdout/stderr from the newest or selected session commands and exit.")
    local.add_argument("--session-output-contexts", nargs="?", const="", metavar="RUN_ID", help="Extract file:line contexts from newest or selected session command output and exit.")
    local.add_argument("--session-output-diagnostics", nargs="?", const="", metavar="RUN_ID", help="Summarize diagnostics from newest or selected session command output and exit.")
    local.add_argument("--session-files", nargs="?", const="", metavar="RUN_ID", help="Show project paths referenced by the newest or selected session and exit.")
    local.add_argument("--session-failures", nargs="?", const="", metavar="RUN_ID", help="Show failed tools, commands, final results, malformed events, and denied approvals from the newest or selected session and exit.")
    local.add_argument("--session-verification", nargs="?", const="", metavar="RUN_ID", help="Show verified, pending, and failed suggested checks for the newest or selected session and exit.")
    local.add_argument("--run-session-verification", nargs="?", const="", metavar="RUN_ID", help="Rerun failed and pending verification commands from the newest or selected session and exit.")
    local.add_argument("--session-audit", nargs="?", const="", metavar="RUN_ID", help="Show finish-time readiness, blockers, active processes, checks, failures, commands, and files for the newest or selected session and exit.")
    local.add_argument("--session-handoff", nargs="?", const="", metavar="RUN_ID", help="Show a compact recovery handoff bundle for the newest or selected session and exit.")
