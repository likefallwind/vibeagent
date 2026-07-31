from __future__ import annotations

from dataclasses import replace

from .process_runtime import (
    attach_output_analysis_to_process_observation,
    check_stop_all_background_processes,
    check_stop_background_process,
    check_write_background_process,
    execute_run_command_item,
    list_background_processes,
    read_background_process,
    read_background_process_output_contexts,
    read_background_process_output_diagnostics,
    start_background_command,
    stop_all_background_processes,
    stop_background_process,
    wait_background_process,
    write_background_process,
)
from .cli_process_stdin import read_project_stdin_file
from .runtime_checks import (
    build_command_check_observation,
    build_command_preflight,
    check_http_url,
    check_tcp_port,
    fetch_http_url,
)
from .web_fetch import fetch_public_document
from .types import (
    AgentAction,
    CheckRunCommandsAction,
    CheckRunCommandsObservation,
    CheckStartCommandAction,
    CheckStartCommandObservation,
    CheckStopAllProcessesAction,
    CheckStopProcessAction,
    CheckWriteProcessAction,
    CheckWriteProcessObservation,
    CommandCheckAction,
    CommandResult,
    EnvironmentInfoAction,
    EnvironmentInfoObservation,
    HttpCheckAction,
    HttpFetchAction,
    WebFetchAction,
    ListProcessesAction,
    Observation,
    PortCheckAction,
    ProcessOutputContextsAction,
    ProcessOutputDiagnosticsAction,
    ReadProcessAction,
    RunCommandAction,
    RunCommandObservation,
    RunCommandsAction,
    RunCommandsObservation,
    RuntimeToolInfo,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    WaitProcessAction,
    WriteProcessAction,
    WriteProcessObservation,
)
from .workspace import RunWorkspace, read_environment_info


def _write_process_content(workspace: RunWorkspace, action: CheckWriteProcessAction | WriteProcessAction) -> str:
    if action.stdin_file is not None:
        return read_project_stdin_file(workspace.root, action.stdin_file, "stdin_file")
    return action.content or ""


def _write_process_file_error_observation(
    action: CheckWriteProcessAction | WriteProcessAction,
    error: ValueError,
) -> CheckWriteProcessObservation | WriteProcessObservation:
    observation_type = CheckWriteProcessObservation if isinstance(action, CheckWriteProcessAction) else WriteProcessObservation
    return observation_type(
        kind=action.type,
        process_id=action.process_id,
        pid=None,
        ok=False,
        running=False,
        command=None,
        cwd=None,
        content_chars=0,
        message=f"Cannot read stdin_file for process {action.process_id}: {error}",
    )


def execute_runtime_action(
    workspace: RunWorkspace,
    action: AgentAction,
    command_timeout_ms: int,
) -> Observation | None:
    if isinstance(action, CommandCheckAction):
        return build_command_check_observation(workspace, action.command, action.cwd)

    if isinstance(action, CheckRunCommandsAction):
        checks = [
            build_command_check_observation(workspace, item.command, item.cwd)
            for item in action.commands
        ]
        failed_count = sum(1 for check in checks if not check.ok)
        return CheckRunCommandsObservation(
            kind="check_run_commands",
            ok=failed_count == 0,
            checks=checks,
            message=f"Preflighted {len(checks)} command(s); {failed_count} failed.",
            commands=action.commands,
        )

    if isinstance(action, CheckStartCommandAction):
        result = build_command_preflight(workspace, action.command, action.cwd)
        return CheckStartCommandObservation(
            kind="check_start_command",
            ok=bool(result["ok"]),
            command=action.command,
            cwd=str(result["cwd"]),
            cwd_ok=bool(result["cwd_ok"]),
            blocked=bool(result["blocked"]),
            block_reason=result["block_reason"] if isinstance(result["block_reason"], str) else None,
            executable_available=bool(result["executable_available"]),
            missing_tool=result["missing_tool"] if isinstance(result["missing_tool"], str) else None,
            message=str(result["message"]),
        )

    if isinstance(action, PortCheckAction):
        return check_tcp_port(action.host, action.port, action.timeout_ms or 1_000)

    if isinstance(action, HttpCheckAction):
        timeout_ms = action.timeout_ms if action.timeout_ms is not None else 2_000
        max_body_chars = action.max_body_chars if action.max_body_chars is not None else 2_000
        return check_http_url(
            action.url,
            timeout_ms=timeout_ms,
            max_body_chars=max_body_chars,
            contains=action.contains,
            regex=action.regex,
        )

    if isinstance(action, HttpFetchAction):
        timeout_ms = action.timeout_ms if action.timeout_ms is not None else 5_000
        max_body_chars = action.max_body_chars if action.max_body_chars is not None else 12_000
        return fetch_http_url(action.url, timeout_ms=timeout_ms, max_body_chars=max_body_chars)

    if isinstance(action, WebFetchAction):
        timeout_ms = action.timeout_ms if action.timeout_ms is not None else 10_000
        max_text_chars = action.max_text_chars if action.max_text_chars is not None else 20_000
        observation = fetch_public_document(action.url, timeout_ms=timeout_ms, max_text_chars=max_text_chars)
        return replace(observation, prompt=action.prompt)

    if isinstance(action, EnvironmentInfoAction):
        try:
            info = read_environment_info(workspace)
            tools = [RuntimeToolInfo(**item) for item in info["tools"]]
            return EnvironmentInfoObservation(
                kind="environment_info",
                ok=True,
                project_root=str(info["project_root"]),
                python_version=str(info["python_version"]),
                python_executable=str(info["python_executable"]),
                platform=str(info["platform"]),
                is_git_repo=bool(info["is_git_repo"]),
                tools=tools,
                message=str(info["message"]),
            )
        except ValueError as error:
            return EnvironmentInfoObservation(
                kind="environment_info",
                ok=False,
                project_root=workspace.root.as_posix(),
                python_version="",
                python_executable="",
                platform="",
                is_git_repo=False,
                tools=[],
                message=str(error),
            )

    if isinstance(action, RunCommandAction):
        return RunCommandObservation(
            kind="run_command",
            result=execute_run_command_item(workspace, action, command_timeout_ms),
        )

    if isinstance(action, RunCommandsAction):
        results: list[CommandResult] = []
        stopped_early = False
        for item in action.commands:
            result = execute_run_command_item(workspace, item, command_timeout_ms)
            results.append(result)
            failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
            if failed and action.stop_on_failure:
                stopped_early = len(results) < len(action.commands)
                break
        ok = len(results) == len(action.commands) and all(
            result.exit_code == 0 and not result.timed_out for result in results
        )
        return RunCommandsObservation(
            kind="run_commands",
            results=results,
            ok=ok,
            stopped_early=stopped_early,
            message=f"Ran {len(results)}/{len(action.commands)} command(s); {'all passed' if ok else 'one or more failed'}.",
        )

    if isinstance(action, StartCommandAction):
        return start_background_command(
            workspace,
            action.command,
            action.cwd,
            max_output_chars=action.max_output_chars or 4_000,
        )

    if isinstance(action, ReadProcessAction):
        return attach_output_analysis_to_process_observation(
            workspace,
            read_background_process(
                workspace.root,
                action.process_id,
                max_output_chars=action.max_output_chars,
                output_filter=action.output_filter,
            ),
        )

    if isinstance(action, ProcessOutputContextsAction):
        return read_background_process_output_contexts(workspace, action)

    if isinstance(action, ProcessOutputDiagnosticsAction):
        return read_background_process_output_diagnostics(workspace, action)

    if isinstance(action, WaitProcessAction):
        return attach_output_analysis_to_process_observation(
            workspace,
            wait_background_process(
                workspace.root,
                action.process_id,
                timeout_ms=action.timeout_ms or 5_000,
                stdout_contains=action.stdout_contains,
                stderr_contains=action.stderr_contains,
                regex=action.regex,
                max_output_chars=action.max_output_chars,
            ),
        )

    if isinstance(action, CheckWriteProcessAction):
        try:
            content = _write_process_content(workspace, action)
        except ValueError as error:
            return _write_process_file_error_observation(action, error)
        return check_write_background_process(workspace.root, action.process_id, content)

    if isinstance(action, WriteProcessAction):
        try:
            content = _write_process_content(workspace, action)
        except ValueError as error:
            return _write_process_file_error_observation(action, error)
        return write_background_process(workspace.root, action.process_id, content)

    if isinstance(action, ListProcessesAction):
        return list_background_processes(workspace.root)

    if isinstance(action, CheckStopAllProcessesAction):
        return check_stop_all_background_processes(workspace.root)

    if isinstance(action, CheckStopProcessAction):
        return check_stop_background_process(workspace.root, action.process_id)

    if isinstance(action, StopAllProcessesAction):
        return stop_all_background_processes(workspace.root)

    if isinstance(action, StopProcessAction):
        return stop_background_process(workspace.root, action.process_id)

    return None
