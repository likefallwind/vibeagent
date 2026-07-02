from __future__ import annotations

import os
import signal
import subprocess
from typing import Any


def close_background_handles(background: Any) -> None:
    handles = [background.stdout_handle, background.stderr_handle, background.process.stdin]
    for handle in handles:
        if handle is not None and not handle.closed:
            handle.close()


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
