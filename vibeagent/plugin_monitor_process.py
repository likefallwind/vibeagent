from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from threading import Thread

from .plugin_monitor_config import PluginMonitorConfig
from .process_lifecycle import terminate_process


MAX_MONITOR_LINE_CHARS = 8_000
MAX_MONITOR_STDERR_CHARS = 16_000
MonitorOutput = Callable[[PluginMonitorConfig, str], None]
MonitorExit = Callable[["RunningPluginMonitor", int], None]


@dataclass
class RunningPluginMonitor:
    config: PluginMonitorConfig
    process: subprocess.Popen[str]
    stdout_thread: Thread | None = None
    stderr_thread: Thread | None = None
    stderr_tail: str = ""
    closing: bool = False

    @classmethod
    def launch(
        cls,
        config: PluginMonitorConfig,
        argv: tuple[str, ...],
        cwd: Path,
        environment: dict[str, str],
    ) -> RunningPluginMonitor:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            start_new_session=os.name != "nt",
            env=environment,
        )
        return cls(config=config, process=process)

    def start_readers(self, on_output: MonitorOutput, on_exit: MonitorExit) -> None:
        self.stderr_thread = Thread(target=self._read_stderr, daemon=True)
        self.stdout_thread = Thread(
            target=self._read_stdout,
            args=(on_output, on_exit),
            daemon=True,
        )
        self.stderr_thread.start()
        self.stdout_thread.start()

    def close(self) -> None:
        self.closing = True
        if self.process.poll() is None:
            terminate_process(self.process)
        for thread in (self.stdout_thread, self.stderr_thread):
            if thread is not None:
                thread.join(timeout=1)
        for stream in (self.process.stdout, self.process.stderr):
            if stream is not None and not stream.closed:
                stream.close()

    def _read_stdout(self, on_output: MonitorOutput, on_exit: MonitorExit) -> None:
        stream = self.process.stdout
        assert stream is not None
        buffer = ""
        try:
            while True:
                chunk = stream.readline(MAX_MONITOR_LINE_CHARS + 1)
                if not chunk:
                    break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    _emit_line(self.config, line.rstrip("\r"), on_output)
                while len(buffer) > MAX_MONITOR_LINE_CHARS:
                    _emit_line(self.config, buffer[:MAX_MONITOR_LINE_CHARS], on_output)
                    buffer = buffer[MAX_MONITOR_LINE_CHARS:]
            if buffer:
                _emit_line(self.config, buffer, on_output)
        finally:
            return_code = self.process.wait()
            # Exit reporting must observe stderr written immediately before the process exits.
            if self.stderr_thread is not None:
                self.stderr_thread.join(timeout=1)
            try:
                on_exit(self, return_code)
            finally:
                stream.close()

    def _read_stderr(self) -> None:
        stream = self.process.stderr
        assert stream is not None
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                self.stderr_tail = (self.stderr_tail + chunk)[-MAX_MONITOR_STDERR_CHARS:]
        finally:
            stream.close()


def _emit_line(
    config: PluginMonitorConfig, line: str, on_output: MonitorOutput
) -> None:
    if line:
        on_output(config, line[:MAX_MONITOR_LINE_CHARS])


__all__ = ["RunningPluginMonitor"]
