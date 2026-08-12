from __future__ import annotations

import argparse

from .cli_resume_args import normalize_resume_arguments
from .safe_mode import resolve_safe_mode


PERMISSION_MODE_ALIASES = {
    "default": "ask",
    "acceptEdits": "ask",
    "bypassPermissions": "allow",
}
PERMISSION_MODE_CHOICES = ("ask", "allow", "auto", "deny", "dontAsk", "plan", *PERMISSION_MODE_ALIASES)


def add_compat_arguments(parser: argparse.ArgumentParser, *, positive_int, positive_decimal) -> None:
    parser.add_argument(
        "--background",
        "--bg",
        action="store_true",
        help="Start a one-shot coding agent in the background and return its management id.",
    )
    parser.add_argument(
        "-p",
        "--print",
        dest="print_mode",
        action="store_true",
        help="Claude-compatible one-shot alias; prints the result and exits.",
    )
    parser.add_argument(
        "-c",
        "--continue",
        dest="continue_latest",
        action="store_true",
        help="Claude-compatible alias for loading the newest session resume context.",
    )
    parser.add_argument(
        "--fork-session",
        action="store_true",
        help="Fork a resumed coding session under a new session id.",
    )
    parser.add_argument(
        "--no-session-persistence",
        action="store_true",
        help="Run a print-mode task without saving a resumable session.",
    )
    parser.add_argument(
        "--permission-mode",
        choices=PERMISSION_MODE_CHOICES,
        help="Claude-compatible alias for --approval.",
    )
    parser.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Claude-compatible alias for --approval allow on one-shot coding tasks.",
    )
    parser.add_argument(
        "--max-turns",
        type=positive_int,
        help="Claude-compatible alias for --max-iterations.",
    )
    parser.add_argument(
        "--input-format",
        choices=("text", "json", "stream-json"),
        default="text",
        help="Input format for task text read from stdin.",
    )
    parser.add_argument(
        "--json-schema",
        metavar="SCHEMA",
        help="Return validated structured_output matching a JSON Schema Draft-07 object (print mode only).",
    )
    parser.add_argument(
        "--max-budget-usd",
        type=positive_decimal,
        help="Stop a print-mode coding task when configured provider cost reaches this USD amount.",
    )
    parser.add_argument(
        "--fallback-model",
        metavar="MODELS",
        help="Use these comma-separated models in order after overloads in print-mode coding tasks.",
    )
    parser.add_argument(
        "--include-partial-messages",
        action="store_true",
        help="Emit incremental model SSE events with stream-json output in print mode.",
    )
    parser.add_argument(
        "--replay-user-messages",
        action="store_true",
        help="Replay normalized stream-json user input records on stdout before agent events.",
    )
    parser.add_argument(
        "--forward-subagent-text",
        action="store_true",
        help="Forward subagent text and tool results as linked stream-json messages.",
    )
    parser.add_argument(
        "--append-subagent-system-prompt",
        metavar="PROMPT",
        help="Append invocation-scoped instructions to every direct and nested subagent (print mode only).",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Disable custom instructions, skills, agents, plugins, hooks, MCP, LSP, workflows, and auto-memory.",
    )
    parser.add_argument(
        "--settings",
        metavar="JSON_OR_PATH",
        help="Load invocation settings from an inline JSON object or JSON file.",
    )
    parser.add_argument(
        "--setting-sources",
        metavar="SOURCES",
        help="Comma-separated settings sources: user, project, local.",
    )
    parser.add_argument(
        "--maintenance",
        action="store_true",
        help="Run Setup hooks with the maintenance matcher before a print-mode task.",
    )


def normalize_compat_arguments(args: argparse.Namespace) -> argparse.Namespace:
    args.compat_error = None
    args.setup_trigger = None
    args.safe_mode = resolve_safe_mode(args.safe_mode)
    if args.print_mode and args.init is not None:
        consumed_task = args.init
        args.init = None
        args.setup_trigger = "init"
        if consumed_task:
            args.task = [consumed_task, *args.task]
    if args.maintenance:
        if args.setup_trigger is not None:
            args.compat_error = "--init and --maintenance cannot be combined."
        else:
            args.setup_trigger = "maintenance"
    permission_mode = normalize_permission_mode(args.permission_mode)
    if args.dangerously_skip_permissions and (args.approval is not None or args.permission_mode is not None):
        args.compat_error = "--dangerously-skip-permissions cannot be combined with --approval or --permission-mode."
    if args.compat_error is None and args.approval is not None and permission_mode is not None and args.approval != permission_mode:
        args.compat_error = "--approval and --permission-mode cannot specify different policies."
    args.approval = "allow" if args.dangerously_skip_permissions else permission_mode or args.approval or "ask"

    if args.compat_error is None and args.max_iterations is not None and args.max_turns is not None and args.max_iterations != args.max_turns:
        args.compat_error = "--max-iterations and --max-turns cannot specify different values."
    if args.max_iterations is None and args.max_turns is not None:
        args.max_iterations = args.max_turns

    return normalize_resume_arguments(args)


def normalize_permission_mode(value: str | None) -> str | None:
    if value is None:
        return None
    return PERMISSION_MODE_ALIASES.get(value, value)


def permission_mode_accepts_edits(value: str | None) -> bool:
    return value == "acceptEdits"
