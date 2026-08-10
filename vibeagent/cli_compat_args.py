from __future__ import annotations

import argparse

from .cli_resume_args import normalize_resume_arguments


PERMISSION_MODE_ALIASES = {
    "default": "ask",
    "acceptEdits": "ask",
    "bypassPermissions": "allow",
}
PERMISSION_MODE_CHOICES = ("ask", "allow", "deny", "plan", *PERMISSION_MODE_ALIASES)


def add_compat_arguments(parser: argparse.ArgumentParser, *, positive_int) -> None:
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


def normalize_compat_arguments(args: argparse.Namespace) -> argparse.Namespace:
    args.compat_error = None
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
