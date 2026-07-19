from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .observation_session_types import SessionAuditProcess
from .session_completion_detail_fields import completion_detail_kwargs_from_report


@dataclass(frozen=True)
class SessionHandoffDetails:
    ready: bool | None = None
    status: str = ""
    blockers: list[str] = field(default_factory=list)
    background_processes_started: int = 0
    active_background_processes: list[SessionAuditProcess] = field(default_factory=list)
    verified_commands: list[dict[str, Any]] = field(default_factory=list)
    pending_commands: list[dict[str, Any]] = field(default_factory=list)
    failed_commands: list[dict[str, Any]] = field(default_factory=list)
    verified_count: int = 0
    pending_count: int = 0
    failed_count: int = 0
    pending_plan_items: list[dict[str, str]] = field(default_factory=list)
    pending_plan_count: int = 0
    plan_items_count: int = 0
    plan_in_progress: bool = False
    file_references: list[dict[str, Any]] = field(default_factory=list)
    file_count: int = 0
    shown_file_count: int = 0
    files_truncated: bool = False
    completion_ready: bool | None = None
    completion_blockers: list[str] = field(default_factory=list)
    latest_completion_blockers: list[str] = field(default_factory=list)
    latest_completion_pending_verification_checks: list[str] = field(default_factory=list)
    latest_completion_failed_verification_checks: list[str] = field(default_factory=list)
    latest_completion_final_review_issues: list[str] = field(default_factory=list)
    latest_completion_final_review_changed_files: list[str] = field(default_factory=list)
    latest_completion_tool_errors: list[str] = field(default_factory=list)
    latest_completion_checkpoint_failures: list[str] = field(default_factory=list)
    latest_completion_active_background_processes: list[str] = field(default_factory=list)
    latest_completion_denied_approvals: list[str] = field(default_factory=list)
    latest_completion_next_actions: list[str] = field(default_factory=list)


def empty_session_handoff_details(status: str = "invalid", ready: bool | None = False) -> SessionHandoffDetails:
    return SessionHandoffDetails(status=status, ready=ready)


def _verification_group(audit: dict[str, object], name: str) -> tuple[list[dict[str, Any]], int]:
    verification = audit.get("verification") if isinstance(audit.get("verification"), dict) else {}
    group = verification.get(name) if isinstance(verification.get(name), dict) else {}
    total = group.get("total")
    raw_commands = group.get("commands")
    commands: list[dict[str, Any]] = []
    if isinstance(raw_commands, list):
        commands = [item for item in raw_commands if isinstance(item, dict)]
    return commands, total if isinstance(total, int) else len(commands)


def _file_references(audit: dict[str, object]) -> tuple[list[dict[str, Any]], int, int, bool]:
    files = audit.get("files") if isinstance(audit.get("files"), dict) else {}
    total = files.get("total")
    shown = files.get("shown")
    truncated = files.get("truncated") is True
    raw_items = files.get("items")
    references: list[dict[str, Any]] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            uses = [
                str(use).strip()
                for use in item.get("uses", [])
                if isinstance(use, str) and use.strip()
            ]
            references.append({"path": path, "uses": uses})
    file_count = total if isinstance(total, int) else len(references)
    shown_file_count = shown if isinstance(shown, int) else len(references)
    return references, file_count, shown_file_count, truncated


def _background_processes(audit: dict[str, object]) -> tuple[int, list[SessionAuditProcess]]:
    background = audit.get("backgroundProcesses") if isinstance(audit.get("backgroundProcesses"), dict) else {}
    started = background.get("started")
    processes = background.get("processes") if isinstance(background.get("processes"), list) else []
    active_processes = []
    for process in processes:
        if not isinstance(process, dict):
            continue
        process_id = str(process.get("processId") or "").strip()
        command = str(process.get("command") or "").strip()
        if not process_id and not command:
            continue
        pid = process.get("pid")
        line_number = process.get("lineNumber")
        active_processes.append(
            SessionAuditProcess(
                process_id=process_id,
                pid=pid if isinstance(pid, int) else None,
                command=command,
                cwd=str(process.get("cwd") or ".").strip() or ".",
                line_number=line_number if isinstance(line_number, int) else 0,
            )
        )
    return started if isinstance(started, int) else 0, active_processes


def _pending_plan_items(audit: dict[str, object]) -> tuple[list[dict[str, str]], int, int, bool]:
    plan = audit.get("plan") if isinstance(audit.get("plan"), dict) else {}
    plan_items = plan.get("items")
    plan_items_count = plan_items if isinstance(plan_items, int) else 0
    plan_in_progress = plan.get("inProgress") is True
    pending_plan = plan.get("pending") if isinstance(plan.get("pending"), dict) else {}
    pending_plan_total = pending_plan.get("total")
    pending_plan_count = pending_plan_total if isinstance(pending_plan_total, int) else 0
    items = []
    raw_items = pending_plan.get("items") if isinstance(pending_plan.get("items"), list) else []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        step = str(item.get("step") or "").strip()
        status_value = str(item.get("status") or "").strip()
        if step:
            items.append({"status": status_value, "step": step})
    return items, pending_plan_count, plan_items_count, plan_in_progress


def extract_session_handoff_details(report: dict[str, object]) -> SessionHandoffDetails:
    ready = report.get("ready") if isinstance(report.get("ready"), bool) else None
    status = str(report.get("status") or "")
    audit = report.get("audit") if isinstance(report.get("audit"), dict) else {}
    blockers_section = audit.get("blockers") if isinstance(audit.get("blockers"), dict) else {}
    blockers = [
        str(blocker).strip()
        for blocker in blockers_section.get("items", [])
        if isinstance(blocker, str) and blocker.strip()
    ]
    background_processes_started, active_background_processes = _background_processes(audit)
    verified_commands, verified_count = _verification_group(audit, "verified")
    pending_commands, pending_count = _verification_group(audit, "pending")
    failed_commands, failed_count = _verification_group(audit, "failed")
    file_references, file_count, shown_file_count, files_truncated = _file_references(audit)
    pending_plan_items, pending_plan_count, plan_items_count, plan_in_progress = _pending_plan_items(audit)
    completion = audit.get("completion") if isinstance(audit.get("completion"), dict) else {}
    completion_ready = completion.get("ready") if isinstance(completion.get("ready"), bool) else None
    completion_blockers = [
        str(blocker).strip()
        for blocker in completion.get("blockers", [])
        if isinstance(blocker, str) and blocker.strip()
    ]
    latest_completion_blockers = [
        str(blocker).strip()
        for blocker in completion.get("latestBlockers", [])
        if isinstance(blocker, str) and blocker.strip()
    ]
    completion_detail_kwargs = completion_detail_kwargs_from_report(completion)
    return SessionHandoffDetails(
        ready=ready,
        status=status,
        blockers=blockers,
        background_processes_started=background_processes_started,
        active_background_processes=active_background_processes,
        verified_commands=verified_commands,
        pending_commands=pending_commands,
        failed_commands=failed_commands,
        verified_count=verified_count,
        pending_count=pending_count,
        failed_count=failed_count,
        pending_plan_items=pending_plan_items,
        pending_plan_count=pending_plan_count,
        plan_items_count=plan_items_count,
        plan_in_progress=plan_in_progress,
        file_references=file_references,
        file_count=file_count,
        shown_file_count=shown_file_count,
        files_truncated=files_truncated,
        completion_ready=completion_ready,
        completion_blockers=completion_blockers,
        latest_completion_blockers=latest_completion_blockers,
        **completion_detail_kwargs,
    )
