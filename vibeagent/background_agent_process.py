from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import threading
from uuid import uuid4

from .background_agent_config import (
    BackgroundAgentConfig,
    background_agent_config_path,
)
from .background_agent_store import (
    background_agent_runtime_root,
    ensure_private_directory,
    open_private_log,
    open_private_log_append,
    write_private_json,
)
from .background_agent_memory import BACKGROUND_AGENT_MEMORY_LIMIT_ENV
from .background_agent_memory_monitor import start_background_agent_memory_monitor
from .tool_memory_limit import (
    ToolMemoryLaunch,
    cleanup_tool_memory_launch,
    prepare_memory_launch,
)
from .tool_memory_systemd import stop_tool_memory_unit, wait_for_tool_memory_service


@dataclass(frozen=True)
class BackgroundAgentSpawn:
    process: subprocess.Popen[str]
    memory_launch: ToolMemoryLaunch | None


def spawn_background_agent_worker(
    config: BackgroundAgentConfig,
    *,
    invocation_root: Path,
    stdout_path: Path,
    stderr_path: Path,
    exit_code_path: Path,
    initial_argv: list[str] | None,
    append_logs: bool,
    memory_limit_bytes: int | None,
) -> BackgroundAgentSpawn:
    launch_root = ensure_private_directory(
        background_agent_runtime_root(config.project_root) / "launch"
    )
    payload_path = launch_root / f"{config.agent_id}-{uuid4().hex[:12]}.json"
    config_path = background_agent_config_path(
        config.project_root,
        config.agent_id,
    ).as_posix()
    payload: dict[str, object] = {
        "schemaVersion": 2,
        "agentId": config.agent_id,
        "projectRoot": config.project_root.as_posix(),
        "configPath": config_path,
        "exitCodePath": exit_code_path.as_posix(),
    }
    if initial_argv is not None:
        payload["initialArgv"] = initial_argv
    write_private_json(payload_path, payload, exclusive=True)
    try:
        stdout_handle = (
            open_private_log_append(stdout_path)
            if append_logs
            else open_private_log(stdout_path)
        )
    except Exception:
        payload_path.unlink(missing_ok=True)
        raise
    try:
        stderr_handle = (
            open_private_log_append(stderr_path)
            if append_logs
            else open_private_log(stderr_path)
        )
    except Exception:
        stdout_handle.close()
        payload_path.unlink(missing_ok=True)
        raise
    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"
    environment["VIBEAGENT_BACKGROUND_AGENT_ID"] = config.agent_id
    environment["VIBEAGENT_BACKGROUND_AGENT_CONFIG"] = config_path
    worker_argv = [
        sys.executable,
        "-m",
        "vibeagent.background_agent_worker",
        payload_path.as_posix(),
    ]
    memory_launch: ToolMemoryLaunch | None = None
    try:
        if memory_limit_bytes is not None:
            memory_launch = prepare_memory_launch(
                worker_argv,
                invocation_root,
                environment,
                limit_bytes=memory_limit_bytes,
                requirement=BACKGROUND_AGENT_MEMORY_LIMIT_ENV,
            )
        process = subprocess.Popen(
            memory_launch.argv if memory_launch is not None else worker_argv,
            cwd=invocation_root,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=os.name != "nt",
            env=environment,
        )
    except Exception:
        cleanup_tool_memory_launch(memory_launch)
        payload_path.unlink(missing_ok=True)
        raise
    finally:
        stdout_handle.close()
        stderr_handle.close()
    try:
        memory_start_error = wait_for_tool_memory_service(process, memory_launch)
    except BaseException:
        _stop_memory_launch(process, memory_launch, environment)
        raise
    if memory_start_error is not None:
        _stop_memory_launch(process, memory_launch, environment)
        raise RuntimeError(memory_start_error)
    if memory_launch is not None:
        try:
            start_background_agent_memory_monitor(
                config.project_root,
                config.agent_id,
                memory_launch,
                process,
                stderr_path=stderr_path,
                exit_code_path=exit_code_path,
            )
        except Exception:
            _stop_memory_launch(process, memory_launch, environment)
            raise
    return BackgroundAgentSpawn(process=process, memory_launch=memory_launch)


def _stop_memory_launch(
    process: subprocess.Popen[str],
    launch: ToolMemoryLaunch | None,
    environment: dict[str, str],
) -> None:
    if launch is not None:
        stop_tool_memory_unit(
            launch.unit,
            environment,
            systemctl=launch.systemctl,
        )
    if process.poll() is None:
        process.kill()
        process.wait()
    cleanup_tool_memory_launch(launch)


def start_background_process_reaper(process: subprocess.Popen[str]) -> None:
    threading.Thread(
        target=process.wait,
        name=f"vibeagent-background-agent-{process.pid}",
        daemon=True,
    ).start()


__all__ = [
    "BackgroundAgentSpawn",
    "spawn_background_agent_worker",
    "start_background_process_reaper",
]
