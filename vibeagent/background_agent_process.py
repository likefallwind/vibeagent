from __future__ import annotations

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


def spawn_background_agent_worker(
    config: BackgroundAgentConfig,
    *,
    invocation_root: Path,
    stdout_path: Path,
    stderr_path: Path,
    exit_code_path: Path,
    initial_argv: list[str] | None,
    append_logs: bool,
) -> subprocess.Popen[str]:
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
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "vibeagent.background_agent_worker",
                payload_path.as_posix(),
            ],
            cwd=invocation_root,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=os.name != "nt",
            env=environment,
        )
    except Exception:
        payload_path.unlink(missing_ok=True)
        raise
    finally:
        stdout_handle.close()
        stderr_handle.close()
    return process


def start_background_process_reaper(process: subprocess.Popen[str]) -> None:
    threading.Thread(
        target=process.wait,
        name=f"vibeagent-background-agent-{process.pid}",
        daemon=True,
    ).start()


__all__ = ["spawn_background_agent_worker", "start_background_process_reaper"]
