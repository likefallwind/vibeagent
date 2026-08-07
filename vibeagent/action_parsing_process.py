from __future__ import annotations

from typing import Any

from .action_parsing_helpers import (
    ActionParseError,
    parse_optional_positive_int,
    parse_run_command_items,
)
from .action_parsing_process_fields import (
    parse_command,
    parse_optional_command_output_chars,
    parse_optional_description,
    parse_output_context_options,
    parse_process_id,
    parse_timeout_ms,
    parse_write_process_content,
)
from .action_parsing_process_read import PROCESS_READ_ACTION_TYPES, parse_process_read_action
from .types import (
    CheckStartCommandAction,
    CheckStopAllProcessesAction,
    CheckStopProcessAction,
    CheckWriteProcessAction,
    RunCommandAction,
    RunCommandsAction,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    WaitProcessAction,
    WriteProcessAction,
)


PROCESS_ACTION_TYPES = PROCESS_READ_ACTION_TYPES | {
    "run_command",
    "run_commands",
    "check_start_command",
    "start_command",
    "wait_process",
    "check_write_process",
    "write_process",
    "check_stop_all_processes",
    "check_stop_process",
    "stop_all_processes",
    "stop_process",
}


def parse_process_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in PROCESS_ACTION_TYPES:
        return None

    read_action = parse_process_read_action(action_type, value, raw)
    if read_action is not None:
        return read_action

    if action_type == "run_command":
        command = parse_command(value.get("command"), raw, "run_command")
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("run_command action cwd must be a string when provided.", raw)
        extract_output_contexts = value.get("extract_output_contexts", False)
        if not isinstance(extract_output_contexts, bool):
            raise ActionParseError("run_command action extract_output_contexts must be a boolean.", raw)
        extract_output_diagnostics = value.get("extract_output_diagnostics", False)
        if not isinstance(extract_output_diagnostics, bool):
            raise ActionParseError("run_command action extract_output_diagnostics must be a boolean.", raw)
        context_lines, max_contexts, max_bytes_per_context = parse_output_context_options(
            value,
            raw,
            default_context_lines=5,
        )
        max_diagnostics = parse_optional_positive_int(value.get("max_diagnostics", 50), "max_diagnostics", raw, maximum=200) or 50
        return RunCommandAction(
            type="run_command",
            command=command,
            timeout_ms=parse_timeout_ms(value.get("timeout_ms"), raw),
            cwd=cwd,
            description=parse_optional_description(value.get("description"), raw, "run_command"),
            max_output_chars=parse_optional_command_output_chars(value.get("max_output_chars"), raw),
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )

    if action_type == "run_commands":
        stop_on_failure = value.get("stop_on_failure", True)
        if not isinstance(stop_on_failure, bool):
            raise ActionParseError("run_commands action stop_on_failure must be a boolean when provided.", raw)
        return RunCommandsAction(
            type="run_commands",
            commands=parse_run_command_items(value.get("commands"), raw, "run_commands"),
            stop_on_failure=stop_on_failure,
        )

    if action_type == "check_start_command":
        command = parse_command(value.get("command"), raw, "check_start_command")
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("check_start_command action cwd must be a string when provided.", raw)
        return CheckStartCommandAction(type="check_start_command", command=command, cwd=cwd)

    if action_type == "start_command":
        command = parse_command(value.get("command"), raw, "start_command")
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ActionParseError("start_command action cwd must be a string when provided.", raw)
        return StartCommandAction(
            type="start_command",
            command=command,
            cwd=cwd,
            max_output_chars=parse_optional_command_output_chars(value.get("max_output_chars"), raw),
            description=parse_optional_description(value.get("description"), raw, "start_command"),
        )

    if action_type == "wait_process":
        process_id = parse_process_id(value.get("process_id"), raw, "wait_process")
        stdout_contains = value.get("stdout_contains")
        stderr_contains = value.get("stderr_contains")
        regex = value.get("regex", False)
        if stdout_contains is not None and (not isinstance(stdout_contains, str) or not stdout_contains.strip()):
            raise ActionParseError("wait_process action stdout_contains must be a non-empty string when provided.", raw)
        if stderr_contains is not None and (not isinstance(stderr_contains, str) or not stderr_contains.strip()):
            raise ActionParseError("wait_process action stderr_contains must be a non-empty string when provided.", raw)
        if not isinstance(regex, bool):
            raise ActionParseError("wait_process action regex must be a boolean when provided.", raw)
        return WaitProcessAction(
            type="wait_process",
            process_id=process_id,
            timeout_ms=parse_timeout_ms(value.get("timeout_ms"), raw),
            stdout_contains=stdout_contains,
            stderr_contains=stderr_contains,
            regex=regex,
            max_output_chars=parse_optional_command_output_chars(value.get("max_output_chars"), raw),
        )

    if action_type == "check_write_process":
        process_id = parse_process_id(value.get("process_id"), raw, "check_write_process")
        content, stdin_file = parse_write_process_content(value, raw, "check_write_process")
        return CheckWriteProcessAction(type="check_write_process", process_id=process_id, content=content, stdin_file=stdin_file)

    if action_type == "write_process":
        process_id = parse_process_id(value.get("process_id"), raw, "write_process")
        content, stdin_file = parse_write_process_content(value, raw, "write_process")
        return WriteProcessAction(type="write_process", process_id=process_id, content=content, stdin_file=stdin_file)

    if action_type == "check_stop_all_processes":
        return CheckStopAllProcessesAction(type="check_stop_all_processes")

    if action_type == "check_stop_process":
        return CheckStopProcessAction(
            type="check_stop_process",
            process_id=parse_process_id(value.get("process_id"), raw, "check_stop_process"),
        )

    if action_type == "stop_all_processes":
        return StopAllProcessesAction(type="stop_all_processes")

    if action_type == "stop_process":
        return StopProcessAction(
            type="stop_process",
            process_id=parse_process_id(value.get("process_id"), raw, "stop_process"),
        )

    raise AssertionError(f"Unhandled process action type: {action_type!r}")
