from __future__ import annotations

from pathlib import Path
import shlex

from .session import (
    build_session_plan_report,
    build_session_search_report,
    build_session_summary_report,
    build_session_transcript_report,
    get_last_session_id,
    summarize_session,
)
from .session_input import normalize_optional_run_id

SESSION_USAGE = "Usage: /session <run-id>"
SESSION_SEARCH_USAGE = "Usage: /session-search [--run run-id] <query>"


def _clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    if max_length <= 3:
        return compacted[:max_length]
    return compacted[: max_length - 3] + "..."


def get_session_text(run_id: str | None, project_root: str | Path = ".") -> str:
    return format_session_summary_report_text(get_session_report(run_id, project_root))


def get_session_report(run_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    selected = normalize_optional_run_id(run_id)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": SESSION_USAGE,
        }
    try:
        return build_session_summary_report(summarize_session(project_root, selected))
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_summary_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        return str(report.get("message") or f"Session not found: {session}")

    events = report.get("events") if isinstance(report.get("events"), dict) else {}
    tool_calls = report.get("toolCalls") if isinstance(report.get("toolCalls"), dict) else {}
    approvals = report.get("approvals") if isinstance(report.get("approvals"), dict) else {}
    tokens = report.get("tokens") if isinstance(report.get("tokens"), dict) else {}
    plan = report.get("plan") if isinstance(report.get("plan"), dict) else {}
    final_review = report.get("finalReview") if isinstance(report.get("finalReview"), dict) else {}
    completion = report.get("completion") if isinstance(report.get("completion"), dict) else {}
    verification = report.get("verification") if isinstance(report.get("verification"), dict) else {}
    checkpoints = report.get("checkpoints") if isinstance(report.get("checkpoints"), dict) else {}
    model_errors = report.get("modelErrors") if isinstance(report.get("modelErrors"), dict) else {}
    background_processes = report.get("backgroundProcesses") if isinstance(report.get("backgroundProcesses"), dict) else {}
    tool_names = [str(item) for item in tool_calls.get("names", [])] if isinstance(tool_calls.get("names"), list) else []
    tools = ", ".join(_format_name_counts(tool_names)) if tool_names else "none"
    input_tokens = int(tokens.get("input", 0) or 0)
    output_tokens = int(tokens.get("output", 0) or 0)
    total_tokens = int(tokens.get("total", 0) or 0)
    cache_creation = int(tokens.get("cacheCreation", 0) or 0)
    cache_read = int(tokens.get("cacheRead", 0) or 0)
    lines = [
        f"Session: {session}",
        f"  status: {report.get('status') or 'unknown'}",
        f"  events: {int(events.get('total', 0) or 0)}",
        f"  iterations: {int(events.get('iterations', 0) or 0)}",
        f"  tools: {tools}",
        (
            "  approvals: "
            f"{int(approvals.get('requested', 0) or 0)} requested, "
            f"{int(approvals.get('approved', 0) or 0)} approved, "
            f"{int(approvals.get('denied', 0) or 0)} denied"
        ),
    ]
    if input_tokens or output_tokens or total_tokens:
        lines.append(f"  tokens: {input_tokens} input, {output_tokens} output, {total_tokens} total")
    if cache_creation or cache_read:
        lines.append(f"  cacheTokens: {cache_creation} created, {cache_read} read")
    malformed = int(events.get("malformed", 0) or 0)
    if malformed:
        lines.append(f"  malformedRows: {malformed}")
    model_error_total = int(model_errors.get("total", 0) or 0)
    if model_error_total:
        error_line = f"  modelErrors: {model_error_total}"
        latest_error = model_errors.get("latest")
        if latest_error:
            error_line += f", latest={_clip(str(latest_error), 180)}"
        lines.append(error_line)
    started_processes = int(background_processes.get("started", 0) or 0)
    active_processes = background_processes.get("active") if isinstance(background_processes.get("active"), list) else []
    if started_processes or active_processes:
        lines.append(f"  backgroundProcesses: started={started_processes}, active={len(active_processes)}")
    if report.get("task"):
        lines.append(f"  task: {_clip(str(report.get('task')), 240)}")
    created_checkpoints = int(checkpoints.get("created", 0) or 0)
    if created_checkpoints:
        checkpoint_line = (
            "  checkpoints: "
            f"created={created_checkpoints}, "
            f"auto={int(checkpoints.get('autoCreated', 0) or 0)}"
        )
        if checkpoints.get("latestId"):
            checkpoint_line += f", latest={_clip(str(checkpoints.get('latestId')), 80)}"
        if checkpoints.get("latestMessage"):
            checkpoint_line += f", message={_clip(str(checkpoints.get('latestMessage')), 160)}"
        lines.append(checkpoint_line)
    plan_items = [item for item in plan.get("items", []) if isinstance(item, dict)] if isinstance(plan.get("items"), list) else []
    if plan_items:
        lines.append("  plan:")
        lines.extend(f"    - {item.get('status')}: {_clip(str(item.get('step') or ''), 160)}" for item in plan_items)
    if bool(final_review.get("seen")):
        ready_value = final_review.get("ready")
        ready = "yes" if ready_value is True else "no" if ready_value is False else "unknown"
        final_review_line = (
            f"  finalReview: ready={ready}, "
            f"blocking={int(final_review.get('blockingIssues', 0) or 0)}, "
            f"warnings={int(final_review.get('warnings', 0) or 0)}, "
            f"files={int(final_review.get('files', 0) or 0)}, "
            f"suggestedChecks={int(final_review.get('suggestedChecks', 0) or 0)}"
        )
        if final_review.get("message"):
            final_review_line += f", message={_clip(str(final_review.get('message')), 160)}"
        lines.append(final_review_line)
        lines.extend(_format_final_review_changed_file_lines(final_review, indent="  ", max_text=160))
        lines.extend(_format_session_report_failure_lines(final_review, indent="  ", max_text=160))
    if completion.get("ready") is not None:
        ready = "yes" if completion.get("ready") is True else "no"
        blockers = completion.get("blockers") if isinstance(completion.get("blockers"), list) else []
        warnings = completion.get("warnings") if isinstance(completion.get("warnings"), list) else []
        lines.append(
            f"  completion: ready={ready}, "
            f"blockers={len(blockers)}, "
            f"warnings={len(warnings)}, "
            f"blockedAttempts={int(completion.get('blockedCount', 0) or 0)}"
        )
        lines.extend(f"    blocker: {_clip(str(item), 160)}" for item in blockers[:10])
        _append_completion_detail_lines(lines, completion, indent="    ", max_text=160)
        lines.extend(f"    warning: {_clip(str(item), 160)}" for item in warnings[:10])
    verified = [str(item) for item in verification.get("verified", [])] if isinstance(verification.get("verified"), list) else []
    pending = [str(item) for item in verification.get("pending", [])] if isinstance(verification.get("pending"), list) else []
    failed = [str(item) for item in verification.get("failed", [])] if isinstance(verification.get("failed"), list) else []
    if verified or pending or failed:
        lines.append("  verification:")
        lines.append(f"    verified: {len(verified)}")
        lines.extend(f"      - {_clip(item, 160)}" for item in verified[:10])
        lines.append(f"    pending: {len(pending)}")
        lines.extend(f"      - {_clip(item, 160)}" for item in pending[:10])
        lines.append(f"    failed: {len(failed)}")
        lines.extend(f"      - {_clip(item, 160)}" for item in failed[:10])
    if report.get("finalMessage"):
        lines.append(f"  final: {_clip(str(report.get('finalMessage')), 500)}")
    return "\n".join(lines)


def _format_name_counts(values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return [f"{name} x{count}" if count > 1 else name for name, count in counts.items()]


def _format_session_report_failure_lines(report: dict[str, object], indent: str = "  ", max_text: int = 160) -> list[str]:
    python_failures = report.get("pythonFailures") if isinstance(report.get("pythonFailures"), list) else []
    config_failures = report.get("configFailures") if isinstance(report.get("configFailures"), list) else []
    failures = [
        ("python", item)
        for item in python_failures
        if isinstance(item, str)
    ] + [
        ("config", item)
        for item in config_failures
        if isinstance(item, str)
    ]
    if not failures:
        return []
    lines = [f"{indent}finalReviewFailures:"]
    lines.extend(f"{indent}  - {kind}: {_clip(item, max_text)}" for kind, item in failures[:20])
    if len(failures) > 20:
        lines.append(f"{indent}  - ... {len(failures) - 20} more")
    return lines


def _format_final_review_changed_file_lines(report: dict[str, object], indent: str = "  ", max_text: int = 160) -> list[str]:
    changed_files = report.get("changedFiles") if isinstance(report.get("changedFiles"), list) else []
    labels = [item for item in changed_files if isinstance(item, str) and item.strip()]
    if not labels:
        return []
    lines = [f"{indent}finalReviewChangedFiles:"]
    lines.extend(f"{indent}  - {_clip(item, max_text)}" for item in labels[:20])
    if len(labels) > 20:
        lines.append(f"{indent}  - ... {len(labels) - 20} more")
    return lines


def _append_completion_detail_lines(
    lines: list[str],
    completion: dict[str, object],
    indent: str = "    ",
    max_text: int = 160,
) -> None:
    fields = (
        ("latestPendingVerificationChecks", "latestCompletionPendingChecks"),
        ("latestFailedVerificationChecks", "latestCompletionFailedChecks"),
        ("latestFinalReviewBlockingIssues", "latestCompletionFinalReviewIssues"),
        ("latestFinalReviewChangedFiles", "latestCompletionFinalReviewChangedFiles"),
        ("latestToolErrors", "latestCompletionToolErrors"),
        ("latestCheckpointFailures", "latestCompletionCheckpointFailures"),
        ("latestActiveBackgroundProcesses", "latestCompletionActiveProcesses"),
        ("latestDeniedApprovals", "latestCompletionDeniedApprovals"),
    )
    for key, label in fields:
        values = completion.get(key)
        items = [item for item in values if isinstance(item, str) and item.strip()] if isinstance(values, list) else []
        _append_limited_bullets(lines, label, items, indent=indent, max_text=max_text, limit=10)


def _append_limited_bullets(
    lines: list[str],
    label: str,
    items: list[str],
    *,
    indent: str,
    max_text: int,
    limit: int,
) -> None:
    if not items:
        return
    lines.append(f"{indent}{label}:")
    lines.extend(f"{indent}  - {_clip(item, max_text)}" for item in items[:limit])
    if len(items) > limit:
        lines.append(f"{indent}  - ... {len(items) - limit} more")


def get_last_session_text(project_root: str | Path = ".") -> str:
    return format_session_summary_report_text(get_last_session_report(project_root))


def get_last_session_report(project_root: str | Path = ".") -> dict[str, object]:
    run_id = get_last_session_id(project_root)
    if not run_id:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    return build_session_summary_report(summarize_session(project_root, run_id))


def get_plan_text(project_root: str | Path = ".", run_id: str | None = None) -> str:
    return format_session_plan_report_text(get_plan_report(project_root, run_id))


def get_plan_report(project_root: str | Path = ".", run_id: str | None = None) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_plan_report(summarize_session(project_root, selected))
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_plan_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    lines = [
        "Plan:",
        f"  session: {session}",
        f"  status: {report.get('status') or 'unknown'}",
    ]
    if report.get("task"):
        lines.append(f"  task: {_clip(str(report.get('task')), 240)}")
    items = [item for item in report.get("items", []) if isinstance(item, dict)] if isinstance(report.get("items"), list) else []
    if items:
        lines.append("  items:")
        lines.extend(f"    - {item.get('status')}: {_clip(str(item.get('step') or ''), 200)}" for item in items)
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def get_transcript_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> str:
    return format_session_transcript_report_text(get_transcript_report(project_root, run_id, max_events=max_events, max_text=max_text))


def get_transcript_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_events: int = 80,
    max_text: int = 500,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id) or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_transcript_report(project_root, selected, max_events=max_events, max_text=max_text)
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_transcript_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    events = report.get("events") if isinstance(report.get("events"), dict) else {}
    total = int(events.get("total", 0) or 0)
    shown = int(events.get("shown", 0) or 0)
    omitted = int(events.get("omitted", 0) or 0)
    lines = [
        "Transcript:",
        f"  session: {session}",
        f"  events: {total}",
        f"  shown: {shown}/{total}",
        f"  truncated: {'yes' if bool(events.get('truncated')) else 'no'}",
    ]
    malformed = int(events.get("malformed", 0) or 0)
    if malformed:
        lines.append(f"  malformedRows: {malformed}")
    lines.append("  timeline:")
    if omitted > 0:
        lines.append(f"    - [{omitted} older event(s) omitted]")
    items = [item for item in events.get("items", []) if isinstance(item, dict)] if isinstance(events.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    lines.extend(str(item.get("summary") or "    - unknown") for item in items)
    return "\n".join(lines)


def get_session_search_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    run_id: str | None = None,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> str:
    return format_session_search_report_text(
        get_session_search_report(
            project_root,
            argument,
            run_id,
            max_matches=max_matches,
            max_text=max_text,
            case_sensitive=case_sensitive,
        )
    )


def get_session_search_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    run_id: str | None = None,
    max_matches: int = 20,
    max_text: int = 500,
    case_sensitive: bool = False,
) -> dict[str, object]:
    selected = normalize_optional_run_id(run_id)
    if not argument or not argument.strip():
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": SESSION_SEARCH_USAGE,
        }
    query = argument.strip()
    if selected is None:
        try:
            parts = shlex.split(argument)
        except ValueError as error:
            return {
                "session": None,
                "exists": False,
                "ok": False,
                "status": "invalid",
                "message": str(error),
            }
        if len(parts) >= 3 and parts[0] == "--run":
            selected = normalize_optional_run_id(parts[1])
            query = " ".join(parts[2:]).strip()
        else:
            query = argument.strip()
    selected = selected or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "query": query,
            "caseSensitive": case_sensitive,
            "message": "No sessions found.",
        }
    try:
        return build_session_search_report(
            project_root,
            selected,
            query,
            max_matches=max_matches,
            max_text=max_text,
            case_sensitive=case_sensitive,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "query": query,
            "caseSensitive": case_sensitive,
            "message": str(error),
        }


def format_session_search_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    matches = report.get("matches") if isinstance(report.get("matches"), dict) else {}
    total = int(matches.get("total", 0) or 0)
    shown = int(matches.get("shown", 0) or 0)
    omitted = int(matches.get("omitted", 0) or 0)
    lines = [
        "Session search:",
        f"  session: {session}",
        f"  query: {report.get('query') or ''}",
        f"  matches: {total}",
        f"  shown: {shown}/{total}",
        f"  caseSensitive: {'yes' if bool(report.get('caseSensitive')) else 'no'}",
        "  timeline:",
    ]
    items = [item for item in matches.get("items", []) if isinstance(item, dict)] if isinstance(matches.get("items"), list) else []
    if items:
        lines.extend(str(item.get("summary") or "    - unknown") for item in items)
    else:
        lines.append("    - none")
    if omitted > 0:
        lines.append(f"    - [{omitted} later match(es) omitted]")
    return "\n".join(lines)
