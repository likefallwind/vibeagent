from __future__ import annotations

from .prompt_next_action_runtime_formatting import (
    check_failure_labels,
    context_labels,
    diagnostic_labels,
    failed_command_labels,
    format_next_action_items,
    not_run_selected_command_labels,
)
from .prompt_next_action_runtime_recovery import (
    SOURCE_CONTEXT_KINDS,
    process_exited_with_failure,
    recovery_rerun_target,
    source_context_labels,
)
from .types import Observation


BATCH_COMMAND_RESULT_KINDS = {
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
    "run_session_verification",
}

RUNTIME_NEXT_ACTION_KINDS = {
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
}


def _diagnostics_next_action_instruction(
    base: str,
    latest: Observation,
    *,
    label: str,
    output_source: str,
    rerun_target: str,
) -> str:
    diagnostics = diagnostic_labels(getattr(latest, "diagnostics", []))
    if diagnostics:
        return (
            f"{base} {label} diagnostics found concrete issues. "
            f"Inspect or edit the referenced source for: {format_next_action_items(diagnostics)}. "
            f"Then rerun the {rerun_target} before finishing."
        )
    return (
        f"{base} {label} diagnostics did not find concrete file references. "
        f"Use the {output_source} and any available contexts to inspect the likely source, fix the issue, "
        f"and rerun the {rerun_target} before finishing."
    )


def _contexts_next_action_instruction(
    base: str,
    latest: Observation,
    *,
    label: str,
    fallback_tool: str,
    output_source: str,
    rerun_target: str,
) -> str:
    contexts = context_labels(getattr(latest, "contexts", []))
    if contexts:
        return (
            f"{base} {label} contexts located source references. "
            f"Inspect or edit the relevant code for: {format_next_action_items(contexts)}. "
            f"Then rerun the {rerun_target} before finishing."
        )
    return (
        f"{base} {label} contexts did not find source references. "
        f"Use {fallback_tool} or the {output_source} to identify the failure, "
        f"then fix it and rerun the {rerun_target} before finishing."
    )


def _run_command_next_action_instruction(base: str, latest: Observation) -> str:
    result = latest.result
    if result.exit_code == 0 and not result.timed_out:
        return (
            f"{base} The latest command succeeded. If it checked the requested work, your next action must be "
            "a concise final answer. Do not run another check unless the output contains a concrete error."
        )
    output_issues = _command_result_output_issue_labels([result])
    if output_issues:
        return _inline_output_issue_instruction(
            base,
            "The latest command failed or timed out.",
            output_issues,
            "fix the issue, and rerun the failed command before finishing.",
        )
    return (
        f"{base} The latest command failed or timed out. Inspect its stdout/stderr for concrete errors; "
        "if the output names file:line locations or is noisy, use output_diagnostics, output_contexts, "
        "or python_traceback to locate the relevant source before editing. Fix the issue and rerun the "
        "failed command before finishing."
    )


def _start_command_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.ok:
        return (
            f"{base} The background command started. Use read_process or wait_process with "
            f"process_id={latest.process_id} to inspect readiness or prompts."
        )
    return f"{base} The background command did not start, so fix the concrete error before finishing."


def _read_process_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.ok and latest.running:
        return f"{base} Use the process output to continue, write_process if the process is waiting for input, or stop_process if it is no longer needed."
    if process_exited_with_failure(latest):
        output_issues = _inline_output_issue_labels(latest)
        if output_issues:
            return _inline_output_issue_instruction(
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
        return f"{base} The background command exited. Use its output to decide whether to fix issues or answer directly."
    return f"{base} The process could not be read, so use a valid process id or choose another useful action."


def _wait_process_next_action_instruction(base: str, latest: Observation) -> str:
    if process_exited_with_failure(latest):
        output_issues = _inline_output_issue_labels(latest)
        if output_issues:
            return _inline_output_issue_instruction(
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
    if getattr(latest, "matched", False):
        stream = str(getattr(latest, "matched_stream", "") or "process output")
        return (
            f"{base} The waited background command matched readiness output on {stream}. "
            "Continue with the dependent check or answer directly if the task is complete."
        )
    if getattr(latest, "running", False) or getattr(latest, "timed_out", False):
        return (
            f"{base} The background command is still running. Use read_process for current output, "
            "wait_process again for a specific readiness signal, or stop_process if it is no longer needed."
        )
    if getattr(latest, "ok", False):
        return f"{base} The waited background command exited. Use its output to decide whether to continue or answer directly."
    return f"{base} The wait_process check failed. Use a valid process id or inspect list_processes before continuing."


def _port_check_next_action_instruction(base: str, latest: Observation) -> str:
    host = str(getattr(latest, "host", "") or "host")
    port = int(getattr(latest, "port", 0) or 0)
    target = f"{host}:{port}" if port else host
    if getattr(latest, "reachable", False):
        return (
            f"{base} Port check reached {target}. Continue with http_check/http_fetch or the dependent workflow, "
            "or answer directly if readiness is proven."
        )
    return (
        f"{base} Port check could not reach {target}. Inspect the server process with list_processes/read_process, "
        "start the required command if needed, or fix the bind/port before retrying."
    )


def _http_check_next_action_instruction(base: str, latest: Observation) -> str:
    url = str(getattr(latest, "url", "") or "the URL")
    if getattr(latest, "reachable", False) and getattr(latest, "matched", False):
        return f"{base} HTTP check reached {url} and matched the expected pattern. Continue the dependent check or answer directly if complete."
    if getattr(latest, "reachable", False):
        status = getattr(latest, "status", None)
        return (
            f"{base} HTTP check reached {url}"
            f"{' with status ' + str(status) if status is not None else ''} but did not prove readiness. "
            "Inspect the response body, adjust the pattern, or continue with http_fetch/read_process to diagnose."
        )
    return (
        f"{base} HTTP check could not reach {url}. Inspect server logs with read_process, verify the port with port_check, "
        "or start/fix the service before retrying."
    )


def _http_fetch_next_action_instruction(base: str, latest: Observation) -> str:
    url = str(getattr(latest, "url", "") or "the URL")
    if not getattr(latest, "reachable", False):
        return (
            f"{base} HTTP fetch could not reach {url}. Inspect the server process, port, or error before retrying."
        )
    if not getattr(latest, "ok", False):
        status = getattr(latest, "status", None)
        return (
            f"{base} HTTP fetch reached {url}"
            f"{' with status ' + str(status) if status is not None else ''}. "
            "Use the response body and server logs to fix the issue, then rerun the relevant HTTP check."
        )
    if getattr(latest, "body_truncated", False):
        return f"{base} HTTP fetch succeeded but the body was truncated. Re-fetch a narrower endpoint or inspect the relevant source/logs."
    return f"{base} HTTP fetch succeeded. Use the response to decide the next fix, dependent check, or final answer."


def _check_run_commands_next_action_instruction(base: str, latest: Observation) -> str:
    checks = getattr(latest, "checks", [])
    blocked = [check for check in checks if getattr(check, "blocked", False)]
    missing = [check for check in checks if not getattr(check, "executable_available", True)]
    if not getattr(latest, "ok", False):
        if blocked:
            commands = [str(getattr(check, "command", "") or "").strip() for check in blocked]
            return (
                f"{base} Command preflight found blocked command(s): {format_next_action_items([item for item in commands if item])}. "
                "Choose a safer command or inspect the block reason before requesting execution."
            )
        if missing:
            tools = [str(getattr(check, "missing_tool", "") or "").strip() for check in missing]
            return (
                f"{base} Command preflight found unavailable executable(s): {format_next_action_items([item for item in tools if item])}. "
                "Use an available project command or inspect environment_info before requesting execution."
            )
        return f"{base} Command preflight failed. Fix the command, cwd, or executable choice before running it."
    return f"{base} Command preflight succeeded. Use run_commands only if executing the checked commands is still required."


def _python_or_config_check_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return (
            f"{base} The latest {latest.kind} passed. Continue with the next required check, "
            "or answer directly if the requested work is complete."
        )
    failures = check_failure_labels(getattr(latest, "files", []))
    if failures:
        return (
            f"{base} The latest {latest.kind} failed. Fix the reported issue(s) before finishing: "
            f"{format_next_action_items(failures)}."
        )
    return f"{base} The latest {latest.kind} failed. Inspect its message, fix the issue, and rerun the check before finishing."


def _batch_command_result_next_action_instruction(base: str, latest: Observation) -> str:
    results = getattr(latest, "results", [])
    failed_commands = failed_command_labels(results)
    if failed_commands:
        output_issues = _command_result_output_issue_labels(results)
        if output_issues:
            return _inline_output_issue_instruction(
                base,
                f"The latest {latest.kind} had failed command(s).",
                output_issues,
                (
                    "fix the issue(s), and rerun the failed command(s) before finishing: "
                    f"{format_next_action_items(failed_commands)}."
                ),
            )
        return (
            f"{base} The latest {latest.kind} had failed command(s). Inspect stdout/stderr; "
            "use output_diagnostics, output_contexts, or python_traceback for noisy output with file references. "
            f"Fix the issue(s) and rerun the failed command(s) before finishing: {format_next_action_items(failed_commands)}."
        )
    return (
        f"{base} The latest {latest.kind} completed without failed commands. "
        "Continue with the next required check, or answer directly if the requested work is complete."
    )


def _inline_output_issue_labels(value: object) -> list[str]:
    diagnostics = _diagnostic_source_labels(getattr(value, "output_diagnostics", []))
    if diagnostics:
        return diagnostics
    return context_labels(getattr(value, "output_contexts", []))


def _diagnostic_source_labels(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    labels: list[str] = []
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        if not path:
            continue
        labels.extend(diagnostic_labels([value]))
    return labels


def _inline_output_issue_instruction(
    base: str,
    intro: str,
    output_issues: list[str],
    resolution: str,
) -> str:
    return (
        f"{base} {intro} Inline output analysis identified referenced source location(s): "
        f"{format_next_action_items(output_issues)}. Inspect or edit the referenced source, {resolution}"
    )


def _command_result_output_issue_labels(results: object) -> list[str]:
    if not isinstance(results, list):
        return []
    labels: list[str] = []
    seen: set[str] = set()
    for result in results:
        if not failed_command_labels([result]):
            continue
        for label in _inline_output_issue_labels(result):
            if label and label not in seen:
                seen.add(label)
                labels.append(label)
    return labels


def _run_session_verification_next_action_instruction(base: str, latest: Observation) -> str:
    selected_count = int(getattr(latest, "selected_count", 0) or 0)
    results = getattr(latest, "results", [])
    failed_commands = failed_command_labels(results)
    if failed_commands:
        stopped = " The run stopped early after the first failure." if getattr(latest, "stopped_early", False) else ""
        not_run = not_run_selected_command_labels(getattr(latest, "selected_commands", []), len(results or []))
        not_run_detail = (
            f" Not-yet-run selected check(s): {format_next_action_items(not_run)}."
            if not_run
            else ""
        )
        output_issues = _command_result_output_issue_labels(results)
        if output_issues:
            return _inline_output_issue_instruction(
                base,
                f"run_session_verification reran recorded verification check(s) and found failed command(s).{stopped}",
                output_issues,
                (
                    "fix the issue(s), then rerun run_session_verification or session_verification before finishing: "
                    f"{format_next_action_items(failed_commands)}.{not_run_detail}"
                ),
            )
        return (
            f"{base} run_session_verification reran recorded verification check(s) and found failed command(s)."
            f"{stopped} Inspect stdout/stderr, use session_output_diagnostics or session_output_contexts for noisy output, "
            f"fix the issue(s), then rerun run_session_verification or session_verification before finishing: "
            f"{format_next_action_items(failed_commands)}.{not_run_detail}"
        )
    if selected_count > 0 and getattr(latest, "ok", False):
        return (
            f"{base} run_session_verification reran {selected_count} recorded verification check(s), and they passed. "
            "Run session_audit or final_review to confirm readiness, or answer directly if the task is complete."
        )
    if selected_count == 0:
        return (
            f"{base} run_session_verification did not select any pending or failed check. "
            "Use session_verification to inspect recorded verification state, or session_audit if readiness is unclear."
        )
    return (
        f"{base} run_session_verification could not confirm the recorded checks passed. "
        "Inspect its message and output, then use session_verification or session_audit before finishing."
    )


def runtime_next_action_instruction(base: str, observations: list[Observation]) -> str | None:
    latest = observations[-1]

    if latest.kind == "run_command":
        return _run_command_next_action_instruction(base, latest)
    if latest.kind == "start_command":
        return _start_command_next_action_instruction(base, latest)
    if latest.kind == "read_process":
        return _read_process_next_action_instruction(base, latest)
    if latest.kind == "list_processes":
        return f"{base} Use a listed process id with read_process, wait_process, write_process, or stop_process; use check_stop_all_processes if cleaning up all background commands."
    if latest.kind == "check_write_process":
        if latest.ok:
            return f"{base} The process can receive stdin. Use write_process only if sending that input is necessary."
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
    if latest.kind in {"command_check", "check_start_command"}:
        if getattr(latest, "blocked", False):
            return f"{base} Command preflight was blocked. Choose a safer command or inspect the block reason before requesting execution."
        if not getattr(latest, "executable_available", True):
            return f"{base} Command preflight found an unavailable executable. Use an available project command or inspect environment_info before requesting execution."
        if getattr(latest, "ok", False):
            return f"{base} Command preflight succeeded. Run the checked command only if execution is still required."
        return f"{base} Command preflight failed. Fix the command or cwd before requesting execution."
    if latest.kind == "check_run_commands":
        return _check_run_commands_next_action_instruction(base, latest)
    if latest.kind in {"check_stop_process", "check_stop_all_processes"}:
        if getattr(latest, "ok", False):
            return f"{base} Stop preflight succeeded. Use the matching stop tool only if cleanup is intended."
        return f"{base} Stop preflight failed. Inspect list_processes or choose a valid process id before stopping."

    if latest.kind == "output_diagnostics":
        return _diagnostics_next_action_instruction(
            base,
            latest,
            label="Output",
            output_source="command output",
            rerun_target="failed command",
        )
    if latest.kind == "output_contexts":
        return _contexts_next_action_instruction(
            base,
            latest,
            label="Output",
            fallback_tool="output_diagnostics",
            output_source="command output",
            rerun_target="failed command",
        )
    if latest.kind == "process_output_diagnostics":
        return _diagnostics_next_action_instruction(
            base,
            latest,
            label="Process output",
            output_source="process output",
            rerun_target="relevant check",
        )
    if latest.kind == "process_output_contexts":
        return _contexts_next_action_instruction(
            base,
            latest,
            label="Process output",
            fallback_tool="process_output_diagnostics",
            output_source="process output",
            rerun_target="relevant check",
        )
    if latest.kind == "session_output_diagnostics":
        return _diagnostics_next_action_instruction(
            base,
            latest,
            label="Session output",
            output_source="session command output",
            rerun_target="relevant check",
        )
    if latest.kind == "session_output_contexts":
        return _contexts_next_action_instruction(
            base,
            latest,
            label="Session output",
            fallback_tool="session_output_diagnostics",
            output_source="session command output",
            rerun_target="relevant check",
        )

    rerun_target = recovery_rerun_target(observations[:-1], BATCH_COMMAND_RESULT_KINDS) if latest.kind in SOURCE_CONTEXT_KINDS else None
    if latest.kind in SOURCE_CONTEXT_KINDS and rerun_target:
        contexts = source_context_labels(latest)
        if contexts:
            return (
                f"{base} Source context was inspected after a failed command or diagnostic lookup. "
                f"Use it to edit the relevant code for: {format_next_action_items(contexts)}. "
                f"Then rerun the {rerun_target} before finishing."
            )
        return (
            f"{base} Source context was inspected after a failed command or diagnostic lookup. "
            f"Use it to choose the edit, then rerun the {rerun_target} before finishing."
        )

    if latest.kind in {"python_check", "config_check"}:
        return _python_or_config_check_next_action_instruction(base, latest)

    if latest.kind == "run_session_verification":
        return _run_session_verification_next_action_instruction(base, latest)

    if latest.kind in BATCH_COMMAND_RESULT_KINDS:
        return _batch_command_result_next_action_instruction(base, latest)

    return None
