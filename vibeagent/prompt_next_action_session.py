from __future__ import annotations

from .types import Observation


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _session_audit_process_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        process_id = str(getattr(value, "process_id", "") or "").strip()
        command = str(getattr(value, "command", "") or "").strip()
        cwd = str(getattr(value, "cwd", "") or "").strip()
        if process_id and command:
            label = f"{process_id}: {command}"
        elif process_id:
            label = process_id
        elif command:
            label = command
        else:
            continue
        if cwd and cwd != ".":
            label = f"{label} (cwd={cwd})"
        labels.append(label)
    return labels


def _verification_command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not isinstance(value, dict):
            continue
        command = str(value.get("command") or "").strip()
        cwd = str(value.get("cwd") or ".").strip() or "."
        reason = str(value.get("failureReason") or "").strip()
        if not command:
            continue
        label = f"{command} (cwd={cwd})"
        if reason:
            label = f"{label}: {reason}"
        labels.append(label)
    return labels


def _session_verification_next_action_instruction(base: str, latest: Observation) -> str:
    failed = _verification_command_labels(getattr(latest, "failed_commands", []))
    pending = _verification_command_labels(getattr(latest, "pending_commands", []))

    if failed and pending:
        return (
            f"{base} Session verification reports failed and pending checks. "
            f"Use run_session_verification to rerun recorded verification checks first: "
            f"{_format_next_action_items(failed + pending)}. "
            "If failures remain, inspect them with session_output_diagnostics or session_output_contexts, "
            "fix the code, and rerun verification before finishing."
        )

    if failed:
        return (
            f"{base} Session verification reports failed checks. "
            f"Use run_session_verification to rerun them first: {_format_next_action_items(failed)}. "
            "If failures remain, inspect them with session_output_diagnostics or session_output_contexts, "
            "fix the code, and rerun verification before finishing."
        )

    if pending:
        return (
            f"{base} Session verification reports pending checks. "
            f"Use run_session_verification to run them before finishing: {_format_next_action_items(pending)}."
        )

    if getattr(latest, "ok", False):
        return (
            f"{base} Session verification is complete. Continue with any remaining requested work, "
            "or answer directly if the task is complete."
        )

    return (
        f"{base} Session verification is not ready. Inspect session_failures or session_output_diagnostics, "
        "fix blockers, and rerun verification before finishing."
    )


def _session_audit_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ready", False):
        return (
            f"{base} Session audit is ready. Continue with any remaining requested work, "
            "or answer directly if the task is complete."
        )

    active_processes = _session_audit_process_labels(getattr(latest, "active_background_processes", []))
    if active_processes:
        return (
            f"{base} Session audit is not ready because background processes are still active. "
            "Use list_processes and read_process to inspect them, or stop_process if they are no longer needed: "
            f"{_format_next_action_items(active_processes)}. "
            "Then run session_verification or final_review before finishing."
        )

    blockers = [str(blocker).strip() for blocker in getattr(latest, "blockers", []) if str(blocker).strip()]
    if blockers:
        return (
            f"{base} Session audit is not ready. Fix audit blocker(s): {_format_next_action_items(blockers)}. "
            "Use session_verification or run_session_verification for verification blockers, "
            "session_failures or session_output_diagnostics for failure blockers, then rerun session_audit before finishing."
        )

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session audit could not confirm readiness. Inspect session_handoff, session_failures, "
            "or session_verification, then fix blockers before finishing."
        )

    return (
        f"{base} Session audit is not ready. Inspect the audit details, continue the incomplete work, "
        "and rerun session_audit or final_review before finishing."
    )


def _session_handoff_next_action_instruction(base: str, latest: Observation) -> str:
    handoff = str(getattr(latest, "handoff", "") or "")
    handoff_lower = handoff.lower()

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session handoff reports blockers. Use session_audit for a structured readiness check, "
            "then use session_verification, session_failures, or session_output_diagnostics to resolve the blocker(s) before finishing."
        )

    if "ready: yes" in handoff_lower or "status: ready" in handoff_lower:
        return (
            f"{base} Session handoff reports the recovered session is ready. "
            "Use its plan and verification sections to continue any remaining requested work, "
            "or answer directly if the task is complete."
        )

    return (
        f"{base} Use the session handoff sections to resume the task. "
        "If readiness is unclear, run session_audit or session_verification before finishing."
    )


def _session_plan_next_action_instruction(base: str, latest: Observation) -> str:
    plan = str(getattr(latest, "plan", "") or "")
    plan_lower = plan.lower()

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session plan could not be read. Use session_handoff or session_audit to recover context, "
            "then continue with the next useful action before finishing."
        )

    unfinished_markers = (
        "in_progress",
        "in progress",
        "pending",
        "todo",
        "not started",
        "blocked",
    )
    if any(marker in plan_lower for marker in unfinished_markers):
        return (
            f"{base} Session plan shows unfinished work. "
            "Continue the in-progress or next pending plan item, update_plan if the plan changed, "
            "then run session_verification or session_audit before finishing."
        )

    complete_markers = ("completed", "complete", "done")
    if any(marker in plan_lower for marker in complete_markers):
        return (
            f"{base} Session plan appears complete. "
            "Confirm readiness with session_verification or session_audit, "
            "or answer directly if the requested work is complete."
        )

    return (
        f"{base} Use the session plan to resume the task. "
        "Continue the next useful plan item, update_plan if needed, "
        "and run session_verification or session_audit before finishing."
    )


def _session_failures_next_action_instruction(base: str, latest: Observation) -> str:
    failure_count = int(getattr(latest, "failure_count", 0) or 0)
    if failure_count > 0:
        return (
            f"{base} Session failures reports {failure_count} failure event(s). "
            "Inspect the failure summary, use session_output_diagnostics or session_output_contexts for command-output failures, "
            "fix the blocker(s), then run session_verification or session_audit before finishing."
        )

    if getattr(latest, "ok", False):
        return (
            f"{base} Session failures reports no failure events. "
            "Continue with session_verification or session_audit to confirm readiness, "
            "or answer directly if the task is complete."
        )

    return (
        f"{base} Session failures could not be read. Use session_handoff or session_audit to recover context, "
        "then fix blockers before finishing."
    )


def _session_files_next_action_instruction(base: str, latest: Observation) -> str:
    file_count = int(getattr(latest, "file_count", 0) or 0)
    if file_count > 0:
        return (
            f"{base} Session files reports {file_count} file reference(s) from the recovered run. "
            "Inspect the listed files with read_file or read_file_context before editing, continue the relevant work, "
            "then run session_verification or session_audit before finishing."
        )

    if getattr(latest, "ok", False):
        return (
            f"{base} Session files found no file references. "
            "Use session_handoff or session_audit to recover the next task state, "
            "or answer directly if the task is complete."
        )

    return (
        f"{base} Session files could not be read. Use session_handoff or session_summary to recover context, "
        "then continue with the next useful action."
    )


SESSION_NEXT_ACTION_KINDS = {
    "session_verification",
    "session_audit",
    "session_handoff",
    "session_plan",
    "session_failures",
    "session_files",
}


def session_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "session_verification":
        return _session_verification_next_action_instruction(base, latest)
    if latest.kind == "session_audit":
        return _session_audit_next_action_instruction(base, latest)
    if latest.kind == "session_handoff":
        return _session_handoff_next_action_instruction(base, latest)
    if latest.kind == "session_plan":
        return _session_plan_next_action_instruction(base, latest)
    if latest.kind == "session_failures":
        return _session_failures_next_action_instruction(base, latest)
    if latest.kind == "session_files":
        return _session_files_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported session next-action kind: {latest.kind}")
