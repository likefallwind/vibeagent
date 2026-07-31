from __future__ import annotations

import argparse
from typing import Callable


IntParser = Callable[[str], int]


def add_runtime_local_arguments(local: argparse._MutuallyExclusiveGroup) -> None:
    local.add_argument("--command-check", "--command", dest="command_check", metavar="COMMAND", help="Preview whether one shell command can run and exit.")
    local.add_argument("--run-command", "--run", dest="run_command", metavar="COMMAND", help="Run one finite shell command with safety checks and exit.")
    local.add_argument("--check-run-commands", nargs="+", metavar="COMMAND", help="Preview a short ordered command sequence and exit.")
    local.add_argument("--run-commands", nargs="+", metavar="COMMAND", help="Run a short ordered command sequence and exit.")
    local.add_argument("--check-start-command", metavar="COMMAND", help="Preview starting one long-running shell command and exit.")
    local.add_argument("--start-command", "--start", dest="start_command", metavar="COMMAND", help="Start one long-running shell command and exit.")


def add_runtime_network_local_arguments(
    local: argparse._MutuallyExclusiveGroup,
    *,
    positive_int: IntParser,
) -> None:
    local.add_argument("--port-check", type=positive_int, metavar="PORT", help="Check whether one local TCP port is reachable and exit.")
    local.add_argument("--http-check", metavar="URL", help="Check HTTP status and optional response text and exit.")
    local.add_argument("--http-fetch", metavar="URL", help="Fetch bounded HTTP response metadata and body text and exit.")


def add_runtime_connection_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    timeout_ms: IntParser,
) -> None:
    parser.add_argument("--command-cwd", metavar="PATH", help="Project-relative command cwd for --command-check or --command.")
    parser.add_argument("--run-cwd", metavar="PATH", help="Project-relative command cwd for --run-command, --run, --run-commands, or --check-run-commands.")
    parser.add_argument("--start-cwd", metavar="PATH", help="Project-relative command cwd for --check-start-command, --start-command, or --start.")
    parser.add_argument("--port-host", default="127.0.0.1", metavar="HOST", help="TCP host for --port-check.")
    parser.add_argument("--port-timeout-ms", type=timeout_ms, default=1_000, metavar="N", help="Maximum milliseconds for --port-check.")
    parser.add_argument("--http-timeout-ms", type=timeout_ms, metavar="N", help="Maximum milliseconds for --http-check or --http-fetch.")
    parser.add_argument("--http-max-body-chars", type=positive_int, metavar="N", help="Maximum response body characters for --http-check or --http-fetch.")
    parser.add_argument("--http-contains", metavar="TEXT", help="Require response body text for --http-check.")
    parser.add_argument("--http-regex", action="store_true", help="Treat --http-contains as a regular expression.")


def add_runtime_run_option_arguments(
    parser: argparse.ArgumentParser,
    *,
    positive_int: IntParser,
    nonnegative_int: IntParser,
    timeout_ms: IntParser,
) -> None:
    parser.add_argument("--run-timeout-ms", type=timeout_ms, default=30_000, metavar="N", help="Maximum milliseconds for --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.")
    parser.add_argument("--run-max-chars", type=positive_int, default=12_000, metavar="N", help="Maximum stdout/stderr characters for --run-command, --run, --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.")
    parser.add_argument("--run-continue-on-failure", action="store_true", help="Continue after a failing command with --run-commands, --run-suggested-checks, --run-focused-tests, or --run-session-verification.")
    parser.add_argument("--run-session-no-failed", action="store_true", help="Do not rerun failed checks with --run-session-verification.")
    parser.add_argument("--run-session-no-pending", action="store_true", help="Do not run pending checks with --run-session-verification.")
    parser.add_argument("--run-output-contexts", action="store_true", help="Extract file:line source contexts from finite run output, including session verification reruns.")
    parser.add_argument("--run-output-diagnostics", action="store_true", help="Summarize errors, warnings, and failures from finite run output, including session verification reruns.")
    parser.add_argument("--run-output-context-lines", type=nonnegative_int, default=5, metavar="N", help="Context lines around each extracted run output reference.")
    parser.add_argument("--run-output-diagnostic-max", type=positive_int, default=50, metavar="N", help="Maximum diagnostic lines to show with --run-output-diagnostics or failed-command auto-diagnostics.")
    parser.add_argument("--run-output-context-max", type=positive_int, default=20, metavar="N", help="Maximum extracted run output contexts.")
    parser.add_argument("--run-output-context-max-bytes", type=positive_int, default=20_000, metavar="N", help="Maximum bytes per extracted run output context.")
