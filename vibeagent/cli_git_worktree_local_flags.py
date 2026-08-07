from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def run_git_worktree_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.check_git_stage is not None:
        return local_text_or_report(
            args,
            "checkGitStage",
            lambda: commands["get_check_stage_report"](root, args.check_git_stage),
            lambda report: commands["format_git_index_report_text"]("Check stage", report),
            lambda: commands["get_check_stage_text"](root, args.check_git_stage),
        )
    if args.git_stage is not None:
        return local_text_or_report(
            args,
            "gitStage",
            lambda: commands["get_stage_report"](root, args.git_stage),
            lambda report: commands["format_git_index_report_text"]("Stage", report),
            lambda: commands["get_stage_text"](root, args.git_stage),
        )
    if args.check_git_unstage is not None:
        return local_text_or_report(
            args,
            "checkGitUnstage",
            lambda: commands["get_check_unstage_report"](root, args.check_git_unstage),
            lambda report: commands["format_git_index_report_text"]("Check unstage", report),
            lambda: commands["get_check_unstage_text"](root, args.check_git_unstage),
        )
    if args.git_unstage is not None:
        return local_text_or_report(
            args,
            "gitUnstage",
            lambda: commands["get_unstage_report"](root, args.git_unstage),
            lambda report: commands["format_git_index_report_text"]("Unstage", report),
            lambda: commands["get_unstage_text"](root, args.git_unstage),
        )
    if args.check_git_commit is not None:
        return local_text_or_report(
            args,
            "checkGitCommit",
            lambda: commands["get_check_commit_report"](root, args.check_git_commit),
            lambda report: commands["format_git_commit_report_text"]("Check commit", report),
            lambda: commands["get_check_commit_text"](root, args.check_git_commit),
        )
    if args.git_commit is not None:
        return local_text_or_report(
            args,
            "gitCommit",
            lambda: commands["get_commit_report"](root, args.git_commit),
            lambda report: commands["format_git_commit_report_text"]("Commit", report),
            lambda: commands["get_commit_text"](root, args.git_commit),
        )
    if args.check_git_restore is not None:
        return local_text_or_report(
            args,
            "checkGitRestore",
            lambda: commands["get_check_restore_report"](root, args.check_git_restore),
            lambda report: commands["format_git_restore_report_text"]("Check restore", report),
            lambda: commands["get_check_restore_text"](root, args.check_git_restore),
        )
    if args.git_restore is not None:
        return local_text_or_report(
            args,
            "gitRestore",
            lambda: commands["get_restore_report"](root, args.git_restore),
            lambda report: commands["format_git_restore_report_text"]("Restore", report),
            lambda: commands["get_restore_text"](root, args.git_restore),
        )
    return None
