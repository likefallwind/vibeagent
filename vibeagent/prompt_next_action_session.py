from __future__ import annotations

from .prompt_next_action_session_formatting import (
    completion_blocker_labels,
    completion_next_action_labels,
    file_reference_labels,
    format_next_action_items,
    has_completion_blocker_signal,
    plan_item_labels,
    session_audit_process_labels,
    subagent_failure_labels,
    text_reports_ready,
    verification_command_labels,
)
from .prompt_next_action_session_reports import (
    session_commands_next_action_instruction,
    session_failures_next_action_instruction,
    session_files_next_action_instruction,
    session_plan_next_action_instruction,
    session_search_next_action_instruction,
    session_summary_next_action_instruction,
    session_transcript_next_action_instruction,
)
from .types import Observation


def _session_verification_next_action_instruction(base: str, latest: Observation) -> str:
    failed = verification_command_labels(getattr(latest, "failed_commands", []))
    pending = verification_command_labels(getattr(latest, "pending_commands", []))
    ready = getattr(latest, "ready", None)
    status = str(getattr(latest, "status", "") or "").strip().lower()
    subagent_failures = subagent_failure_labels(latest)

    if failed and pending:
        return (
            f"{base} Session verification reports failed and pending checks. "
            f"Use run_session_verification to rerun recorded verification checks first: "
            f"{format_next_action_items(failed + pending)}. "
            "If failures remain, inspect them with session_output_diagnostics or session_output_contexts, "
            "fix the code, and rerun verification before finishing."
        )

    if failed:
        return (
            f"{base} Session verification reports failed checks. "
            f"Use run_session_verification to rerun them first: {format_next_action_items(failed)}. "
            "If failures remain, inspect them with session_output_diagnostics or session_output_contexts, "
            "fix the code, and rerun verification before finishing."
        )

    if pending:
        return (
            f"{base} Session verification reports pending checks. "
            f"Use run_session_verification to run them before finishing: {format_next_action_items(pending)}."
        )

    if subagent_failures:
        return (
            f"{base} Session verification reports latest subagent failure(s): "
            f"{format_next_action_items(subagent_failures, max_items=4)}. "
            "Continue the necessary work in the main agent context, or retry once with a narrower delegated task; "
            "do not repeat the same delegation unchanged. Use session_failures or session_audit if more detail is needed, "
            "then rerun session_verification before finishing."
        )

    if ready is False or status == "blocked":
        return (
            f"{base} Session verification reports readiness is blocked, but no failed or pending check command was selected. "
            "Use session_audit or final_review to inspect the remaining blocker(s), fix them, "
            "then rerun session_verification before finishing."
        )

    if ready is True or status == "ready":
        return (
            f"{base} Session verification reports readiness is complete. Continue with any remaining requested work, "
            "or answer directly if the task is complete."
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
    subagent_failures = subagent_failure_labels(latest)
    if subagent_failures:
        return (
            f"{base} Session audit reports latest subagent failure(s): "
            f"{format_next_action_items(subagent_failures, max_items=4)}. "
            "Continue the necessary work in the main agent context, or retry once with a narrower delegated task; "
            "do not repeat the same delegation unchanged. Use session_failures or session_output_diagnostics if more detail is needed, "
            "then rerun session_audit before finishing."
        )

    if getattr(latest, "ready", False):
        return (
            f"{base} Session audit is ready. Continue with any remaining requested work, "
            "or answer directly if the task is complete."
        )

    active_processes = session_audit_process_labels(getattr(latest, "active_background_processes", []))
    if active_processes:
        return (
            f"{base} Session audit is not ready because background processes are still active. "
            "Use list_processes and read_process to inspect them, or stop_process if they are no longer needed: "
            f"{format_next_action_items(active_processes)}. "
            "Then run session_verification or final_review before finishing."
        )

    blockers = [str(blocker).strip() for blocker in getattr(latest, "blockers", []) if str(blocker).strip()]
    completion_blockers = completion_blocker_labels(latest)
    next_actions = completion_next_action_labels(latest)
    file_references = file_reference_labels(getattr(latest, "file_references", []))
    if blockers and has_completion_blocker_signal(blockers, latest):
        completion_details = completion_blockers or blockers
        recovery = (
            f" Follow latest completion next action(s): {format_next_action_items(next_actions, max_items=4)}."
            if next_actions
            else ""
        )
        return (
            f"{base} Session audit is not ready because completion blocker(s) remain. "
            f"Fix completion blocker(s): {format_next_action_items(completion_details, max_items=6)}.{recovery} "
            "Use session_plan for unfinished task-plan blockers, "
            "session_verification or run_session_verification for verification blockers, "
            "and session_failures or session_output_diagnostics for failure blockers; "
            "then rerun session_audit before finishing."
        )

    changed_file_blocker = any(
        "changed files exist" in blocker.lower() or "final_review" in blocker.lower() for blocker in blockers
    )
    if blockers and file_references and changed_file_blocker:
        return (
            f"{base} Session audit reports changed file(s): {format_next_action_items(file_references)}. "
            "Inspect the relevant file(s) with read_file or read_file_context, finish or review the edits, "
            "then run final_review or session_audit before finishing."
        )

    if blockers:
        return (
            f"{base} Session audit is not ready. Fix audit blocker(s): {format_next_action_items(blockers)}. "
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
    blockers = [str(blocker).strip() for blocker in getattr(latest, "blockers", []) if str(blocker).strip()]
    completion_blockers = completion_blocker_labels(latest)
    next_actions = completion_next_action_labels(latest)
    active_processes = session_audit_process_labels(getattr(latest, "active_background_processes", []))
    failed = verification_command_labels(getattr(latest, "failed_commands", []))
    pending = verification_command_labels(getattr(latest, "pending_commands", []))
    pending_plan_items = plan_item_labels(getattr(latest, "pending_plan_items", []))
    file_references = file_reference_labels(getattr(latest, "file_references", []))
    subagent_failures = subagent_failure_labels(latest)
    if subagent_failures:
        return (
            f"{base} Session handoff reports latest subagent failure(s): "
            f"{format_next_action_items(subagent_failures, max_items=4)}. "
            "Continue the necessary work in the main agent context, or retry once with a narrower delegated task; "
            "do not repeat the same delegation unchanged. Use session_failures or session_output_diagnostics if more detail is needed, "
            "then run session_audit or session_verification before finishing."
        )

    if getattr(latest, "ready", None) is True:
        return (
            f"{base} Session handoff reports the recovered session is ready. "
            "Use its plan and verification sections to continue any remaining requested work, "
            "or answer directly if the task is complete."
        )

    if active_processes:
        return (
            f"{base} Session handoff reports active background process(es). "
            "Use list_processes and read_process to inspect them, or stop_process if they are no longer needed: "
            f"{format_next_action_items(active_processes)}. "
            "Then run session_audit or session_verification before finishing."
        )

    if failed or pending:
        return (
            f"{base} Session handoff reports pending or failed verification checks. "
            f"Use run_session_verification to rerun recorded checks first: {format_next_action_items(failed + pending)}. "
            "If failures remain, inspect them with session_output_diagnostics or session_output_contexts, "
            "fix the code, and rerun session_audit before finishing."
        )

    if pending_plan_items:
        return (
            f"{base} Session handoff reports unfinished plan item(s): {format_next_action_items(pending_plan_items)}. "
            "Continue the in-progress or next pending plan item, use session_plan if more detail is needed, "
            "update_plan after progress, then run session_audit or session_verification before finishing."
        )

    if blockers and has_completion_blocker_signal(blockers, latest):
        completion_details = completion_blockers or blockers
        recovery = (
            f" Follow latest completion next action(s): {format_next_action_items(next_actions, max_items=4)}."
            if next_actions
            else ""
        )
        return (
            f"{base} Session handoff reports completion blocker(s). "
            f"Fix completion blocker(s): {format_next_action_items(completion_details, max_items=6)}.{recovery} "
            "Use session_plan for unfinished task-plan blockers, "
            "session_verification or run_session_verification for verification blockers, "
            "and session_failures or session_output_diagnostics for failure blockers before finishing."
        )

    changed_file_blocker = any(
        "changed files exist" in blocker.lower() or "final_review" in blocker.lower() for blocker in blockers
    )
    if blockers and file_references and changed_file_blocker:
        return (
            f"{base} Session handoff reports changed file(s): {format_next_action_items(file_references)}. "
            "Inspect the relevant file(s) with read_file or read_file_context, finish or review the edits, "
            "then run final_review or session_audit before finishing."
        )

    if blockers:
        return (
            f"{base} Session handoff reports blockers: {format_next_action_items(blockers)}. "
            "Use session_audit for a structured readiness check, "
            "then use session_verification, session_failures, or session_output_diagnostics to resolve the blocker(s) before finishing."
        )

    handoff = str(getattr(latest, "handoff", "") or "")

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session handoff could not be read. Use session_summary or session_audit to recover context, "
            "then continue the next useful action before finishing."
        )

    if text_reports_ready(handoff):
        return (
            f"{base} Session handoff reports the recovered session is ready. "
            "Use its plan and verification sections to continue any remaining requested work, "
            "or answer directly if the task is complete."
        )

    return (
        f"{base} Use the session handoff sections to resume the task. "
        "If readiness is unclear, run session_audit or session_verification before finishing."
    )


SESSION_NEXT_ACTION_KINDS = {
    "session_summary",
    "session_transcript",
    "session_search",
    "session_commands",
    "session_verification",
    "session_audit",
    "session_handoff",
    "session_plan",
    "session_failures",
    "session_files",
}


def session_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "session_summary":
        return session_summary_next_action_instruction(base, latest)
    if latest.kind == "session_transcript":
        return session_transcript_next_action_instruction(base, latest)
    if latest.kind == "session_search":
        return session_search_next_action_instruction(base, latest)
    if latest.kind == "session_commands":
        return session_commands_next_action_instruction(base, latest)
    if latest.kind == "session_verification":
        return _session_verification_next_action_instruction(base, latest)
    if latest.kind == "session_audit":
        return _session_audit_next_action_instruction(base, latest)
    if latest.kind == "session_handoff":
        return _session_handoff_next_action_instruction(base, latest)
    if latest.kind == "session_plan":
        return session_plan_next_action_instruction(base, latest)
    if latest.kind == "session_failures":
        return session_failures_next_action_instruction(base, latest)
    if latest.kind == "session_files":
        return session_files_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported session next-action kind: {latest.kind}")
