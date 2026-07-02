from __future__ import annotations

import argparse

from .cli_parse_diff_git import build_diff_argument


def normalize_task_bound_diff_args(args: argparse.Namespace) -> None:
    if args.diff_contexts is not None and args.task:
        args.diff_contexts = build_diff_argument(args.diff_contexts, args.diff_staged, args.task)
        args.task = []
    elif args.diff_contexts is not None and args.diff_staged:
        args.diff_contexts = build_diff_argument(args.diff_contexts, args.diff_staged, [])
    elif args.diff_hunks is not None and args.task:
        args.diff_hunks = build_diff_argument(args.diff_hunks, args.diff_staged, args.task)
        args.task = []
    elif args.diff_hunks is not None and args.diff_staged:
        args.diff_hunks = build_diff_argument(args.diff_hunks, args.diff_staged, [])
    elif args.diff is not None and args.task:
        args.diff = build_diff_argument(args.diff, args.diff_staged, args.task)
        args.task = []
    elif args.diff is not None and args.diff_staged:
        args.diff = build_diff_argument(args.diff, args.diff_staged, [])


__all__ = ["normalize_task_bound_diff_args"]
