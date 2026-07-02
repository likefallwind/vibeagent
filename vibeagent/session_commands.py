from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .config import resolve_cost_rates
from .session import build_cost_report, build_session_audit_report, build_session_commands_report, build_session_failures_report, build_session_files_report, build_session_handoff_report, build_session_plan_report, build_session_resume_context, build_session_search_report, build_session_summary_report, build_session_transcript_report, build_session_verification_report, build_sessions_report, build_usage_report, get_last_session_id, summarize_session
from .types import SessionOutputContextsAction, SessionOutputDiagnosticsAction
from .workspace_core import RunWorkspace


def _clip(value: str, max_length: int) -> str:
    compacted = value.strip()
    if len(compacted) <= max_length:
        return compacted
    if max_length <= 3:
        return compacted[:max_length]
    return compacted[: max_length - 3] + "..."


def _indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())


def get_sessions_text(project_root: str | Path = ".") -> str:
    return format_sessions_report_text(get_sessions_report(project_root))


def get_sessions_report(project_root: str | Path = ".") -> dict[str, object]:
    return build_sessions_report(project_root)


def format_sessions_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("exists")):
        return str(report.get("message") or "No sessions found.")
    sessions = report.get("sessions") if isinstance(report.get("sessions"), dict) else {}
    items = [item for item in sessions.get("items", []) if isinstance(item, dict)] if isinstance(sessions.get("items"), list) else []
    if not items:
        return str(report.get("message") or "No sessions found.")
    lines = ["Recent sessions:"]
    for item in items:
        malformed = f", {item.get('malformed')} malformed" if int(item.get("malformed", 0) or 0) else ""
        last = item.get("lastEventTime") or "unknown"
        task = f"  task={item.get('task')}" if item.get("task") else ""
        lines.append(
            f"  {item.get('session')}  status={item.get('status')}  "
            f"events={int(item.get('events', 0) or 0)}{malformed}  last={last}{task}"
        )
    return "\n".join(lines)


def get_usage_text(project_root: str | Path = ".") -> str:
    return format_usage_report_text(get_usage_report(project_root))


def get_usage_report(project_root: str | Path = ".") -> dict[str, object]:
    return build_usage_report(project_root)


def format_usage_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("exists")):
        return str(report.get("message") or "No sessions found.")
    usage = report.get("usage") if isinstance(report.get("usage"), dict) else {}
    approvals = usage.get("approvals") if isinstance(usage.get("approvals"), dict) else {}
    statuses = usage.get("statuses") if isinstance(usage.get("statuses"), dict) else {}
    tokens = usage.get("tokens") if isinstance(usage.get("tokens"), dict) else {}
    input_tokens = int(tokens.get("input", 0) or 0)
    output_tokens = int(tokens.get("output", 0) or 0)
    total_tokens = int(tokens.get("total", 0) or 0)
    cache_creation = int(tokens.get("cacheCreation", 0) or 0)
    cache_read = int(tokens.get("cacheRead", 0) or 0)
    lines = [
        "Usage:",
        f"  sessions: {int(usage.get('sessions', 0) or 0)}",
        f"  events: {int(usage.get('events', 0) or 0)}",
        f"  iterations: {int(usage.get('iterations', 0) or 0)}",
        f"  toolCalls: {int(usage.get('toolCalls', 0) or 0)}",
        (
            "  approvals: "
            f"{int(approvals.get('requested', 0) or 0)} requested, "
            f"{int(approvals.get('approved', 0) or 0)} approved, "
            f"{int(approvals.get('denied', 0) or 0)} denied"
        ),
        f"  completed: {int(statuses.get('completed', 0) or 0)}",
        f"  blocked: {int(statuses.get('blocked', 0) or 0)}",
        f"  incomplete: {int(statuses.get('incomplete', 0) or 0)}",
        f"  failed: {int(statuses.get('failed', 0) or 0)}",
    ]
    if input_tokens or output_tokens or total_tokens:
        lines.extend(
            [
                f"  inputTokens: {input_tokens}",
                f"  outputTokens: {output_tokens}",
                f"  totalTokens: {total_tokens}",
            ]
        )
    if cache_creation or cache_read:
        lines.append(f"  cacheTokens: {cache_creation} created, {cache_read} read")
    malformed_rows = int(usage.get("malformedRows", 0) or 0)
    if malformed_rows:
        lines.append(f"  malformedRows: {malformed_rows}")
    cost = report.get("cost") if isinstance(report.get("cost"), dict) else {}
    reason = str(cost.get("reason") or "provider token usage is not recorded")
    lines.append(f"  cost: unavailable; {reason}.")
    return "\n".join(lines)


def get_cost_text(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> str:
    return format_cost_report_text(get_cost_report(project_root, env))


def get_cost_report(project_root: str | Path = ".", env: dict[str, str | None] | None = None) -> dict[str, object]:
    rates, errors = resolve_cost_rates(env)
    return build_cost_report(project_root, rates, errors)


def format_cost_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("exists")):
        return str(report.get("message") or "No sessions found.")
    usage = report.get("usage") if isinstance(report.get("usage"), dict) else {}
    tokens = usage.get("tokens") if isinstance(usage.get("tokens"), dict) else {}
    input_tokens = int(tokens.get("input", 0) or 0)
    output_tokens = int(tokens.get("output", 0) or 0)
    total_tokens = int(tokens.get("total", 0) or 0)
    cache_creation = int(tokens.get("cacheCreation", 0) or 0)
    cache_read = int(tokens.get("cacheRead", 0) or 0)
    lines = [
        "Cost:",
        f"  sessions: {int(usage.get('sessions', 0) or 0)}",
        f"  inputTokens: {input_tokens}",
        f"  outputTokens: {output_tokens}",
        f"  totalTokens: {total_tokens}",
    ]
    if cache_creation or cache_read:
        lines.append(f"  cacheTokens: {cache_creation} created, {cache_read} read")
    errors = [str(error) for error in report.get("errors", [])] if isinstance(report.get("errors"), list) else []
    if errors:
        lines.extend(f"  error: {error}" for error in errors)
        return "\n".join(lines)
    estimate = report.get("estimate") if isinstance(report.get("estimate"), dict) else {}
    if not bool(estimate.get("available")):
        reason = str(estimate.get("reason") or "provider token usage is not recorded")
        missing = estimate.get("missingRates") if isinstance(estimate.get("missingRates"), list) else []
        if missing:
            lines.append(f"  estimate: unavailable; set {', '.join(str(item) for item in missing)}.")
        else:
            lines.append(f"  estimate: unavailable; {reason}.")
        return "\n".join(lines)
    formatted = estimate.get("formatted") if isinstance(estimate.get("formatted"), dict) else {}
    lines.extend(
        [
            f"  inputCostUsd: {formatted.get('inputCostUsd') or estimate.get('inputCostUsd')}",
            f"  outputCostUsd: {formatted.get('outputCostUsd') or estimate.get('outputCostUsd')}",
        ]
    )
    if cache_creation or cache_read:
        lines.append(f"  cacheCostUsd: {formatted.get('cacheCostUsd') or estimate.get('cacheCostUsd')}")
    lines.append(f"  estimatedCostUsd: {formatted.get('estimatedCostUsd') or estimate.get('estimatedCostUsd')}")
    return "\n".join(lines)


def get_session_text(run_id: str | None, project_root: str | Path = ".") -> str:
    return format_session_summary_report_text(get_session_report(run_id, project_root))


def get_session_report(run_id: str | None, project_root: str | Path = ".") -> dict[str, object]:
    if not run_id:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": "Usage: /session <run-id>",
        }
    try:
        return build_session_summary_report(summarize_session(project_root, run_id))
    except ValueError as error:
        return {
            "session": run_id,
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
        if not items:
            continue
        lines.append(f"{indent}{label}:")
        lines.extend(f"{indent}  - {_clip(item, max_text)}" for item in items[:10])
        if len(items) > 10:
            lines.append(f"{indent}  - ... {len(items) - 10} more")


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
    selected = run_id or get_last_session_id(project_root)
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
    selected = run_id or get_last_session_id(project_root)
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
    if not argument or not argument.strip():
        return {
            "session": run_id,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": "Usage: /session-search [--run run-id] <query>",
        }
    selected = run_id
    query = argument.strip()
    if run_id is None:
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
            selected = parts[1]
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


def get_session_commands_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> str:
    return format_session_commands_report_text(
        get_session_commands_report(
            project_root,
            run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )
    )


def get_session_commands_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 2_000,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_commands_report(
            project_root,
            selected,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_commands_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    total = int(commands.get("total", 0) or 0)
    shown = int(commands.get("shown", 0) or 0)
    omitted = int(commands.get("omitted", 0) or 0)
    lines = [
        "Command results:",
        f"  session: {session}",
        f"  commands: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older command result(s) omitted]")
    items = [item for item in commands.get("items", []) if isinstance(item, dict)] if isinstance(commands.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for item in items:
        parts = [
            f"exit={item.get('exitCode') if isinstance(item.get('exitCode'), int) else 'unknown'}",
            f"timedOut={'yes' if bool(item.get('timedOut')) else 'no'}",
        ]
        if item.get("signal"):
            parts.append(f"signal={item.get('signal')}")
        if item.get("cwd"):
            parts.append(f"cwd={item.get('cwd')}")
        line_number = item.get("lineNumber") if item.get("lineNumber") is not None else "?"
        kind = item.get("kind") or "command"
        index = item.get("index") if item.get("index") is not None else "?"
        lines.append(f"    - #{line_number} {kind}[{index}]: " + ", ".join(parts))
        lines.append(f"      command: {item.get('command') or 'unknown'}")
        for label, text_key, truncated_key in (
            ("stdout", "stdout", "stdoutStoredTruncated"),
            ("stderr", "stderr", "stderrStoredTruncated"),
        ):
            suffix = " (stored truncated)" if bool(item.get(truncated_key)) else ""
            lines.append(f"      {label}{suffix}:")
            text = item.get(text_key) if isinstance(item.get(text_key), str) else ""
            if not text:
                lines.append("        (empty)")
            else:
                lines.extend(f"        {line}" for line in text.splitlines())
    return "\n".join(lines)


def get_session_output_contexts_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_session_output_contexts_report_text(
        get_session_output_contexts_report(
            project_root,
            run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def get_session_output_contexts_observation(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
):
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-session-output-contexts", session_dir=root / ".vibeagent" / "sessions" / "local-session-output-contexts")
    return execute_action(
        workspace,
        SessionOutputContextsAction(
            type="session_output_contexts",
            run_id=selected,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )


def get_session_output_contexts_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 5,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    observation = get_session_output_contexts_observation(
        project_root,
        selected,
        max_commands=max_commands,
        max_output_chars=max_output_chars,
        context_lines=context_lines,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if observation is None:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    if observation.kind != "session_output_contexts":
        return {
            "session": selected,
            "exists": True,
            "ok": False,
            "status": "invalid",
            "message": f"Unexpected observation: {observation.kind}",
        }

    ok_contexts = sum(1 for item in observation.contexts if item.ok)
    exists = not observation.message.startswith("Session not found:")
    return {
        "session": observation.run_id,
        "exists": exists,
        "ok": observation.ok,
        "status": "ready" if observation.ok else ("failed" if exists else "missing"),
        "commands": {
            "total": observation.command_count,
            "shown": observation.shown_commands,
        },
        "contexts": {
            "total": len(observation.contexts),
            "ok": ok_contexts,
            "failed": len(observation.contexts) - ok_contexts,
            "totalRefs": observation.total_refs,
            "truncated": observation.truncated,
            "items": [serialize_output_context_result(item) for item in observation.contexts],
        },
        "message": observation.message,
    }


def format_session_output_contexts_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    items = [item for item in contexts.get("items", []) if isinstance(item, dict)] if isinstance(contexts.get("items"), list) else []
    lines = [
        "Session output contexts:",
        f"  session: {session}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  commands: {int(commands.get('shown', 0) or 0)}/{int(commands.get('total', 0) or 0)}",
        f"  contexts: {int(contexts.get('ok', 0) or 0)}/{int(contexts.get('total', 0) or 0)}",
        f"  totalRefs: {int(contexts.get('totalRefs', 0) or 0)}",
        f"  truncated: {'yes' if bool(contexts.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    for item in items:
        lines.extend(_format_output_context_item_text(item))
    return "\n".join(lines)


def _format_output_context_item_text(item: dict[str, object]) -> list[str]:
    column = f":{item.get('column')}" if item.get("column") is not None else ""
    total_lines = item.get("totalLines") if item.get("totalLines") is not None else "unknown"
    lines = [
        "",
        f"Context: {item.get('path') or ''}:{item.get('line')}{column}",
        f"  raw: {item.get('raw') or ''}",
        f"  ok: {'yes' if bool(item.get('ok')) else 'no'}",
        f"  range: {item.get('startLine')}:{item.get('endLine')}",
        f"  contextLines: {item.get('contextLines')}",
        f"  targetLineExists: {'yes' if bool(item.get('targetLineExists')) else 'no'}",
        f"  lines: {item.get('lineCount')}/{total_lines}",
        f"  maxBytes: {item.get('maxBytes')}",
        f"  truncated: {'yes' if bool(item.get('truncated')) else 'no'}",
        f"  message: {item.get('message') or ''}",
    ]
    content = item.get("content") if isinstance(item.get("content"), str) else ""
    if content:
        lines.append("  content:")
        lines.append(_indent_block(content.rstrip("\n"), spaces=4))
    else:
        lines.append("  content: none")
    return lines


def serialize_output_context_result(item) -> dict[str, object]:
    return {
        "path": item.path,
        "line": item.line,
        "column": item.column,
        "raw": item.raw,
        "ok": item.ok,
        "content": item.content,
        "message": item.message,
        "contextLines": item.context_lines,
        "startLine": item.start_line,
        "endLine": item.end_line,
        "lineCount": item.line_count,
        "totalLines": item.total_lines,
        "targetLineExists": item.target_line_exists,
        "truncated": item.truncated,
        "maxBytes": item.max_bytes,
    }


def get_session_output_diagnostics_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_session_output_diagnostics_report_text(
        get_session_output_diagnostics_report(
            project_root,
            run_id,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def format_session_output_diagnostics_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    contexts = report.get("contexts") if isinstance(report.get("contexts"), dict) else {}
    diagnostic_items = [item for item in diagnostics.get("items", []) if isinstance(item, dict)] if isinstance(diagnostics.get("items"), list) else []
    context_items = [item for item in contexts.get("items", []) if isinstance(item, dict)] if isinstance(contexts.get("items"), list) else []
    lines = [
        "Session output diagnostics:",
        f"  session: {session}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  commands: {int(commands.get('shown', 0) or 0)}/{int(commands.get('total', 0) or 0)}",
        f"  diagnostics: {int(diagnostics.get('shown', 0) or 0)}/{int(diagnostics.get('total', 0) or 0)}",
        f"  contexts: {int(contexts.get('ok', 0) or 0)}/{int(contexts.get('total', 0) or 0)}",
        f"  totalRefs: {int(contexts.get('totalRefs', 0) or 0)}",
        f"  diagnosticsTruncated: {'yes' if bool(diagnostics.get('truncated')) else 'no'}",
        f"  contextsTruncated: {'yes' if bool(contexts.get('truncated')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    for diagnostic in diagnostic_items:
        location = ""
        if diagnostic.get("path") and diagnostic.get("line") is not None:
            column = f":{diagnostic.get('column')}" if diagnostic.get("column") is not None else ""
            location = f" {diagnostic.get('path')}:{diagnostic.get('line')}{column}"
        lines.append(
            f"  - {diagnostic.get('severity')} outputLine={diagnostic.get('outputLine')}{location}: {diagnostic.get('text') or ''}"
        )
    for item in context_items:
        lines.extend(_format_output_context_item_text(item))
    return "\n".join(lines)


def get_session_output_diagnostics_observation(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
):
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-session-output-diagnostics", session_dir=root / ".vibeagent" / "sessions" / "local-session-output-diagnostics")
    return execute_action(
        workspace,
        SessionOutputDiagnosticsAction(
            type="session_output_diagnostics",
            run_id=selected,
            max_commands=max_commands,
            max_output_chars=max_output_chars,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )


def get_session_output_diagnostics_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_commands: int = 20,
    max_output_chars: int = 20_000,
    context_lines: int = 2,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    observation = get_session_output_diagnostics_observation(
        project_root,
        selected,
        max_commands=max_commands,
        max_output_chars=max_output_chars,
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
    )
    if observation is None:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    if observation.kind != "session_output_diagnostics":
        return {
            "session": selected,
            "exists": True,
            "ok": False,
            "status": "invalid",
            "message": f"Unexpected observation: {observation.kind}",
        }

    ok_contexts = sum(1 for item in observation.contexts if item.ok)
    exists = not observation.message.startswith("Session not found:")
    return {
        "session": observation.run_id,
        "exists": exists,
        "ok": observation.ok,
        "status": "ready" if observation.ok else ("failed" if exists else "missing"),
        "commands": {
            "total": observation.command_count,
            "shown": observation.shown_commands,
        },
        "diagnostics": {
            "total": observation.total_diagnostics,
            "shown": len(observation.diagnostics),
            "truncated": observation.diagnostics_truncated,
            "items": [serialize_output_diagnostic(item) for item in observation.diagnostics],
        },
        "contexts": {
            "total": len(observation.contexts),
            "ok": ok_contexts,
            "failed": len(observation.contexts) - ok_contexts,
            "totalRefs": observation.total_refs,
            "truncated": observation.contexts_truncated,
            "items": [serialize_output_context_result(item) for item in observation.contexts],
        },
        "message": observation.message,
    }


def serialize_output_diagnostic(item) -> dict[str, object]:
    return {
        "severity": item.severity,
        "outputLine": item.output_line,
        "text": item.text,
        "path": item.path,
        "line": item.line,
        "column": item.column,
        "raw": item.raw,
    }


def get_session_files_text(project_root: str | Path = ".", run_id: str | None = None, max_files: int = 100) -> str:
    return format_session_files_report_text(get_session_files_report(project_root, run_id, max_files=max_files))


def get_session_files_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_files: int = 100,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_files_report(project_root, selected, max_files=max_files)
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_files_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    total = int(files.get("total", 0) or 0)
    shown = int(files.get("shown", 0) or 0)
    omitted = int(files.get("omitted", 0) or 0)
    lines = [
        "Session files:",
        f"  session: {session}",
        f"  files: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    items = [item for item in files.get("items", []) if isinstance(item, dict)] if isinstance(files.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for item in items:
        tools = ", ".join(str(tool) for tool in item.get("tools", []) if isinstance(tool, str)) if isinstance(item.get("tools"), list) else ""
        uses = ", ".join(str(use) for use in item.get("uses", []) if isinstance(use, str)) if isinstance(item.get("uses"), list) else ""
        line_values = [line for line in item.get("lines", []) if isinstance(line, int)] if isinstance(item.get("lines"), list) else []
        line_numbers = ", ".join(f"#{line}" for line in line_values[:8])
        if len(line_values) > 8:
            line_numbers += f", +{len(line_values) - 8} more"
        lines.append(f"    - {item.get('path') or ''}")
        lines.append(f"      uses: {uses}")
        lines.append(f"      tools: {tools}")
        lines.append(f"      count: {int(item.get('count', 0) or 0)}")
        lines.append(f"      lines: {line_numbers}")
    if omitted > 0:
        lines.append(f"    - [{omitted} file(s) omitted]")
    return "\n".join(lines)


def get_session_failures_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 50,
    max_text: int = 500,
) -> str:
    return format_session_failures_report_text(
        get_session_failures_report(project_root, run_id, max_failures=max_failures, max_text=max_text)
    )


def get_session_failures_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 50,
    max_text: int = 500,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_failures_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_failures_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    failures = report.get("failures") if isinstance(report.get("failures"), dict) else {}
    total = int(failures.get("total", 0) or 0)
    shown = int(failures.get("shown", 0) or 0)
    omitted = int(failures.get("omitted", 0) or 0)
    lines = [
        "Session failures:",
        f"  session: {session}",
        f"  failures: {total}",
        f"  shown: {shown}/{total}",
        "  entries:",
    ]
    if omitted > 0:
        lines.append(f"    - [{omitted} older failure(s) omitted]")
    items = [item for item in failures.get("items", []) if isinstance(item, dict)] if isinstance(failures.get("items"), list) else []
    if not items:
        lines.append("    - none")
        return "\n".join(lines)
    for failure in items:
        lines.append(f"    - #{failure.get('lineNumber', '')} {failure.get('type') or ''}: {failure.get('name') or ''}")
        if failure.get("message"):
            lines.append(f"      message: {failure.get('message')}")
        if failure.get("detail"):
            lines.append(f"      detail: {failure.get('detail')}")
    return "\n".join(lines)


def get_session_verification_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 50,
) -> str:
    return format_session_verification_report_text(
        get_session_verification_report(project_root, run_id, max_checks=max_checks)
    )


def get_session_verification_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_checks: int = 50,
    max_text: int = 160,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_verification_report(
            project_root,
            selected,
            max_checks=max_checks,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_verification_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    lines = ["Session verification:"]
    truncated = bool(report.get("truncated"))
    for key, label in (("verified", "verified"), ("pending", "pendingChecks"), ("failed", "failedChecks")):
        group = report.get(key) if isinstance(report.get(key), dict) else {}
        total = int(group.get("total", 0) or 0)
        shown = int(group.get("shown", 0) or 0)
        items = [item for item in group.get("items", []) if isinstance(item, str)] if isinstance(group.get("items"), list) else []
        if items:
            lines.append(f"  {label}: {shown}/{total}")
            lines.extend(f"    - {item}" for item in items)
        else:
            lines.append(f"  {label}: none")
        truncated = truncated or bool(group.get("truncated"))
    lines.append(f"  truncated: {'yes' if truncated else 'no'}")
    return "\n".join(lines)


def get_session_audit_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_audit_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


def get_session_audit_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 10,
    max_files: int = 20,
    max_commands: int = 10,
    max_checks: int = 50,
    max_text: int = 300,
) -> str:
    return format_session_audit_report_text(
        get_session_audit_report(
            project_root,
            run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_text=max_text,
        )
    )


def format_session_audit_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    approvals = summary.get("approvals") if isinstance(summary.get("approvals"), dict) else {}
    checkpoints = report.get("checkpoints") if isinstance(report.get("checkpoints"), dict) else {}
    final_review = report.get("finalReview") if isinstance(report.get("finalReview"), dict) else {}
    background = report.get("backgroundProcesses") if isinstance(report.get("backgroundProcesses"), dict) else {}
    blockers = report.get("blockers") if isinstance(report.get("blockers"), dict) else {}
    completion = report.get("completion") if isinstance(report.get("completion"), dict) else {}
    verification = report.get("verification") if isinstance(report.get("verification"), dict) else {}
    plan = report.get("plan") if isinstance(report.get("plan"), dict) else {}
    failures = report.get("failures") if isinstance(report.get("failures"), dict) else {}
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    files = report.get("files") if isinstance(report.get("files"), dict) else {}

    lines = [
        "Session audit:",
        f"  session: {session}",
        f"  ready: {'yes' if bool(report.get('ready')) else 'no'}",
        f"  status: {report.get('status') or ''}",
        f"  events: {int(summary.get('events', 0) or 0)}",
        f"  iterations: {int(summary.get('iterations', 0) or 0)}",
        f"  tools: {int(summary.get('toolCalls', 0) or 0)}",
        (
            "  approvals: "
            f"{int(approvals.get('requested', 0) or 0)} requested, "
            f"{int(approvals.get('approved', 0) or 0)} approved, "
            f"{int(approvals.get('denied', 0) or 0)} denied"
        ),
    ]
    if summary.get("task"):
        lines.append(f"  task: {summary.get('task')}")
    if int(checkpoints.get("created", 0) or 0) > 0:
        checkpoint_line = (
            "  checkpoints: "
            f"created={int(checkpoints.get('created', 0) or 0)}, "
            f"auto={int(checkpoints.get('autoCreated', 0) or 0)}"
        )
        if checkpoints.get("latestId"):
            checkpoint_line += f", latest={checkpoints.get('latestId')}"
        lines.append(checkpoint_line)
    if final_review.get("seen"):
        final_ready = final_review.get("ready")
        ready = "yes" if final_ready is True else "no" if final_ready is False else "unknown"
        lines.append(
            "  finalReview: "
            f"ready={ready}, "
            f"blocking={int(final_review.get('blockingIssues', 0) or 0)}, "
            f"warnings={int(final_review.get('warnings', 0) or 0)}, "
            f"files={int(final_review.get('files', 0) or 0)}, "
            f"suggestedChecks={int(final_review.get('suggestedChecks', 0) or 0)}"
        )
        lines.extend(_format_final_review_changed_file_lines(final_review, indent="  ", max_text=300))
    else:
        lines.append("  finalReview: not run")

    lines.append("  backgroundProcesses:")
    lines.append(f"    started: {int(background.get('started', 0) or 0)}")
    lines.append(f"    active: {int(background.get('active', 0) or 0)}")
    background_items = [item for item in background.get("processes", []) if isinstance(item, dict)] if isinstance(background.get("processes"), list) else []
    for process in background_items:
        lines.append(
            "    - "
            f"#{process.get('lineNumber', '')} {process.get('processId') or ''}: "
            f"pid={process.get('pid') if process.get('pid') is not None else 'unknown'}, "
            f"cwd={process.get('cwd') or ''}, "
            f"command={process.get('command') or ''}"
        )

    lines.append("  blockers:")
    blocker_items = [item for item in blockers.get("items", []) if isinstance(item, str)] if isinstance(blockers.get("items"), list) else []
    if blocker_items:
        lines.extend(f"    - {blocker}" for blocker in blocker_items)
    else:
        lines.append("    - none")

    if completion.get("ready") is not None:
        lines.append(f"  completionReady: {'yes' if completion.get('ready') else 'no'}")
    _append_audit_string_list(lines, "  completionBlockers:", completion.get("blockers"))
    if int(completion.get("blockedCount", 0) or 0) > 0:
        lines.append(f"  completionBlocked: {int(completion.get('blockedCount', 0) or 0)}")
        _append_audit_string_list(lines, "  latestCompletionBlockers:", completion.get("latestBlockers"))
    _append_audit_string_list(lines, "  latestPendingVerificationChecks:", completion.get("latestPendingVerificationChecks"))
    _append_audit_string_list(lines, "  latestFailedVerificationChecks:", completion.get("latestFailedVerificationChecks"))
    _append_audit_string_list(lines, "  latestFinalReviewBlockingIssues:", completion.get("latestFinalReviewBlockingIssues"))
    _append_audit_string_list(lines, "  latestFinalReviewChangedFiles:", completion.get("latestFinalReviewChangedFiles"))
    _append_audit_string_list(lines, "  latestToolErrors:", completion.get("latestToolErrors"))
    _append_audit_string_list(lines, "  latestCheckpointFailures:", completion.get("latestCheckpointFailures"))
    _append_audit_string_list(lines, "  latestActiveBackgroundProcesses:", completion.get("latestActiveBackgroundProcesses"))
    _append_audit_string_list(lines, "  latestDeniedApprovals:", completion.get("latestDeniedApprovals"))
    _append_audit_string_list(lines, "  completionWarnings:", completion.get("warnings"))

    lines.append("  verification:")
    _append_audit_verification_group(lines, "verified", "verifiedChecks", "verifiedChecksOmitted", verification.get("verified"))
    _append_audit_verification_group(lines, "pending", "pendingChecks", "pendingChecksOmitted", verification.get("pending"))
    _append_audit_verification_group(lines, "failed", "failedChecks", "failedChecksOmitted", verification.get("failed"))

    lines.append("  plan:")
    plan_items = int(plan.get("items", 0) or 0)
    lines.append(f"    items: {plan_items}")
    if plan_items > 0:
        lines.append(f"    inProgress: {'yes' if bool(plan.get('inProgress')) else 'no'}")
        pending = plan.get("pending") if isinstance(plan.get("pending"), dict) else {}
        pending_items = [item for item in pending.get("items", []) if isinstance(item, dict)] if isinstance(pending.get("items"), list) else []
        for item in pending_items:
            lines.append(f"    - {item.get('status') or ''}: {item.get('step') or ''}")

    _append_audit_failures(lines, failures)
    _append_audit_commands(lines, commands)
    _append_audit_files(lines, files)
    return "\n".join(lines)


def _append_audit_string_list(lines: list[str], label: str, values: object) -> None:
    items = [item for item in values if isinstance(item, str)] if isinstance(values, list) else []
    if not items:
        return
    lines.append(label)
    lines.extend(f"    - {item}" for item in items)


def _append_audit_verification_group(
    lines: list[str],
    count_label: str,
    list_label: str,
    omitted_label: str,
    group: object,
) -> None:
    data = group if isinstance(group, dict) else {}
    total = int(data.get("total", 0) or 0)
    shown = int(data.get("shown", 0) or 0)
    items = [item for item in data.get("items", []) if isinstance(item, str)] if isinstance(data.get("items"), list) else []
    lines.append(f"    {count_label}: {total}")
    if not items:
        return
    lines.append(f"    {list_label}:")
    lines.extend(f"      - {item}" for item in items)
    omitted = max(total - shown, 0)
    if omitted > 0:
        lines.append(f"    {omitted_label}: {omitted}")


def _append_audit_failures(lines: list[str], failures: dict[str, object]) -> None:
    total = int(failures.get("total", 0) or 0)
    shown = int(failures.get("shown", 0) or 0)
    items = [item for item in failures.get("items", []) if isinstance(item, dict)] if isinstance(failures.get("items"), list) else []
    lines.append("  failures:")
    lines.append(f"    count: {total}")
    lines.append(f"    shown: {shown}/{total}")
    if not items:
        lines.append("    - none")
        return
    for failure in items:
        lines.append(
            "    - "
            f"#{failure.get('lineNumber', '')} {failure.get('type') or ''} {failure.get('name') or ''}: "
            f"{failure.get('message') or ''}"
        )
        if failure.get("detail"):
            lines.append(f"      detail: {failure.get('detail')}")


def _append_audit_commands(lines: list[str], commands: dict[str, object]) -> None:
    total = int(commands.get("total", 0) or 0)
    shown = int(commands.get("shown", 0) or 0)
    items = [item for item in commands.get("items", []) if isinstance(item, dict)] if isinstance(commands.get("items"), list) else []
    lines.append("  commands:")
    lines.append(f"    count: {total}")
    lines.append(f"    shown: {shown}/{total}")
    if not items:
        lines.append("    - none")
        return
    for command in items:
        exit_code = command.get("exitCode")
        lines.append(
            "    - "
            f"#{command.get('lineNumber', '')} {command.get('kind') or ''}[{command.get('index')}]: "
            f"exit={exit_code if isinstance(exit_code, int) else 'unknown'}, "
            f"timedOut={'yes' if command.get('timedOut') is True else 'no'}, "
            f"cwd={command.get('cwd') or '.'}, "
            f"command={command.get('command') or 'unknown'}"
        )


def _append_audit_files(lines: list[str], files: dict[str, object]) -> None:
    total = int(files.get("total", 0) or 0)
    shown = int(files.get("shown", 0) or 0)
    items = [item for item in files.get("items", []) if isinstance(item, dict)] if isinstance(files.get("items"), list) else []
    lines.append("  files:")
    lines.append(f"    count: {total}")
    lines.append(f"    shown: {shown}/{total}")
    if not items:
        lines.append("    - none")
        return
    for item in items:
        uses = ",".join(str(use) for use in item.get("uses", []) if isinstance(use, str)) if isinstance(item.get("uses"), list) else "unknown"
        lines.append(f"    - {item.get('path') or 'unknown'} uses={uses}")


def get_session_handoff_text(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> str:
    return format_session_handoff_report_text(
        get_session_handoff_report(
            project_root,
            run_id,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    )


def get_session_handoff_report(
    project_root: str | Path = ".",
    run_id: str | None = None,
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> dict[str, object]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return {
            "session": None,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "missing",
            "message": "No sessions found.",
        }
    try:
        return build_session_handoff_report(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return {
            "session": selected,
            "exists": False,
            "ok": False,
            "ready": False,
            "status": "invalid",
            "message": str(error),
        }


def format_session_handoff_report_text(report: dict[str, object]) -> str:
    session = str(report.get("session") or "")
    if not bool(report.get("exists")):
        fallback = f"Session not found: {session}" if session else "No sessions found."
        return str(report.get("message") or fallback)

    lines = ["Session handoff:", f"  session: {session}"]
    sections = report.get("sections") if isinstance(report.get("sections"), dict) else {}
    for title in ("summary", "readiness", "plan", "verification", "failures", "files", "commands"):
        section_text = sections.get(title)
        if not isinstance(section_text, str):
            continue
        lines.append(f"  {title}:")
        lines.extend(f"    {line}" for line in section_text.splitlines())
    return "\n".join(lines)


def get_resume_context(
    run_id: str | None,
    project_root: str | Path = ".",
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> tuple[str | None, str | None, str]:
    if run_id and run_id.strip().lower() in {"off", "clear", "none"}:
        return None, None, "Resume context cleared."
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None, None, "No sessions found."
    try:
        context = build_session_resume_context(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return None, None, str(error)
    return selected, context, f"Resume context loaded from session {selected}."


def get_compact_context(
    run_id: str | None,
    project_root: str | Path = ".",
    max_failures: int = 20,
    max_files: int = 50,
    max_commands: int = 10,
    max_checks: int = 50,
    max_output_chars: int = 1_000,
    max_text: int = 500,
) -> tuple[str | None, str | None, str]:
    selected = run_id or get_last_session_id(project_root)
    if not selected:
        return None, None, "No sessions found."
    try:
        context = build_session_resume_context(
            project_root,
            selected,
            max_failures=max_failures,
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_output_chars=max_output_chars,
            max_text=max_text,
        )
    except ValueError as error:
        return None, None, str(error)
    return selected, context, f"Compacted context loaded from session {selected}."
