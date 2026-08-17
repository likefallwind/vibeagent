from __future__ import annotations

import os
import signal
import subprocess
from typing import Any

from .process_pty import remove_process_stdin
from .tool_memory_limit import cleanup_tool_memory_launch
from .tool_memory_systemd import stop_tool_memory_unit


def close_background_handles(background: Any) -> None:
    diagnostics_done = getattr(background, "memory_diagnostics_done", None)
    if diagnostics_done is not None and background.process.poll() is not None:
        diagnostics_done.wait(timeout=6.0)
    handles = [background.stdout_handle, background.stderr_handle, background.process.stdin]
    for handle in handles:
        if handle is not None and not handle.closed:
            handle.close()
    if background.process.poll() is not None:
        remove_process_stdin(getattr(background, "stdin_path", None))
    cleanup_tool_memory_launch(getattr(background, "memory_launch", None))


def terminate_background_process(background: Any) -> None:
    memory_launch = getattr(background, "memory_launch", None)
    if memory_launch is not None:
        stop_tool_memory_unit(
            memory_launch.unit,
            systemctl=memory_launch.systemctl,
        )
    if background.process.poll() is None:
        terminate_process(background.process)


def terminate_process(process: subprocess.Popen[str]) -> None:
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return


def signal_name(returncode: int) -> str | None:
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return None
