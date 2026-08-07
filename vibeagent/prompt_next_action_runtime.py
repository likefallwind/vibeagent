from __future__ import annotations

from .prompt_next_action_runtime_commands import (
    batch_command_result_next_action_instruction,
    check_run_commands_next_action_instruction,
    python_or_config_check_next_action_instruction,
    run_command_next_action_instruction,
    run_session_verification_next_action_instruction,
)
from .prompt_next_action_runtime_formatting import format_next_action_items, inline_output_issue_instruction, inline_output_issue_labels
from .prompt_next_action_runtime_network import (
    _http_check_next_action_instruction,
    _http_fetch_next_action_instruction,
    _port_check_next_action_instruction,
    _web_fetch_next_action_instruction,
)
from .prompt_next_action_runtime_output import (
    BATCH_COMMAND_RESULT_KINDS,
    command_output_rerun_target,
    contexts_next_action_instruction,
    diagnostics_next_action_instruction,
    process_output_rerun_target,
    recovery_not_run_detail,
    session_output_rerun_target,
)
from .prompt_next_action_runtime_recovery import (
    SOURCE_CONTEXT_KINDS,
    process_exited_with_failure,
    recovery_rerun_target,
    source_context_labels,
)
from .types import Observation


RUNTIME_NEXT_ACTION_KINDS = {
    "Bash",
    "BashOutput",
    "KillBash",
    "run_command",
    "start_command",
    "read_process",
    "list_processes",
    "check_write_process",
    "write_process",
    "stop_process",
    "stop_all_processes",
    "wait_process",
    "command_check",
    "check_start_command",
    "check_run_commands",
    "check_stop_process",
    "check_stop_all_processes",
    "output_diagnostics",
    "output_contexts",
    "process_output_diagnostics",
    "process_output_contexts",
    "session_output_diagnostics",
    "session_output_contexts",
    "python_check",
    "config_check",
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
    "run_session_verification",
    "port_check",
    "http_check",
    "http_fetch",
    "web_fetch",
}


def _start_command_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.ok:
        return (
            f"{base} The background command started. Use read_process or wait_process with "
            f"process_id={latest.process_id} to inspect readiness or prompts."
        )
    return f"{base} The background command did not start, so fix the concrete error before finishing."


def _read_process_next_action_instruction(base: str, latest: Observation) -> str:
    output_issues = inline_output_issue_labels(latest)
    if latest.ok and latest.running:
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The background command is still running, but inline output analysis found source-linked issue(s).",
                output_issues,
                "decide whether they are relevant, edit or fix if needed, and rerun or continue only after confirming they are non-blocking.",
            )
        return (
            f"{base} Use the process output to continue, check_write_process then write_process if the process is "
            "waiting for input, prefer stdin_file for large or project-file-backed input, or stop_process if it is no longer needed."
        )
    if process_exited_with_failure(latest):
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The background command exited with a failure.",
                output_issues,
                "fix the issue, and rerun the relevant check before finishing.",
            )
        return (
            f"{base} The background command exited with a failure. Inspect stdout/stderr; use "
            f"process_output_diagnostics or process_output_contexts with process_id={latest.process_id} "
            "when the output is noisy or names file:line references. Fix the issue and rerun the relevant check before finishing."
        )
    if latest.ok:
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The background command exited successfully, but inline output analysis found source-linked issue(s).",
                output_issues,
                "decide whether they are relevant, edit or fix if needed, and rerun or continue only after confirming they are non-blocking.",
            )
        return f"{base} The background command exited. Use its output to decide whether to fix issues or answer directly."
    return f"{base} The process could not be read, so use a valid process id or choose another useful action."


def _wait_process_next_action_instruction(base: str, latest: Observation) -> str:
    if process_exited_with_failure(latest):
        output_issues = inline_output_issue_labels(latest)
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The waited background command exited with a failure.",
                output_issues,
                "fix the issue, and rerun the relevant check before finishing.",
            )
        return (
            f"{base} The waited background command exited with a failure. Inspect stdout/stderr; use "
            f"process_output_diagnostics or process_output_contexts with process_id={latest.process_id} "
            "when the output is noisy or names file:line references. Fix the issue and rerun the relevant check before finishing."
        )
    output_issues = inline_output_issue_labels(latest)
    if getattr(latest, "matched", False):
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The waited background command matched readiness output, but inline output analysis found source-linked issue(s).",
                output_issues,
                "decide whether they are relevant, edit or fix if needed, and rerun or continue only after confirming they are non-blocking.",
            )
        stream = str(getattr(latest, "matched_stream", "") or "process output")
        return (
            f"{base} The waited background command matched readiness output on {stream}. "
            "Continue with the dependent check or answer directly if the task is complete."
        )
    if getattr(latest, "running", False) or getattr(latest, "timed_out", False):
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The background command is still running, but inline output analysis found source-linked issue(s).",
                output_issues,
                "decide whether they are relevant, edit or fix if needed, and rerun or continue only after confirming they are non-blocking.",
            )
        return (
            f"{base} The background command is still running. Use read_process for current output, "
            "wait_process again for a specific readiness signal, or stop_process if it is no longer needed."
        )
    if getattr(latest, "ok", False):
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The waited background command exited successfully, but inline output analysis found source-linked issue(s).",
                output_issues,
                "decide whether they are relevant, edit or fix if needed, and rerun or continue only after confirming they are non-blocking.",
            )
        return f"{base} The waited background command exited. Use its output to decide whether to continue or answer directly."
    return f"{base} The wait_process check failed. Use a valid process id or inspect list_processes before continuing."


def runtime_next_action_instruction(base: str, observations: list[Observation]) -> str | None:
    latest = observations[-1]

    if latest.kind == "run_command":
        return run_command_next_action_instruction(base, latest)
    if latest.kind == "start_command":
        return _start_command_next_action_instruction(base, latest)
    if latest.kind == "read_process":
        return _read_process_next_action_instruction(base, latest)
    if latest.kind == "list_processes":
        return f"{base} Use a listed process id with read_process, wait_process, write_process, or stop_process; use check_stop_all_processes if cleaning up all background commands."
    if latest.kind == "check_write_process":
        if latest.ok:
            return (
                f"{base} The process can receive stdin. Use write_process only if sending that input is necessary, "
                "and use stdin_file instead of inline content for large or existing project-file input."
            )
        return f"{base} The process cannot receive stdin, so inspect its output or choose another useful action."
    if latest.kind == "write_process":
        if latest.ok:
            return f"{base} Input was sent. Use wait_process or read_process to inspect the result."
        return f"{base} Input was not sent, so inspect the process state or choose another useful action."
    if latest.kind == "stop_process":
        return f"{base} The background process was stopped. Continue with the next check or answer directly if the task is complete."
    if latest.kind == "stop_all_processes":
        return f"{base} All tracked background processes were stopped. Continue with the next check or answer directly if the task is complete."
    if latest.kind == "wait_process":
        return _wait_process_next_action_instruction(base, latest)
    if latest.kind == "port_check":
        return _port_check_next_action_instruction(base, latest)
    if latest.kind == "http_check":
        return _http_check_next_action_instruction(base, latest)
    if latest.kind == "http_fetch":
        return _http_fetch_next_action_instruction(base, latest)
    if latest.kind == "web_fetch":
        return _web_fetch_next_action_instruction(base, latest)
    if latest.kind in {"command_check", "check_start_command"}:
        if getattr(latest, "blocked", False):
            return f"{base} Command preflight was blocked. Choose a safer command or inspect the block reason before requesting execution."
        if not getattr(latest, "executable_available", True):
            return f"{base} Command preflight found an unavailable executable. Use an available project command or inspect environment_info before requesting execution."
        if getattr(latest, "ok", False):
            return f"{base} Command preflight succeeded. Run the checked command only if execution is still required."
        return f"{base} Command preflight failed. Fix the command or cwd before requesting execution."
    if latest.kind == "check_run_commands":
        return check_run_commands_next_action_instruction(base, latest)
    if latest.kind in {"check_stop_process", "check_stop_all_processes"}:
        if getattr(latest, "ok", False):
            return f"{base} Stop preflight succeeded. Use the matching stop tool only if cleanup is intended."
        return f"{base} Stop preflight failed. Inspect list_processes or choose a valid process id before stopping."

    if latest.kind == "output_diagnostics":
        previous_observations = observations[:-1]
        return diagnostics_next_action_instruction(
            base,
            latest,
            label="Output",
            output_source="command output",
            rerun_target=command_output_rerun_target(previous_observations),
            recovery_detail=recovery_not_run_detail(previous_observations),
        )
    if latest.kind == "output_contexts":
        previous_observations = observations[:-1]
        return contexts_next_action_instruction(
            base,
            latest,
            label="Output",
            fallback_tool="output_diagnostics",
            output_source="command output",
            rerun_target=command_output_rerun_target(previous_observations),
            recovery_detail=recovery_not_run_detail(previous_observations),
        )
    if latest.kind == "process_output_diagnostics":
        return diagnostics_next_action_instruction(
            base,
            latest,
            label="Process output",
            output_source="process output",
            rerun_target=process_output_rerun_target(observations[:-1]),
        )
    if latest.kind == "process_output_contexts":
        return contexts_next_action_instruction(
            base,
            latest,
            label="Process output",
            fallback_tool="process_output_diagnostics",
            output_source="process output",
            rerun_target=process_output_rerun_target(observations[:-1]),
        )
    if latest.kind == "session_output_diagnostics":
        previous_observations = observations[:-1]
        return diagnostics_next_action_instruction(
            base,
            latest,
            label="Session output",
            output_source="session command output",
            rerun_target=session_output_rerun_target(previous_observations),
            recovery_detail=recovery_not_run_detail(previous_observations),
        )
    if latest.kind == "session_output_contexts":
        previous_observations = observations[:-1]
        return contexts_next_action_instruction(
            base,
            latest,
            label="Session output",
            fallback_tool="session_output_diagnostics",
            output_source="session command output",
            rerun_target=session_output_rerun_target(previous_observations),
            recovery_detail=recovery_not_run_detail(previous_observations),
        )

    previous_observations = observations[:-1]
    rerun_target = (
        recovery_rerun_target(previous_observations, BATCH_COMMAND_RESULT_KINDS)
        if latest.kind in SOURCE_CONTEXT_KINDS
        else None
    )
    if latest.kind in SOURCE_CONTEXT_KINDS and rerun_target:
        contexts = source_context_labels(latest)
        not_run_text = recovery_not_run_detail(previous_observations)
        if contexts:
            return (
                f"{base} Source context was inspected after a failed command or diagnostic lookup. "
                f"Use it to edit the relevant code for: {format_next_action_items(contexts)}. "
                f"Then rerun the {rerun_target} before finishing.{not_run_text}"
            )
        return (
            f"{base} Source context was inspected after a failed command or diagnostic lookup. "
            f"Use it to choose the edit, then rerun the {rerun_target} before finishing.{not_run_text}"
        )

    if latest.kind in {"python_check", "config_check"}:
        return python_or_config_check_next_action_instruction(base, latest)

    if latest.kind == "run_session_verification":
        return run_session_verification_next_action_instruction(base, latest)

    if latest.kind in BATCH_COMMAND_RESULT_KINDS:
        return batch_command_result_next_action_instruction(base, latest)

    return None
