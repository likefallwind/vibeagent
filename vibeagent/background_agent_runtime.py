from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid

from .background_agent_store import (
    as_process_record,
    background_agent_record_path,
    background_agent_runtime_root,
    background_agent_view,
    background_agent_view_payload,
    ensure_background_agent_runtime_root,
    ensure_private_directory,
    get_background_agent,
    list_background_agents,
    open_private_log,
    write_background_agent_record,
    write_private_json,
    write_private_text,
)
from .background_agent_types import (
    DEFAULT_BACKGROUND_AGENT_LOG_CHARS,
    MAX_BACKGROUND_AGENT_LOG_CHARS,
    BackgroundAgentRecord,
    BackgroundAgentView,
)
from .process_registry import read_process_start_ticks, terminate_persistent_process
from .redaction import redact_sensitive_text


def launch_background_agent(
    project_root: Path,
    invocation_root: Path,
    argv: list[str],
    *,
    task_summary: str,
    session_name: str | None,
) -> BackgroundAgentView:
    root = project_root.resolve()
    invocation = invocation_root.resolve()
    agent_id = uuid.uuid4().hex[:12]
    runtime_root = ensure_background_agent_runtime_root(root)
    logs_root = ensure_private_directory(runtime_root / "logs")
    launch_root = ensure_private_directory(runtime_root / "launch")
    stdout_path = logs_root / f"{agent_id}.stdout.log"
    stderr_path = logs_root / f"{agent_id}.stderr.log"
    exit_code_path = logs_root / f"{agent_id}.exitcode"
    stopped_path = logs_root / f"{agent_id}.stopped"
    payload_path = launch_root / f"{agent_id}.json"

    child_argv = _without_background_flag(argv)
    if not _contains_option(child_argv, {"-p", "--print"}):
        child_argv.insert(0, "--print")
    effective_session_name = session_name
    if effective_session_name is None and not _resumes_existing_session(child_argv):
        effective_session_name = f"background-{agent_id}"
        child_argv[0:0] = ["--name", effective_session_name]

    write_private_json(
        payload_path,
        {
            "schemaVersion": 1,
            "argv": child_argv,
            "exitCodePath": exit_code_path.as_posix(),
        },
        exclusive=True,
    )
    write_private_text(exit_code_path, "", exclusive=True)
    stdout_handle = open_private_log(stdout_path)
    stderr_handle = open_private_log(stderr_path)
    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"
    environment["VIBEAGENT_BACKGROUND_AGENT_ID"] = agent_id
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "vibeagent.background_agent_worker",
                payload_path.as_posix(),
            ],
            cwd=invocation,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=os.name != "nt",
            env=environment,
        )
    except Exception:
        stdout_handle.close()
        stderr_handle.close()
        _remove_paths(payload_path, stdout_path, stderr_path, exit_code_path)
        raise
    else:
        stdout_handle.close()
        stderr_handle.close()

    record = BackgroundAgentRecord(
        id=agent_id,
        project_root=root,
        invocation_root=invocation,
        pid=process.pid,
        start_ticks=read_process_start_ticks(process.pid),
        started_at=datetime.now(UTC).isoformat(timespec="seconds"),
        task_summary=_task_summary(task_summary),
        session_name=effective_session_name,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exit_code_path=exit_code_path,
        stopped_path=stopped_path,
    )
    try:
        write_background_agent_record(record)
    except Exception:
        terminate_persistent_process(as_process_record(record))
        _start_process_reaper(process)
        _remove_paths(payload_path, stdout_path, stderr_path, exit_code_path)
        raise
    _start_process_reaper(process)
    return background_agent_view(record)


def stop_background_agent(project_root: Path, agent_id: str) -> BackgroundAgentView | None:
    view = get_background_agent(project_root, agent_id)
    if view is None:
        return None
    if view.status == "running":
        terminate_persistent_process(as_process_record(view.record))
        write_private_text(view.record.stopped_path, "stopped\n", exclusive=False)
    return background_agent_view(view.record)


def remove_background_agent(project_root: Path, agent_id: str) -> tuple[bool, str]:
    view = get_background_agent(project_root, agent_id)
    if view is None:
        return False, f"Background agent not found: {agent_id}"
    if view.status == "running":
        return False, f"Background agent is still running: {agent_id}"
    record_path = background_agent_record_path(project_root.resolve(), agent_id)
    _remove_paths(
        view.record.stdout_path,
        view.record.stderr_path,
        view.record.exit_code_path,
        view.record.stopped_path,
        record_path,
    )
    return True, f"Removed background agent {agent_id}. Session transcript was preserved."


def read_background_agent_logs(
    project_root: Path,
    agent_id: str,
    *,
    max_chars: int = DEFAULT_BACKGROUND_AGENT_LOG_CHARS,
) -> tuple[BackgroundAgentView | None, str, str]:
    view = get_background_agent(project_root, agent_id)
    if view is None:
        return None, "", ""
    bounded = max(1_000, min(max_chars, MAX_BACKGROUND_AGENT_LOG_CHARS))
    return (
        view,
        _read_text_tail(view.record.stdout_path, bounded),
        _read_text_tail(view.record.stderr_path, bounded),
    )


def _task_summary(task: str) -> str:
    return " ".join(redact_sensitive_text(task).split())[:500]


def _without_background_flag(argv: list[str]) -> list[str]:
    result: list[str] = []
    options = True
    for item in argv:
        if options and item == "--":
            options = False
            result.append(item)
        elif options and item in {"--background", "--bg"}:
            continue
        else:
            result.append(item)
    return result


def _contains_option(argv: list[str], names: set[str]) -> bool:
    for item in argv:
        if item == "--":
            return False
        if item in names or any(
            item.startswith(f"{name}=") for name in names if name.startswith("--")
        ):
            return True
    return False


def _resumes_existing_session(argv: list[str]) -> bool:
    return _contains_option(
        argv,
        {"-c", "--continue", "-r", "--resume", "--session-id", "--compact"},
    )


def _read_text_tail(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) <= max_chars:
        return text
    return f"[truncated to last {max_chars} chars]\n{text[-max_chars:]}"


def _remove_paths(*paths: Path | None) -> None:
    for path in paths:
        if path is not None:
            path.unlink(missing_ok=True)


def _start_process_reaper(process: subprocess.Popen[str]) -> None:
    threading.Thread(
        target=process.wait,
        name=f"vibeagent-background-agent-{process.pid}",
        daemon=True,
    ).start()


__all__ = [
    "BackgroundAgentRecord",
    "BackgroundAgentView",
    "background_agent_record_path",
    "background_agent_runtime_root",
    "background_agent_view_payload",
    "get_background_agent",
    "launch_background_agent",
    "list_background_agents",
    "read_background_agent_logs",
    "remove_background_agent",
    "stop_background_agent",
]
