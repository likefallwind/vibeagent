from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_optional_nonnegative_int,
    parse_optional_positive_int,
)
from .action_parsing_session_fields import parse_min_text, parse_run_id
from .action_parsing_session_output import SESSION_OUTPUT_ACTION_TYPES, parse_session_output_action
from .types import (
    SessionAuditAction,
    SessionFailuresAction,
    SessionFilesAction,
    SessionHandoffAction,
    SessionPlanAction,
    RunSessionVerificationAction,
    SessionSearchAction,
    SessionSummaryAction,
    SessionTranscriptAction,
    SessionVerificationAction,
)


SESSION_ACTION_TYPES = SESSION_OUTPUT_ACTION_TYPES | {
    "todo_read",
    "session_summary",
    "session_plan",
    "session_transcript",
    "session_search",
    "session_files",
    "session_failures",
    "session_verification",
    "run_session_verification",
    "session_audit",
    "session_handoff",
}


def parse_session_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in SESSION_ACTION_TYPES:
        return None

    output_action = parse_session_output_action(action_type, value, raw)
    if output_action is not None:
        return output_action

    if action_type == "session_summary":
        run_id = parse_run_id(value.get("run_id"), raw, "session_summary")
        recent_limit = parse_optional_positive_int(value.get("recent_limit", 5), "recent_limit", raw, maximum=20) or 5
        return SessionSummaryAction(type="session_summary", run_id=run_id, recent_limit=recent_limit)

    if action_type in {"session_plan", "todo_read"}:
        run_id = parse_run_id(value.get("run_id"), raw, str(action_type))
        return SessionPlanAction(type="session_plan", run_id=run_id)

    if action_type == "session_transcript":
        run_id = parse_run_id(value.get("run_id"), raw, "session_transcript")
        max_events = parse_optional_positive_int(value.get("max_events", 80), "max_events", raw, maximum=500) or 80
        max_text = parse_min_text(value.get("max_text", 500), raw, default=500)
        return SessionTranscriptAction(
            type="session_transcript",
            run_id=run_id,
            max_events=max_events,
            max_text=max_text,
        )

    if action_type == "session_search":
        query = value.get("query")
        run_id = parse_run_id(value.get("run_id"), raw, "session_search")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("session_search action query must be a non-empty string.", raw)
        normalized_query = query.strip()
        max_matches = parse_optional_positive_int(value.get("max_matches", 20), "max_matches", raw, maximum=100) or 20
        max_text = parse_min_text(value.get("max_text", 500), raw, default=500)
        case_sensitive = value.get("case_sensitive", False)
        if not isinstance(case_sensitive, bool):
            raise ActionParseError("session_search action case_sensitive must be a boolean.", raw)
        return SessionSearchAction(
            type="session_search",
            query=normalized_query,
            run_id=run_id,
            max_matches=max_matches,
            max_text=max_text,
            case_sensitive=case_sensitive,
        )

    if action_type == "session_files":
        run_id = parse_run_id(value.get("run_id"), raw, "session_files")
        max_files = parse_optional_positive_int(value.get("max_files", 100), "max_files", raw, maximum=500) or 100
        return SessionFilesAction(type="session_files", run_id=run_id, max_files=max_files)

    if action_type == "session_failures":
        run_id = parse_run_id(value.get("run_id"), raw, "session_failures")
        max_failures = parse_optional_positive_int(value.get("max_failures", 50), "max_failures", raw, maximum=200) or 50
        max_text = parse_min_text(value.get("max_text", 500), raw, default=500)
        return SessionFailuresAction(
            type="session_failures",
            run_id=run_id,
            max_failures=max_failures,
            max_text=max_text,
        )

    if action_type == "session_verification":
        run_id = parse_run_id(value.get("run_id"), raw, "session_verification")
        max_checks = parse_optional_positive_int(value.get("max_checks", 50), "max_checks", raw, maximum=500) or 50
        return SessionVerificationAction(type="session_verification", run_id=run_id, max_checks=max_checks)

    if action_type == "run_session_verification":
        run_id = parse_run_id(value.get("run_id"), raw, "run_session_verification")
        max_checks = parse_optional_positive_int(value.get("max_checks", 10), "max_checks", raw, maximum=10) or 10
        timeout_ms = parse_optional_positive_int(value.get("timeout_ms", 30_000), "timeout_ms", raw, maximum=600_000) or 30_000
        if timeout_ms < 100:
            raise ActionParseError("timeout_ms must be at least 100.", raw)
        max_output_chars = parse_optional_positive_int(value.get("max_output_chars", 12_000), "max_output_chars", raw, maximum=50_000) or 12_000
        if max_output_chars < 1_000:
            raise ActionParseError("max_output_chars must be at least 1000.", raw)
        context_lines = parse_optional_nonnegative_int(value.get("context_lines", 5), "context_lines", raw, maximum=50)
        context_lines = 5 if context_lines is None else context_lines
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=500) or 50
        max_contexts = parse_optional_positive_int(value.get("max_contexts", 20), "max_contexts", raw, maximum=200) or 20
        max_bytes_per_context = parse_optional_positive_int(value.get("max_bytes_per_context", 20_000), "max_bytes_per_context", raw, maximum=200_000) or 20_000
        include_pending = value.get("include_pending", True)
        include_failed = value.get("include_failed", True)
        stop_on_failure = value.get("stop_on_failure", True)
        extract_output_contexts = value.get("extract_output_contexts", False)
        extract_output_diagnostics = value.get("extract_output_diagnostics", False)
        if not isinstance(include_pending, bool):
            raise ActionParseError("run_session_verification action include_pending must be a boolean.", raw)
        if not isinstance(include_failed, bool):
            raise ActionParseError("run_session_verification action include_failed must be a boolean.", raw)
        if not include_pending and not include_failed:
            raise ActionParseError("run_session_verification action must include pending or failed checks.", raw)
        if not isinstance(stop_on_failure, bool):
            raise ActionParseError("run_session_verification action stop_on_failure must be a boolean.", raw)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError("run_session_verification action extract_output_contexts must be a boolean.", raw)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError("run_session_verification action extract_output_diagnostics must be a boolean.", raw)
        return RunSessionVerificationAction(
            type="run_session_verification",
            run_id=run_id,
            max_checks=max_checks,
            include_pending=include_pending,
            include_failed=include_failed,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "session_audit":
        run_id = parse_run_id(value.get("run_id"), raw, "session_audit")
        max_failures = parse_optional_positive_int(value.get("max_failures", 10), "max_failures", raw, maximum=200) or 10
        max_files = parse_optional_positive_int(value.get("max_files", 20), "max_files", raw, maximum=500) or 20
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=100) or 10
        max_checks = parse_optional_positive_int(value.get("max_checks", 50), "max_checks", raw, maximum=500) or 50
        max_text = parse_min_text(value.get("max_text", 300), raw, default=300)
        return SessionAuditAction(
            type="session_audit",
            run_id=run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )

    if action_type == "session_handoff":
        run_id = parse_run_id(value.get("run_id"), raw, "session_handoff")
        max_failures = parse_optional_positive_int(value.get("max_failures", 20), "max_failures", raw, maximum=200) or 20
        max_files = parse_optional_positive_int(value.get("max_files", 50), "max_files", raw, maximum=500) or 50
        max_commands = parse_optional_positive_int(value.get("max_commands", 10), "max_commands", raw, maximum=100) or 10
        max_checks = parse_optional_positive_int(value.get("max_checks", 50), "max_checks", raw, maximum=500) or 50
        max_output_chars = value.get("max_output_chars", 1_000)
        if not isinstance(max_output_chars, int):
            raise ActionParseError("max_output_chars must be an integer.", raw)
        if max_output_chars < 0:
            raise ActionParseError("max_output_chars must be at least 0.", raw)
        if max_output_chars > 20_000:
            raise ActionParseError("max_output_chars must be at most 20000.", raw)
        max_text = parse_min_text(value.get("max_text", 500), raw, default=500)
        return SessionHandoffAction(
            type="session_handoff",
            run_id=run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )

    raise AssertionError(f"Unhandled session action type: {action_type!r}")
