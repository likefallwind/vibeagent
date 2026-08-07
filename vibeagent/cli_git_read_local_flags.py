from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def run_git_read_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.git_status:
        return local_text_or_report(
            args,
            "gitStatus",
            lambda: commands["get_git_status_report"](root),
            commands["format_git_status_report_text"],
            lambda: commands["get_git_status_text"](root),
        )
    if args.conflicts is not None:
        return local_text_or_report(
            args,
            "gitConflicts",
            lambda: commands["get_git_conflicts_report"](root, args.conflicts or None),
            commands["format_git_conflicts_report_text"],
            lambda: commands["get_git_conflicts_text"](root, args.conflicts or None),
        )
    if args.git_info:
        return local_text_or_report(
            args,
            "gitInfo",
            lambda: commands["get_git_info_report"](root),
            commands["format_git_info_report_text"],
            lambda: commands["get_git_info_text"](root),
        )
    if args.branches:
        return local_text_or_report(
            args,
            "branches",
            lambda: commands["get_branches_report"](root),
            commands["format_branches_report_text"],
            lambda: commands["get_branches_text"](root),
        )
    if args.log is not None:
        return local_text_or_report(
            args,
            "log",
            lambda: commands["get_log_report"](root, args.log or None, args.log_count),
            commands["format_log_report_text"],
            lambda: commands["get_log_text"](root, args.log or None, args.log_count),
        )
    if args.show is not None:
        return local_text_or_report(
            args,
            "show",
            lambda: commands["get_show_report"](
                root,
                rev=args.show or "HEAD",
                path=args.show_path,
                max_output_chars=args.show_max_chars,
            ),
            commands["format_show_report_text"],
            lambda: commands["get_show_text"](
                root,
                rev=args.show or "HEAD",
                path=args.show_path,
                max_output_chars=args.show_max_chars,
            ),
        )
    if args.blame is not None:
        return local_text_or_report(
            args,
            "blame",
            lambda: commands["get_blame_report"](root, args.blame, args.blame_lines, args.blame_max_chars),
            commands["format_blame_report_text"],
            lambda: commands["get_blame_text"](root, args.blame, args.blame_lines, args.blame_max_chars),
        )
    if args.stashes:
        return local_text_or_report(
            args,
            "stashes",
            lambda: commands["get_stashes_report"](root, max_entries=args.stash_count),
            commands["format_stashes_report_text"],
            lambda: commands["get_stashes_text"](root, max_entries=args.stash_count),
        )
    return None
