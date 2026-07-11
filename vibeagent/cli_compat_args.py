from __future__ import annotations

import argparse


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
        "--permission-mode",
        choices=("ask", "allow", "deny", "plan"),
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
        choices=("text", "stream-json"),
        default="text",
        help="Input format for task text read from stdin.",
    )


def normalize_compat_arguments(args: argparse.Namespace) -> argparse.Namespace:
    args.compat_error = None
    if args.dangerously_skip_permissions and (args.approval is not None or args.permission_mode is not None):
        args.compat_error = "--dangerously-skip-permissions cannot be combined with --approval or --permission-mode."
    if args.compat_error is None and args.approval is not None and args.permission_mode is not None and args.approval != args.permission_mode:
        args.compat_error = "--approval and --permission-mode cannot specify different policies."
    args.approval = "allow" if args.dangerously_skip_permissions else args.permission_mode or args.approval or "ask"

    if args.compat_error is None and args.max_iterations is not None and args.max_turns is not None and args.max_iterations != args.max_turns:
        args.compat_error = "--max-iterations and --max-turns cannot specify different values."
    if args.max_iterations is None and args.max_turns is not None:
        args.max_iterations = args.max_turns

    args.resume_from_continue = False
    if args.continue_latest and args.resume is None:
        args.resume = ""
        args.resume_from_continue = True
    return args
