from __future__ import annotations

import json
import os
import shlex
import sys
import uuid
from pathlib import Path

from .action_process_types import MonitorWebSocketSource
from .process_runtime import start_background_command
from .types import StartCommandObservation
from .websocket_monitor_safety import resolve_public_websocket_endpoint
from .workspace_core import RunWorkspace


def start_websocket_monitor_process(
    workspace: RunWorkspace,
    source: MonitorWebSocketSource,
) -> StartCommandObservation:
    try:
        resolve_public_websocket_endpoint(source)
        config_path = _write_worker_config(workspace, source)
    except (OSError, ValueError) as error:
        return _failure_observation(source.url, str(error))
    command = shlex.join(
        (
            sys.executable,
            "-m",
            "vibeagent.websocket_monitor_worker",
            config_path.as_posix(),
        )
    )
    started = start_background_command(workspace, command, max_output_chars=20_000)
    if not started.ok:
        config_path.unlink(missing_ok=True)
    return started


def _write_worker_config(
    workspace: RunWorkspace,
    source: MonitorWebSocketSource,
) -> Path:
    directory = workspace.session_dir / "monitor-configs"
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError("Monitor config path is not a regular directory.")
    directory.mkdir(parents=True, exist_ok=True)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Monitor config path is not a regular directory.")
    path = directory / f"{uuid.uuid4().hex}.json"
    payload = {"url": source.url, "protocols": list(source.protocols)}
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False)
        stream.write("\n")
    if os.name != "nt":
        path.chmod(0o600)
    return path


def _failure_observation(url: str, message: str) -> StartCommandObservation:
    return StartCommandObservation(
        kind="start_command",
        process_id="",
        pid=None,
        command=f"WebSocket monitor for {url}",
        cwd=".",
        ok=False,
        message=message,
        stdout_path="",
        stderr_path="",
    )


__all__ = ["start_websocket_monitor_process"]
