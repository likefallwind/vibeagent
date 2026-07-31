from __future__ import annotations

from .prompt_next_action_session_formatting import (
    completion_next_action_labels,
    file_reference_labels,
    format_next_action_items,
    session_plan_appears_complete,
    session_plan_has_unfinished_work,
    subagent_failure_labels,
    text_reports_ready,
)
from .types import Observation


def session_summary_next_action_instruction(base: str, latest: Observation) -> str:
    summary = str(getattr(latest, "summary", "") or "")

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session summary could not be read. Use session_handoff or session_search to recover context, "
            "then continue with the next useful action before finishing."
        )

    next_actions = completion_next_action_labels(latest)
    if next_actions:
        return (
            f"{base} Session summary reports latest completion next action(s): "
            f"{format_next_action_items(next_actions, max_items=4)}. "
            "Follow them before trying to finish again."
        )

    subagent_failures = subagent_failure_labels(latest)
    if subagent_failures:
        return (
            f"{base} Session summary reports latest subagent failure(s): "
            f"{format_next_action_items(subagent_failures, max_items=4)}. "
            "Continue the necessary work in the main agent context, or retry once with a narrower delegated task; "
            "do not repeat the same delegation unchanged. Run session_audit or session_verification before finishing."
        )

    if text_reports_ready(summary):
        return (
            f"{base} Session summary reports the recovered session is ready. "
            "Confirm any requested deliverable is present, or answer directly if the task is complete."
        )

    if summary.strip():
        return (
            f"{base} Session summary gives recovered task context. "
            "Use it to choose the next concrete work item, inspect session_plan or session_files if exact state is needed, "
            "then run session_verification or session_audit before finishing."
        )

    return (
        f"{base} Session summary is empty. Use session_handoff, session_plan, or session_transcript to recover context, "
        "then continue with the next useful action before finishing."
    )


def session_transcript_next_action_instruction(base: str, latest: Observation) -> str:
    transcript = str(getattr(latest, "transcript", "") or "")

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session transcript could not be read. Use session_summary or session_handoff to recover context, "
            "then continue with the next useful action before finishing."
        )

    if transcript.strip():
        return (
            f"{base} Session transcript gives detailed prior turn history. "
            "Continue from the latest unfinished action, use session_plan, session_files, or session_commands for targeted follow-up if needed, "
            "then run session_verification or session_audit before finishing."
        )

    return (
        f"{base} Session transcript is empty. Use session_summary, session_plan, or session_handoff to recover context, "
        "or answer directly if the task is complete."
    )


def session_search_next_action_instruction(base: str, latest: Observation) -> str:
    total_matches = int(getattr(latest, "total_matches", 0) or 0)

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session search could not be read. Use session_summary or session_handoff to recover context, "
            "then continue with the next useful action before finishing."
        )

    if total_matches > 0:
        return (
            f"{base} Session search found {total_matches} matching event(s). "
            "Use the matches to narrow the resumed context; inspect session_transcript, session_commands, or session_files if more detail is needed, "
            "then continue the relevant work and verify before finishing."
        )

    return (
        f"{base} Session search found no matches. Use session_summary or session_handoff for broader recovery, "
        "or answer directly if the task is complete."
    )


def session_commands_next_action_instruction(base: str, latest: Observation) -> str:
    command_count = int(getattr(latest, "command_count", 0) or 0)

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session commands could not be read. Use session_summary or session_handoff to recover context, "
            "then continue with the next useful action before finishing."
        )

    if command_count > 0:
        return (
            f"{base} Session commands reports {command_count} command event(s). "
            "Use the command history to identify failed or pending checks; inspect session_output_diagnostics or session_output_contexts for failures, "
            "or use session_verification or session_audit to confirm readiness before finishing."
        )

    return (
        f"{base} Session commands found no command history. Use session_plan, session_files, or session_handoff to recover task state, "
        "or answer directly if the task is complete."
    )


def session_plan_next_action_instruction(base: str, latest: Observation) -> str:
    plan = str(getattr(latest, "plan", "") or "")

    if not getattr(latest, "ok", False):
        return (
            f"{base} Session plan could not be read. Use session_handoff or session_audit to recover context, "
            "then continue with the next useful action before finishing."
        )

    if session_plan_has_unfinished_work(plan):
        return (
            f"{base} Session plan shows unfinished work. "
            "Continue the in-progress or next pending plan item, update_plan if the plan changed, "
            "then run session_verification or session_audit before finishing."
        )

    if session_plan_appears_complete(plan):
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


def session_failures_next_action_instruction(base: str, latest: Observation) -> str:
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


def session_files_next_action_instruction(base: str, latest: Observation) -> str:
    file_count = int(getattr(latest, "file_count", 0) or 0)
    file_references = file_reference_labels(getattr(latest, "file_references", []))
    if file_count > 0:
        file_detail = (
            f" Inspect these file(s) first: {format_next_action_items(file_references)}."
            if file_references
            else ""
        )
        return (
            f"{base} Session files reports {file_count} file reference(s) from the recovered run. "
            "Inspect the listed files with read_file or read_file_context before editing."
            f"{file_detail} "
            "Then continue the relevant work, "
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
