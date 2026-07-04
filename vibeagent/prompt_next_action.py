from __future__ import annotations

from .types import Observation


RECOVERY_SIGNAL_KINDS = {
    "output_diagnostics",
    "output_contexts",
}

SOURCE_CONTEXT_KINDS = {
    "read_file_context",
    "read_file_contexts",
}


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _observation_commands(values: object) -> list[str]:
    commands: list[str] = []
    if not isinstance(values, list):
        return commands
    for value in values:
        command = str(getattr(value, "command", "") or "").strip()
        if command:
            commands.append(command)
    return commands


def _running_process_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not getattr(value, "running", False):
            continue
        process_id = str(getattr(value, "process_id", "") or "").strip()
        command = str(getattr(value, "command", "") or "").strip()
        if process_id and command:
            labels.append(f"{process_id}: {command}")
        elif process_id:
            labels.append(process_id)
        elif command:
            labels.append(command)
    return labels


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


def _has_recovery_signal(observations: list[Observation]) -> bool:
    for observation in reversed(observations):
        if observation.kind in RECOVERY_SIGNAL_KINDS:
            return True
        if observation.kind == "run_command":
            result = observation.result
            return result.exit_code != 0 or result.timed_out
    return False


def _final_review_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ready", None) is not False:
        return f"{base} Use the final review report to decide whether to run verification, continue, or answer directly."

    running_processes = _running_process_labels(getattr(latest, "running_processes", []))
    if running_processes:
        return (
            f"{base} Final review is not ready because background processes are still running. "
            f"Inspect with list_processes or read_process if needed, then stop_process or stop_all_processes for: "
            f"{_format_next_action_items(running_processes)}. Rerun final_review before finishing."
        )

    focused_commands = _observation_commands(getattr(latest, "focused_test_commands", []))
    suggested_commands = _observation_commands(getattr(latest, "suggested_checks", []))
    if focused_commands and suggested_commands:
        return (
            f"{base} Final review is not ready and lists focused and suggested verification checks. "
            f"Run run_focused_test_commands or run_command first for: {_format_next_action_items(focused_commands)}. "
            f"Then run run_suggested_checks or run_command for broader checks: {_format_next_action_items(suggested_commands)}. "
            "Fix failures before finishing."
        )

    if suggested_commands:
        return (
            f"{base} Final review is not ready and lists suggested verification checks. "
            f"Run run_suggested_checks or run_command for: {_format_next_action_items(suggested_commands)}. "
            "Fix failures before finishing."
        )

    if focused_commands:
        return (
            f"{base} Final review is not ready and lists focused verification checks. "
            f"Run run_focused_test_commands or run_command for: {_format_next_action_items(focused_commands)}. "
            "Fix failures before finishing."
        )

    issues = [str(issue).strip() for issue in getattr(latest, "blocking_issues", []) if str(issue).strip()]
    if issues:
        return (
            f"{base} Final review is not ready. "
            f"Fix final review blocking issue(s) before finishing: {_format_next_action_items(issues)}."
        )

    return f"{base} Final review is not ready. Inspect its warnings and changed files, fix blockers, then rerun final_review before finishing."


def get_next_action_instruction(task: str, observations: list[Observation]) -> str:
    base = "Choose the next response: call a tool if needed, or answer directly if the task is complete."
    if not observations:
        return base

    latest = observations[-1]
    if latest.kind == "run_command":
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

    if latest.kind == "start_command":
        if latest.ok:
            return f"{base} The background command started. Use read_process or wait_process with process_id={latest.process_id} to inspect readiness or prompts."
        return f"{base} The background command did not start, so fix the concrete error before finishing."

    if latest.kind == "read_process":
        if latest.ok and latest.running:
            return f"{base} Use the process output to continue, write_process if the process is waiting for input, or stop_process if it is no longer needed."
        if latest.ok:
            return f"{base} The background command exited. Use its output to decide whether to fix issues or answer directly."
        return f"{base} The process could not be read, so use a valid process id or choose another useful action."

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

    if latest.kind == "final_review":
        return _final_review_next_action_instruction(base, latest)

    if latest.kind == "output_diagnostics":
        diagnostics = _diagnostic_labels(getattr(latest, "diagnostics", []))
        if diagnostics:
            return (
                f"{base} Output diagnostics found concrete issues. Inspect or edit the referenced source for: "
                f"{_format_next_action_items(diagnostics)}. Then rerun the failed command before finishing."
            )
        return (
            f"{base} Output diagnostics did not find concrete file references. Use the command output and any "
            "available contexts to inspect the likely source, fix the issue, and rerun the failed command before finishing."
        )

    if latest.kind == "output_contexts":
        contexts = _context_labels(getattr(latest, "contexts", []))
        if contexts:
            return (
                f"{base} Output contexts located source references. Inspect or edit the relevant code for: "
                f"{_format_next_action_items(contexts)}. Then rerun the failed command before finishing."
            )
        return (
            f"{base} Output contexts did not find source references. Use output_diagnostics or the command output "
            "to identify the failure, then fix it and rerun the failed command before finishing."
        )

    if latest.kind in SOURCE_CONTEXT_KINDS and _has_recovery_signal(observations[:-1]):
        contexts = _source_context_labels(latest)
        if contexts:
            return (
                f"{base} Source context was inspected after a failed command or diagnostic lookup. "
                f"Use it to edit the relevant code for: {_format_next_action_items(contexts)}. "
                "Then rerun the failed command before finishing."
            )
        return (
            f"{base} Source context was inspected after a failed command or diagnostic lookup. "
            "Use it to choose the edit, then rerun the failed command before finishing."
        )

    if latest.kind in {"python_check", "config_check"}:
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

    if latest.kind in {
        "read_file",
        "read_file_context",
        "read_file_contexts",
        "python_traceback",
        "tail_file",
        "read_files",
        "read_file_ranges",
        "file_info",
        "image_info",
        "repo_map",
        "python_symbols",
        "code_outline",
        "check_json_set",
        "check_json_remove",
        "check_json_patch",
        "python_dependencies",
        "code_dependencies",
        "code_references",
        "code_reference_contexts",
        "code_definitions",
        "code_rename_preview",
        "python_definitions",
        "python_calls",
        "python_call_graph",
        "python_references",
        "python_reference_contexts",
        "python_rename_preview",
        "tool_search",
        "project_commands",
        "related_tests",
        "focused_test_commands",
        "check_focused_test_commands",
        "git_branches",
        "check_git_fetch",
        "check_git_pull",
        "check_git_push",
        "check_git_restore",
        "git_conflicts",
        "git_diff_contexts",
        "git_stashes",
        "check_git_stash",
        "check_git_stash_apply",
        "check_git_stash_drop",
        "check_git_switch",
        "command_check",
        "check_run_commands",
        "check_suggested_checks",
        "check_focused_test_commands",
        "check_start_command",
        "port_check",
        "http_check",
        "http_fetch",
        "wait_process",
        "check_write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "environment_info",
        "list_files",
        "search",
        "search_contexts",
        "list_tree",
        "glob",
    }:
        return (
            f"{base} Do not repeat inspection unless you need specific missing information. "
            "If you already created the requested files, run one appropriate check or answer directly if the task is complete."
        )

    if latest.kind in {
        "git_info",
        "git_status",
        "git_conflicts",
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
        "git_changes",
        "review_changes",
        "suggest_checks",
        "check_suggested_checks",
        "tool_search",
        "project_commands",
        "related_tests",
        "focused_test_commands",
        "project_manifests",
        "project_instructions",
        "command_check",
        "check_start_command",
        "port_check",
        "http_check",
        "http_fetch",
        "wait_process",
        "check_write_process",
        "check_stop_all_processes",
        "check_stop_process",
        "environment_info",
        "git_diff",
        "git_diff_hunks",
        "git_diff_contexts",
        "git_log",
        "git_show",
        "git_blame",
        "session_summary",
        "session_plan",
        "session_transcript",
        "session_search",
        "session_commands",
        "session_output_contexts",
        "session_files",
        "session_failures",
        "session_verification",
        "run_session_verification",
        "session_audit",
        "session_handoff",
        "checkpoint_list",
        "checkpoint_show",
        "checkpoint_diff",
        "checkpoint_status",
        "check_checkpoint_restore",
        "check_checkpoint_delete",
        "check_checkpoint_prune",
    }:
        return f"{base} Use the repository or session information to decide whether to continue, run a check, or answer directly."

    if latest.kind in {
        "check_patch",
        "check_patches",
        "check_regex_replace",
        "check_write_file",
        "check_write_files",
        "check_edit_file",
        "check_multi_edit_file",
        "check_replace_python_definition",
        "check_replace_lines",
        "check_insert_lines",
        "check_append_file",
        "check_json_set",
        "check_json_remove",
        "check_json_patch",
        "check_delete_file",
        "check_delete_files",
        "check_move_file",
        "check_move_files",
        "check_copy_file",
        "check_copy_files",
        "check_move_dir",
        "check_move_dirs",
        "check_copy_dir",
        "check_copy_dirs",
        "check_create_dir",
        "check_create_dirs",
        "check_delete_empty_dir",
        "check_delete_empty_dirs",
        "check_set_executable",
        "check_git_stage",
        "check_git_unstage",
        "check_git_commit",
        "check_run_commands",
    }:
        if latest.ok:
            return f"{base} The dry-run succeeded. Apply it if the diff or validation result matches the requested change, or continue with the next required step."
        return f"{base} The dry-run failed, so fix the context or choose another edit tool before applying changes."

    if latest.kind in {"project_overview", "write_file", "write_files", "edit_file", "multi_edit_file", "replace_python_definition", "python_rename", "regex_replace", "json_set", "json_remove", "json_patch", "replace_lines", "insert_lines", "append_file", "patch_file", "patch_files", "delete_file", "delete_files", "move_file", "move_files", "copy_file", "copy_files", "move_dir", "move_dirs", "copy_dir", "copy_dirs", "create_dir", "create_dirs", "delete_empty_dir", "delete_empty_dirs", "set_executable", "git_fetch", "git_pull", "git_push", "git_restore", "git_stash", "git_stash_apply", "git_stash_drop", "git_switch", "git_stage", "git_unstage", "git_commit", "checkpoint_create", "checkpoint_restore", "checkpoint_delete", "checkpoint_prune", "run_commands", "run_suggested_checks", "run_focused_test_commands"}:
        return f"{base} Continue with the next required file, run one appropriate check, or answer directly if the task is complete."

    if latest.kind == "update_plan":
        return f"{base} Continue with the current in-progress plan item, or update the plan again if the work changed."

    return f"{base} If the task is complete, answer directly or use finish."
