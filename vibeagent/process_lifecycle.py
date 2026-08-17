from __future__ import annotations

from typing import Any

from .process_pty import remove_process_stdin
from .process_termination import signal_name, terminate_process
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
