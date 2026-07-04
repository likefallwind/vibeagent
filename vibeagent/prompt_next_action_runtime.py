from __future__ import annotations

from .types import Observation


RECOVERY_SIGNAL_KINDS = {
    "output_diagnostics",
    "output_contexts",
    "process_output_diagnostics",
    "process_output_contexts",
}

PROCESS_RECOVERY_SIGNAL_KINDS = {
    "process_output_diagnostics",
    "process_output_contexts",
}

SESSION_RECOVERY_SIGNAL_KINDS = {
    "session_output_diagnostics",
    "session_output_contexts",
}

SOURCE_CONTEXT_KINDS = {
    "read_file_context",
    "read_file_contexts",
}

BATCH_COMMAND_RESULT_KINDS = {
    "run_commands",
    "run_suggested_checks",
    "run_focused_test_commands",
    "run_session_verification",
}


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _diagnostic_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        column = getattr(value, "column", None)
        text = str(getattr(value, "text", "") or "").strip()
        severity = str(getattr(value, "severity", "") or "").strip()
        location = path
        if path and isinstance(line, int):
            location = f"{path}:{line}"
            if isinstance(column, int):
                location = f"{location}:{column}"
        if location and text:
            labels.append(f"{location} {severity}: {text}" if severity else f"{location}: {text}")
        elif location:
            labels.append(location)
        elif text:
            labels.append(f"{severity}: {text}" if severity else text)
    return labels


def _context_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        column = getattr(value, "column", None)
        raw = str(getattr(value, "raw", "") or "").strip()
        ok = getattr(value, "ok", True)
        label = path
        if path and isinstance(line, int):
            label = f"{path}:{line}"
            if isinstance(column, int):
                label = f"{label}:{column}"
        if not label:
            label = raw
        if label:
            labels.append(label if ok else f"{label} (context unavailable)")
    return labels


def _check_failure_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if getattr(value, "ok", True):
            continue
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        column = getattr(value, "column", None)
        message = str(getattr(value, "message", "") or "").strip()
        label = path
        if path and isinstance(line, int):
            label = f"{path}:{line}"
            if isinstance(column, int):
                label = f"{label}:{column}"
        if label and message:
            labels.append(f"{label}: {message}")
        elif label:
            labels.append(label)
        elif message:
            labels.append(message)
    return labels


def _command_result_failed(result: object) -> bool:
    return bool(getattr(result, "timed_out", False)) or getattr(result, "exit_code", 0) != 0


def _process_exited_with_failure(observation: Observation) -> bool:
    if not getattr(observation, "ok", False) or getattr(observation, "running", False):
        return False
    exit_code = getattr(observation, "exit_code", 0)
    signal = getattr(observation, "signal", None)
    return bool(signal) or (exit_code is not None and exit_code != 0)


def _failed_command_labels(results: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(results, list):
        return labels
    for result in results:
        if not _command_result_failed(result):
            continue
        command = str(getattr(result, "command", "") or "").strip()
        cwd = str(getattr(result, "cwd", ".") or ".").strip()
        exit_code = getattr(result, "exit_code", None)
        timed_out = bool(getattr(result, "timed_out", False))
        status = "timed out" if timed_out else f"exit {exit_code}"
        if command:
            labels.append(f"{command} (cwd={cwd}, {status})")
        else:
            labels.append(status)
    return labels


def _source_context_labels(observation: Observation) -> list[str]:
    if observation.kind == "read_file_context":
        path = str(getattr(observation, "path", "") or "").strip()
        line = getattr(observation, "line", None)
        if path and isinstance(line, int):
            label = f"{path}:{line}"
        else:
            label = path
        if label and not getattr(observation, "ok", True):
            return [f"{label} (context unavailable)"]
        return [label] if label else []
    if observation.kind == "read_file_contexts":
        return _context_labels(getattr(observation, "contexts", []))
    return []


def _recovery_rerun_target(observations: list[Observation]) -> str | None:
    for observation in reversed(observations):
        if observation.kind in SESSION_RECOVERY_SIGNAL_KINDS:
            return "relevant check"
        if observation.kind in PROCESS_RECOVERY_SIGNAL_KINDS:
            return "relevant check"
        if observation.kind in RECOVERY_SIGNAL_KINDS:
            return "failed command"
        if observation.kind in {"read_process", "wait_process"} and _process_exited_with_failure(observation):
            return "relevant check"
        if observation.kind in BATCH_COMMAND_RESULT_KINDS:
            if _failed_command_labels(getattr(observation, "results", [])):
                return "failed command"
        if observation.kind == "run_command":
            result = observation.result
            if result.exit_code != 0 or result.timed_out:
                return "failed command"
    return None


def _diagnostics_next_action_instruction(
    base: str,
    latest: Observation,
    *,
    label: str,
    output_source: str,
    rerun_target: str,
) -> str:
    diagnostics = _diagnostic_labels(getattr(latest, "diagnostics", []))
    if diagnostics:
        return (
            f"{base} {label} diagnostics found concrete issues. "
            f"Inspect or edit the referenced source for: {_format_next_action_items(diagnostics)}. "
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
    contexts = _context_labels(getattr(latest, "contexts", []))
    if contexts:
        return (
            f"{base} {label} contexts located source references. "
            f"Inspect or edit the relevant code for: {_format_next_action_items(contexts)}. "
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
    if _process_exited_with_failure(latest):
        return (
            f"{base} The background command exited with a failure. Inspect stdout/stderr; use "
            f"process_output_diagnostics or process_output_contexts with process_id={latest.process_id} "
            "when the output is noisy or names file:line references. Fix the issue and rerun the relevant check before finishing."
        )
    if latest.ok:
        return f"{base} The background command exited. Use its output to decide whether to fix issues or answer directly."
    return f"{base} The process could not be read, so use a valid process id or choose another useful action."


def _wait_process_next_action_instruction(base: str, latest: Observation) -> str:
    if _process_exited_with_failure(latest):
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


def _check_run_commands_next_action_instruction(base: str, latest: Observation) -> str:
    checks = getattr(latest, "checks", [])
    blocked = [check for check in checks if getattr(check, "blocked", False)]
    missing = [check for check in checks if not getattr(check, "executable_available", True)]
    if not getattr(latest, "ok", False):
        if blocked:
            commands = [str(getattr(check, "command", "") or "").strip() for check in blocked]
            return (
                f"{base} Command preflight found blocked command(s): {_format_next_action_items([item for item in commands if item])}. "
                "Choose a safer command or inspect the block reason before requesting execution."
            )
        if missing:
            tools = [str(getattr(check, "missing_tool", "") or "").strip() for check in missing]
            return (
                f"{base} Command preflight found unavailable executable(s): {_format_next_action_items([item for item in tools if item])}. "
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
    failures = _check_failure_labels(getattr(latest, "files", []))
    if failures:
        return (
            f"{base} The latest {latest.kind} failed. Fix the reported issue(s) before finishing: "
            f"{_format_next_action_items(failures)}."
        )
    return f"{base} The latest {latest.kind} failed. Inspect its message, fix the issue, and rerun the check before finishing."


def _batch_command_result_next_action_instruction(base: str, latest: Observation) -> str:
    failed_commands = _failed_command_labels(getattr(latest, "results", []))
    if failed_commands:
        return (
            f"{base} The latest {latest.kind} had failed command(s). Inspect stdout/stderr; "
            "use output_diagnostics, output_contexts, or python_traceback for noisy output with file references. "
            f"Fix the issue(s) and rerun the failed command(s) before finishing: {_format_next_action_items(failed_commands)}."
        )
    return (
        f"{base} The latest {latest.kind} completed without failed commands. "
        "Continue with the next required check, or answer directly if the requested work is complete."
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

    rerun_target = _recovery_rerun_target(observations[:-1]) if latest.kind in SOURCE_CONTEXT_KINDS else None
    if latest.kind in SOURCE_CONTEXT_KINDS and rerun_target:
        contexts = _source_context_labels(latest)
        if contexts:
            return (
                f"{base} Source context was inspected after a failed command or diagnostic lookup. "
                f"Use it to edit the relevant code for: {_format_next_action_items(contexts)}. "
                f"Then rerun the {rerun_target} before finishing."
            )
        return (
            f"{base} Source context was inspected after a failed command or diagnostic lookup. "
            f"Use it to choose the edit, then rerun the {rerun_target} before finishing."
        )

    if latest.kind in {"python_check", "config_check"}:
        return _python_or_config_check_next_action_instruction(base, latest)

    if latest.kind in BATCH_COMMAND_RESULT_KINDS:
        return _batch_command_result_next_action_instruction(base, latest)

    return None
