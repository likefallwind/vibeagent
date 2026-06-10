from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .config import CostRates


@dataclass(frozen=True)
class SessionPlanItem:
    step: str
    status: str


@dataclass(frozen=True)
class SessionEvent:
    type: str
    payload: dict[str, Any]
    line_number: int
    raw: dict[str, Any] | None = None
    malformed: bool = False
    error: str | None = None


@dataclass(frozen=True)
class SessionInfo:
    run_id: str
    event_count: int
    malformed_count: int
    last_event_time: datetime | None


@dataclass(frozen=True)
class SessionSummary:
    run_id: str
    exists: bool
    event_count: int
    malformed_count: int
    iterations: int
    task: str | None
    tool_calls: list[str]
    approvals_requested: int
    approvals_approved: int
    approvals_denied: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    final_message: str | None
    latest_plan: list[SessionPlanItem]
    completed: bool
    failed: bool


@dataclass(frozen=True)
class SessionUsageSummary:
    sessions: int
    events: int
    malformed_rows: int
    iterations: int
    tool_calls: int
    approvals_requested: int
    approvals_approved: int
    approvals_denied: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    completed: int
    failed: int


def list_sessions(project_root: str | Path, limit: int = 20) -> list[SessionInfo]:
    sessions_root = sessions_dir(project_root)
    if not sessions_root.is_dir():
        return []

    infos = [read_session_info(path) for path in sessions_root.iterdir() if path.is_dir()]
    infos.sort(key=lambda info: info.last_event_time or datetime.min.replace(tzinfo=UTC), reverse=True)
    return infos[:limit]


def read_session_events(project_root: str | Path, run_id: str) -> list[SessionEvent]:
    return read_events_file(events_path(project_root, run_id))


def summarize_session(project_root: str | Path, run_id: str) -> SessionSummary:
    session_path = session_dir(project_root, run_id)
    events = read_session_events(project_root, run_id)
    valid_events = [event for event in events if not event.malformed]
    malformed_count = len(events) - len(valid_events)
    iterations = max((as_int(event.payload.get("iteration")) or 0 for event in valid_events), default=0)

    tool_calls: list[str] = []
    approvals_requested = 0
    approvals_approved = 0
    approvals_denied = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    cache_creation_tokens = 0
    cache_read_tokens = 0
    task: str | None = None
    final_message: str | None = None
    latest_plan: list[SessionPlanItem] = []
    completed = False
    failed = False

    for event in valid_events:
        if event.type == "task":
            event_task = event.payload.get("task")
            if isinstance(event_task, str):
                task = event_task
        elif event.type == "tool_call":
            name = event.payload.get("name")
            if isinstance(name, str):
                tool_calls.append(name)
        elif event.type == "approval_requested":
            approvals_requested += 1
        elif event.type == "approval_decision":
            decision = event.payload.get("decision")
            approved = decision.get("approved") if isinstance(decision, dict) else None
            if approved is True:
                approvals_approved += 1
            elif approved is False:
                approvals_denied += 1
        elif event.type == "model":
            text = model_text(event.payload.get("content"))
            has_tool_call = has_tool_call_content(event.payload.get("content"))
            usage = parse_usage_payload(event.payload.get("usage"))
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]
            total_tokens += usage["total_tokens"]
            cache_creation_tokens += usage["cache_creation_tokens"]
            cache_read_tokens += usage["cache_read_tokens"]
            if text and not has_tool_call:
                final_message = text
                completed = True
        elif event.type == "tool_result":
            result = event.payload.get("result")
            if isinstance(result, dict):
                kind = result.get("kind")
                if kind == "finish" and isinstance(result.get("message"), str):
                    final_message = result["message"]
                    completed = True
                if kind == "update_plan":
                    latest_plan = parse_session_plan(result.get("plan"))
                if is_failed_tool_result(result):
                    failed = True
        elif event.type == "step_completed":
            step = event.payload.get("step")
            status = step.get("status") if isinstance(step, dict) else None
            if status in {"failed", "denied"}:
                failed = True

    return SessionSummary(
        run_id=run_id,
        exists=session_path.is_dir(),
        event_count=len(valid_events),
        malformed_count=malformed_count,
        iterations=iterations,
        task=task,
        tool_calls=tool_calls,
        approvals_requested=approvals_requested,
        approvals_approved=approvals_approved,
        approvals_denied=approvals_denied,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        final_message=final_message,
        latest_plan=latest_plan,
        completed=completed,
        failed=failed or (session_path.is_dir() and bool(valid_events) and not completed),
    )


def summarize_usage(project_root: str | Path, limit: int = 20) -> SessionUsageSummary:
    summaries = [summarize_session(project_root, info.run_id) for info in list_sessions(project_root, limit=limit)]
    return SessionUsageSummary(
        sessions=len(summaries),
        events=sum(summary.event_count for summary in summaries),
        malformed_rows=sum(summary.malformed_count for summary in summaries),
        iterations=sum(summary.iterations for summary in summaries),
        tool_calls=sum(len(summary.tool_calls) for summary in summaries),
        approvals_requested=sum(summary.approvals_requested for summary in summaries),
        approvals_approved=sum(summary.approvals_approved for summary in summaries),
        approvals_denied=sum(summary.approvals_denied for summary in summaries),
        input_tokens=sum(summary.input_tokens for summary in summaries),
        output_tokens=sum(summary.output_tokens for summary in summaries),
        total_tokens=sum(summary.total_tokens for summary in summaries),
        cache_creation_tokens=sum(summary.cache_creation_tokens for summary in summaries),
        cache_read_tokens=sum(summary.cache_read_tokens for summary in summaries),
        completed=sum(1 for summary in summaries if summary.completed),
        failed=sum(1 for summary in summaries if summary.failed),
    )


def format_sessions(project_root: str | Path, limit: int = 20) -> str:
    sessions = list_sessions(project_root, limit=limit)
    if not sessions:
        return "No sessions found."
    lines = ["Recent sessions:"]
    for info in sessions:
        last = (
            info.last_event_time.isoformat(timespec="seconds").replace("+00:00", "Z")
            if info.last_event_time
            else "unknown"
        )
        malformed = f", {info.malformed_count} malformed" if info.malformed_count else ""
        lines.append(f"  {info.run_id}  events={info.event_count}{malformed}  last={last}")
    return "\n".join(lines)


def format_usage(project_root: str | Path, limit: int = 20) -> str:
    usage = summarize_usage(project_root, limit=limit)
    if usage.sessions == 0:
        return "No sessions found."
    lines = [
        "Usage:",
        f"  sessions: {usage.sessions}",
        f"  events: {usage.events}",
        f"  iterations: {usage.iterations}",
        f"  toolCalls: {usage.tool_calls}",
        (
            "  approvals: "
            f"{usage.approvals_requested} requested, "
            f"{usage.approvals_approved} approved, "
            f"{usage.approvals_denied} denied"
        ),
        f"  completed: {usage.completed}",
        f"  failed: {usage.failed}",
    ]
    if usage.total_tokens or usage.input_tokens or usage.output_tokens:
        lines.extend(
            [
                f"  inputTokens: {usage.input_tokens}",
                f"  outputTokens: {usage.output_tokens}",
                f"  totalTokens: {usage.total_tokens}",
            ]
        )
    if usage.cache_creation_tokens or usage.cache_read_tokens:
        lines.append(
            f"  cacheTokens: {usage.cache_creation_tokens} created, {usage.cache_read_tokens} read"
        )
    if usage.malformed_rows:
        lines.append(f"  malformedRows: {usage.malformed_rows}")
    if usage.total_tokens or usage.input_tokens or usage.output_tokens:
        lines.append("  cost: unavailable; provider pricing is not configured.")
    else:
        lines.append("  cost: unavailable; provider token usage is not recorded.")
    return "\n".join(lines)


def format_cost(
    project_root: str | Path,
    rates: CostRates,
    rate_errors: list[str] | None = None,
    limit: int = 20,
) -> str:
    usage = summarize_usage(project_root, limit=limit)
    if usage.sessions == 0:
        return "No sessions found."
    lines = [
        "Cost:",
        f"  sessions: {usage.sessions}",
        f"  inputTokens: {usage.input_tokens}",
        f"  outputTokens: {usage.output_tokens}",
        f"  totalTokens: {usage.total_tokens}",
    ]
    if usage.cache_creation_tokens or usage.cache_read_tokens:
        lines.append(
            f"  cacheTokens: {usage.cache_creation_tokens} created, {usage.cache_read_tokens} read"
        )
    if rate_errors:
        lines.extend(f"  error: {error}" for error in rate_errors)
        return "\n".join(lines)
    if not (usage.input_tokens or usage.output_tokens or usage.total_tokens):
        lines.append("  estimate: unavailable; provider token usage is not recorded.")
        return "\n".join(lines)
    missing = missing_cost_rate_names(usage, rates)
    if missing:
        lines.append(f"  estimate: unavailable; set {', '.join(missing)}.")
        return "\n".join(lines)

    input_cost = token_cost(usage.input_tokens, rates.input_usd_per_million)
    output_cost = token_cost(usage.output_tokens, rates.output_usd_per_million)
    cache_creation_cost = token_cost(usage.cache_creation_tokens, rates.cache_creation_usd_per_million)
    cache_read_cost = token_cost(usage.cache_read_tokens, rates.cache_read_usd_per_million)
    total_cost = input_cost + output_cost + cache_creation_cost + cache_read_cost
    lines.extend(
        [
            f"  inputCostUsd: {format_usd(input_cost)}",
            f"  outputCostUsd: {format_usd(output_cost)}",
        ]
    )
    if usage.cache_creation_tokens or usage.cache_read_tokens:
        lines.append(
            f"  cacheCostUsd: {format_usd(cache_creation_cost + cache_read_cost)}"
        )
    lines.append(f"  estimatedCostUsd: {format_usd(total_cost)}")
    return "\n".join(lines)


def format_session_summary(summary: SessionSummary) -> str:
    if not summary.exists:
        return f"Session not found: {summary.run_id}"

    tool_counts = count_names(summary.tool_calls)
    tools = ", ".join(f"{name} x{count}" if count > 1 else name for name, count in tool_counts.items())
    status = "completed" if summary.completed else "failed" if summary.failed else "incomplete"
    lines = [
        f"Session: {summary.run_id}",
        f"  status: {status}",
        f"  events: {summary.event_count}",
        f"  iterations: {summary.iterations}",
        f"  tools: {tools or 'none'}",
        (
            "  approvals: "
            f"{summary.approvals_requested} requested, "
            f"{summary.approvals_approved} approved, "
            f"{summary.approvals_denied} denied"
        ),
    ]
    if summary.total_tokens or summary.input_tokens or summary.output_tokens:
        lines.append(
            "  tokens: "
            f"{summary.input_tokens} input, "
            f"{summary.output_tokens} output, "
            f"{summary.total_tokens} total"
        )
    if summary.cache_creation_tokens or summary.cache_read_tokens:
        lines.append(
            "  cacheTokens: "
            f"{summary.cache_creation_tokens} created, "
            f"{summary.cache_read_tokens} read"
        )
    if summary.malformed_count:
        lines.append(f"  malformedRows: {summary.malformed_count}")
    if summary.task:
        lines.append(f"  task: {compact(summary.task, 240)}")
    if summary.latest_plan:
        lines.append("  plan:")
        lines.extend(f"    - {item.status}: {compact(item.step, 160)}" for item in summary.latest_plan)
    if summary.final_message:
        lines.append(f"  final: {compact(summary.final_message, 240)}")
    return "\n".join(lines)


def build_session_resume_context(project_root: str | Path, run_id: str) -> str:
    summary = summarize_session(project_root, run_id)
    if not summary.exists:
        raise ValueError(f"Session not found: {run_id}")

    tool_counts = count_names(summary.tool_calls)
    tools = ", ".join(f"{name} x{count}" if count > 1 else name for name, count in tool_counts.items()) or "none"
    status = "completed" if summary.completed else "failed" if summary.failed else "incomplete"
    lines = [
        f"session: {summary.run_id}",
        f"status: {status}",
        f"iterations: {summary.iterations}",
        f"tools: {tools}",
    ]
    if summary.task:
        lines.append(f"task: {compact(summary.task, 1000)}")
    if summary.latest_plan:
        lines.append("plan:")
        lines.extend(f"- {item.status}: {compact(item.step, 400)}" for item in summary.latest_plan)
    if summary.final_message:
        lines.append(f"final: {compact(summary.final_message, 1200)}")
    return "\n".join(lines)


def get_last_session_id(project_root: str | Path) -> str | None:
    sessions = list_sessions(project_root, limit=1)
    return sessions[0].run_id if sessions else None


def read_session_info(path: Path) -> SessionInfo:
    events = path / "events.jsonl"
    parsed_events = read_events_file(events)
    event_count = len([event for event in parsed_events if not event.malformed])
    malformed_count = len(parsed_events) - event_count
    if events.exists():
        last_event_time = datetime.fromtimestamp(events.stat().st_mtime, tz=UTC)
    else:
        last_event_time = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return SessionInfo(
        run_id=path.name,
        event_count=event_count,
        malformed_count=malformed_count,
        last_event_time=last_event_time,
    )


def read_events_file(path: Path) -> list[SessionEvent]:
    if not path.is_file():
        return []
    events: list[SessionEvent] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as error:
            events.append(
                SessionEvent(
                    type="malformed",
                    payload={},
                    line_number=line_number,
                    malformed=True,
                    error=f"Invalid JSON: {error.msg}",
                )
            )
            continue
        if not isinstance(parsed, dict) or not isinstance(parsed.get("type"), str):
            events.append(
                SessionEvent(
                    type="malformed",
                    payload={},
                    line_number=line_number,
                    malformed=True,
                    error="Event row must be an object with a string type.",
                )
            )
            continue
        events.append(
            SessionEvent(
                type=parsed["type"],
                payload={key: value for key, value in parsed.items() if key != "type"},
                line_number=line_number,
                raw=parsed,
            )
        )
    return events


def sessions_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".vibeagent" / "sessions"


def session_dir(project_root: str | Path, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError(f"Invalid session id: {run_id}")
    return sessions_dir(project_root) / run_id


def events_path(project_root: str | Path, run_id: str) -> Path:
    return session_dir(project_root, run_id) / "events.jsonl"


def as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def as_nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def missing_cost_rate_names(usage: SessionUsageSummary, rates: CostRates) -> list[str]:
    missing: list[str] = []
    if usage.input_tokens and rates.input_usd_per_million is None:
        missing.append("VIBEAGENT_INPUT_USD_PER_MILLION")
    if usage.output_tokens and rates.output_usd_per_million is None:
        missing.append("VIBEAGENT_OUTPUT_USD_PER_MILLION")
    if usage.cache_creation_tokens and rates.cache_creation_usd_per_million is None:
        missing.append("VIBEAGENT_CACHE_CREATION_USD_PER_MILLION")
    if usage.cache_read_tokens and rates.cache_read_usd_per_million is None:
        missing.append("VIBEAGENT_CACHE_READ_USD_PER_MILLION")
    return missing


def token_cost(tokens: int, usd_per_million: Decimal | None) -> Decimal:
    if not tokens or usd_per_million is None:
        return Decimal("0")
    return (Decimal(tokens) * usd_per_million) / Decimal(1_000_000)


def format_usd(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.000001'))}"


def parse_usage_payload(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
        }
    input_tokens = as_nonnegative_int(value.get("input_tokens"))
    output_tokens = as_nonnegative_int(value.get("output_tokens"))
    total_tokens = as_nonnegative_int(value.get("total_tokens"))
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_creation_tokens": as_nonnegative_int(value.get("cache_creation_tokens")),
        "cache_read_tokens": as_nonnegative_int(value.get("cache_read_tokens")),
    }


def parse_session_plan(value: Any) -> list[SessionPlanItem]:
    if not isinstance(value, list):
        return []
    items: list[SessionPlanItem] = []
    for item in value[:20]:
        if not isinstance(item, dict):
            continue
        step = item.get("step")
        status = item.get("status")
        if not isinstance(step, str) or not step.strip():
            continue
        if status not in {"pending", "in_progress", "completed"}:
            continue
        items.append(SessionPlanItem(step=step.strip(), status=status))
    return items


def model_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    return "".join(
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ).strip()


def has_tool_call_content(content: Any) -> bool:
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_call" for block in content
    )


def is_failed_tool_result(result: dict[str, Any]) -> bool:
    kind = result.get("kind")
    if kind in {"tool_error", "approval_denied"}:
        return True
    if kind in {
        "check_write_file",
        "write_file",
        "check_write_files",
        "write_files",
        "check_edit_file",
        "edit_file",
        "check_multi_edit_file",
        "multi_edit_file",
        "check_replace_python_definition",
        "replace_python_definition",
        "python_rename",
        "check_replace_lines",
        "replace_lines",
        "check_insert_lines",
        "insert_lines",
        "check_append_file",
        "append_file",
        "regex_replace",
        "check_regex_replace",
        "check_json_set",
        "json_set",
        "check_json_remove",
        "json_remove",
        "check_json_patch",
        "json_patch",
        "check_patch",
        "check_patches",
        "patch_file",
        "patch_files",
        "check_delete_file",
        "delete_file",
        "check_delete_files",
        "delete_files",
        "check_move_file",
        "move_file",
        "check_move_files",
        "move_files",
        "check_copy_file",
        "copy_file",
        "check_copy_files",
        "copy_files",
        "check_move_dir",
        "move_dir",
        "check_move_dirs",
        "move_dirs",
        "check_copy_dir",
        "copy_dir",
        "check_copy_dirs",
        "copy_dirs",
        "check_create_dir",
        "create_dir",
        "check_create_dirs",
        "create_dirs",
        "check_delete_empty_dir",
        "delete_empty_dir",
        "check_delete_empty_dirs",
        "delete_empty_dirs",
        "check_set_executable",
        "set_executable",
        "check_git_stage",
        "git_stage",
        "check_git_unstage",
        "git_unstage",
        "check_git_commit",
        "git_commit",
    }:
        return result.get("ok") is False
    if kind == "read_files":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "read_file_ranges":
        ranges = result.get("ranges")
        return isinstance(ranges, list) and any(isinstance(item, dict) and item.get("ok") is False for item in ranges)
    if kind == "file_info":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "repo_map":
        return result.get("ok") is False
    if kind == "python_symbols":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "code_outline":
        files = result.get("files")
        return isinstance(files, list) and any(isinstance(file, dict) and file.get("ok") is False for file in files)
    if kind == "python_check":
        return result.get("ok") is False
    if kind == "config_check":
        return result.get("ok") is False
    if kind == "python_dependencies":
        return result.get("ok") is False
    if kind == "code_dependencies":
        return result.get("ok") is False
    if kind == "code_references":
        return result.get("ok") is False
    if kind == "code_definitions":
        return result.get("ok") is False
    if kind == "python_definitions":
        return result.get("ok") is False
    if kind == "python_calls":
        return result.get("ok") is False
    if kind == "python_call_graph":
        return result.get("ok") is False
    if kind == "python_references":
        return result.get("ok") is False
    if kind == "python_rename_preview":
        return result.get("ok") is False
    if kind in {
        "git_info",
        "git_status",
        "git_changes",
        "git_branches",
        "check_git_fetch",
        "git_fetch",
        "check_git_pull",
        "git_pull",
        "check_git_push",
        "git_push",
        "check_git_restore",
        "git_restore",
        "git_stashes",
        "check_git_stash",
        "git_stash",
        "check_git_stash_apply",
        "git_stash_apply",
        "check_git_stash_drop",
        "git_stash_drop",
        "check_git_switch",
        "git_switch",
        "review_changes",
        "final_review",
        "suggest_checks",
        "project_commands",
        "project_manifests",
        "project_overview",
        "command_check",
        "check_run_commands",
        "check_start_command",
        "port_check",
        "http_check",
        "check_write_process",
        "write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "environment_info",
        "git_diff",
        "git_diff_hunks",
        "git_log",
        "git_show",
        "git_blame",
    }:
        return result.get("ok") is False
    if kind == "session_summary":
        return result.get("ok") is False
    if kind == "search":
        return result.get("ok") is False
    if kind == "glob":
        return result.get("ok") is False
    if kind == "list_tree":
        return result.get("ok") is False
    if kind in {
        "start_command",
        "read_process",
        "wait_process",
        "check_stop_all_processes",
        "check_stop_process",
        "stop_all_processes",
        "stop_process",
    }:
        return result.get("ok") is False
    if kind == "run_command":
        command_result = result.get("result")
        if not isinstance(command_result, dict):
            return True
        return command_result.get("exit_code") != 0 or command_result.get("timed_out") is True
    if kind == "run_commands":
        return result.get("ok") is False
    return False


def count_names(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def compact(value: str, max_length: int) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= max_length:
        return collapsed
    return f"{collapsed[:max_length]}..."
