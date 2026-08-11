from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .cli_local_result import local_text_or_report
from .session_input import normalize_optional_run_id


def normalize_session_search_query(value: str) -> str:
    return value.strip()


def run_session_summary_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    commands: dict[str, Any],
) -> tuple[str, dict[str, object]] | None:
    root = project_root or "."
    if args.sessions:
        return local_text_or_report(
            args,
            "sessions",
            lambda: commands["get_sessions_report"](root),
            commands["format_sessions_report_text"],
            lambda: commands["get_sessions_text"](root),
        )
    if args.last:
        return local_text_or_report(
            args,
            "sessionSummary",
            lambda: commands["get_last_session_report"](root),
            commands["format_session_summary_report_text"],
            lambda: commands["get_last_session_text"](root),
        )
    if args.session is not None:
        run_id = normalize_optional_run_id(args.session)
        return local_text_or_report(
            args,
            "sessionSummary",
            lambda: commands["get_session_report"](run_id, root),
            commands["format_session_summary_report_text"],
            lambda: commands["get_session_text"](run_id, root),
        )
    if args.session_inspect is not None:
        run_id = normalize_optional_run_id(args.session_inspect)
        return local_text_or_report(
            args,
            "sessionInspect",
            lambda: commands["get_session_inspect_report"](root, run_id),
            commands["format_session_inspect_report_text"],
            lambda: commands["format_session_inspect_report_text"](
                commands["get_session_inspect_report"](root, run_id)
            ),
        )
    if args.session_tasks is not None:
        run_id = normalize_optional_run_id(args.session_tasks)
        return local_text_or_report(
            args,
            "sessionTasks",
            lambda: commands["get_session_tasks_report"](root, run_id),
            commands["format_session_tasks_report_text"],
            lambda: commands["get_session_tasks_text"](root, run_id),
        )
    if args.plan is not None:
        run_id = normalize_optional_run_id(args.plan)
        return local_text_or_report(
            args,
            "sessionPlan",
            lambda: commands["get_plan_report"](root, run_id),
            commands["format_session_plan_report_text"],
            lambda: commands["get_plan_text"](root, run_id),
        )
    if args.transcript is not None:
        session_kwargs = commands["session_transcript_kwargs"](args)
        run_id = normalize_optional_run_id(args.transcript)
        return local_text_or_report(
            args,
            "sessionTranscript",
            lambda: commands["get_transcript_report"](root, run_id, **session_kwargs),
            commands["format_session_transcript_report_text"],
            lambda: commands["get_transcript_text"](root, run_id, **session_kwargs),
        )
    if args.session_search is not None:
        session_kwargs = commands["session_search_kwargs"](args)
        query = normalize_session_search_query(args.session_search)
        run_id = normalize_optional_run_id(args.session_search_run)
        return local_text_or_report(
            args,
            "sessionSearch",
            lambda: commands["get_session_search_report"](root, query, run_id, **session_kwargs),
            commands["format_session_search_report_text"],
            lambda: commands["get_session_search_text"](root, query, run_id, **session_kwargs),
        )
    return None
