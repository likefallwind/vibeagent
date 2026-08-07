from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report


def run_git_remote_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.check_git_fetch is not None:
        return local_text_or_report(
            args,
            "checkGitFetch",
            lambda: commands["get_check_fetch_report"](root, args.check_git_fetch),
            lambda report: commands["format_git_fetch_report_text"]("Check fetch", report),
            lambda: commands["get_check_fetch_text"](root, args.check_git_fetch),
        )
    if args.git_fetch is not None:
        return local_text_or_report(
            args,
            "gitFetch",
            lambda: commands["get_fetch_report"](root, args.git_fetch),
            lambda report: commands["format_git_fetch_report_text"]("Fetch", report),
            lambda: commands["get_fetch_text"](root, args.git_fetch),
        )
    if args.check_git_pull:
        return local_text_or_report(
            args,
            "checkGitPull",
            lambda: commands["get_check_pull_report"](root),
            lambda report: commands["format_git_sync_preview_report_text"]("Check pull", report),
            lambda: commands["get_check_pull_text"](root),
        )
    if args.git_pull:
        return local_text_or_report(
            args,
            "gitPull",
            lambda: commands["get_pull_report"](root),
            lambda report: commands["format_git_pull_report_text"]("Pull", report),
            lambda: commands["get_pull_text"](root),
        )
    if args.check_git_push:
        return local_text_or_report(
            args,
            "checkGitPush",
            lambda: commands["get_check_push_report"](root),
            lambda report: commands["format_git_sync_preview_report_text"]("Check push", report),
            lambda: commands["get_check_push_text"](root),
        )
    if args.git_push:
        return local_text_or_report(
            args,
            "gitPush",
            lambda: commands["get_push_report"](root),
            lambda report: commands["format_git_push_report_text"]("Push", report),
            lambda: commands["get_push_text"](root),
        )
    if args.check_git_switch is not None:
        switch_arg = commands["build_switch_argument"](args.check_git_switch, args.git_switch_create)
        return local_text_or_report(
            args,
            "checkGitSwitch",
            lambda: commands["get_check_switch_report"](root, switch_arg),
            lambda report: commands["format_git_switch_report_text"]("Check switch", report),
            lambda: commands["get_check_switch_text"](root, switch_arg),
        )
    if args.git_switch is not None:
        switch_arg = commands["build_switch_argument"](args.git_switch, args.git_switch_create)
        return local_text_or_report(
            args,
            "gitSwitch",
            lambda: commands["get_switch_report"](root, switch_arg),
            lambda report: commands["format_git_switch_report_text"]("Switch", report),
            lambda: commands["get_switch_text"](root, switch_arg),
        )
    return None
