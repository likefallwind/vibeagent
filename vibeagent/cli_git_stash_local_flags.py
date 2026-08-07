from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def run_git_stash_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.check_git_stash is not None:
        stash_arg = commands["build_stash_argument"](args.check_git_stash, args.stash_include_untracked)
        return local_text_or_report(
            args,
            "checkGitStash",
            lambda: commands["get_check_stash_report"](root, stash_arg),
            lambda report: commands["format_git_stash_report_text"]("Check stash", report),
            lambda: commands["get_check_stash_text"](root, stash_arg),
        )
    if args.git_stash is not None:
        stash_arg = commands["build_stash_argument"](args.git_stash, args.stash_include_untracked)
        return local_text_or_report(
            args,
            "gitStash",
            lambda: commands["get_stash_report"](root, stash_arg),
            lambda report: commands["format_git_stash_report_text"]("Stash", report),
            lambda: commands["get_stash_text"](root, stash_arg),
        )
    if args.check_git_stash_apply is not None:
        return local_text_or_report(
            args,
            "checkGitStashApply",
            lambda: commands["get_check_stash_apply_report"](root, args.check_git_stash_apply),
            lambda report: commands["format_git_stash_apply_report_text"]("Check stash apply", report),
            lambda: commands["get_check_stash_apply_text"](root, args.check_git_stash_apply),
        )
    if args.git_stash_apply is not None:
        return local_text_or_report(
            args,
            "gitStashApply",
            lambda: commands["get_stash_apply_report"](root, args.git_stash_apply),
            lambda report: commands["format_git_stash_apply_report_text"]("Stash apply", report),
            lambda: commands["get_stash_apply_text"](root, args.git_stash_apply),
        )
    if args.check_git_stash_drop is not None:
        return local_text_or_report(
            args,
            "checkGitStashDrop",
            lambda: commands["get_check_stash_drop_report"](root, args.check_git_stash_drop),
            lambda report: commands["format_git_stash_drop_report_text"]("Check stash drop", report),
            lambda: commands["get_check_stash_drop_text"](root, args.check_git_stash_drop),
        )
    if args.git_stash_drop is not None:
        return local_text_or_report(
            args,
            "gitStashDrop",
            lambda: commands["get_stash_drop_report"](root, args.git_stash_drop),
            lambda report: commands["format_git_stash_drop_report_text"]("Stash drop", report),
            lambda: commands["get_stash_drop_text"](root, args.git_stash_drop),
        )
    return None
