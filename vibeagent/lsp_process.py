from __future__ import annotations

from collections import deque
import os
import re
import subprocess
from threading import Lock, Thread
from typing import BinaryIO

from .lsp_config import LspServerConfig


ENV_REFERENCE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class LspProcess:
    def __init__(self, config: LspServerConfig) -> None:
        self.config = config
        self.process: subprocess.Popen[bytes] | None = None
        self._write_lock = Lock()
        self._stderr: deque[str] = deque(maxlen=20)

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> BinaryIO:
        environment = dict(os.environ)
        for key, value in self.config.env.items():
            environment[key] = ENV_REFERENCE_PATTERN.sub(
                lambda match: os.environ.get(match.group(1), ""), value
            )
        try:
            process = subprocess.Popen(
                self.config.argv,
                cwd=self.config.workspace_folder,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            raise ValueError(f"Could not start LSP server {self.config.name}: {error}") from error
        self.process = process
        assert process.stdout is not None and process.stderr is not None
        Thread(target=self._stderr_loop, args=(process.stderr,), daemon=True).start()
        return process.stdout

    def write(self, payload: bytes) -> None:
        process = self.process
        if process is None or process.stdin is None or process.poll() is not None:
            raise ValueError(f"LSP server {self.config.name} is not running.")
        with self._write_lock:
            try:
                process.stdin.write(payload)
                process.stdin.flush()
            except (BrokenPipeError, OSError) as error:
                raise ValueError(f"Could not write to LSP server {self.config.name}: {error}") from error

    def stop(self) -> None:
        process = self.process
        self.process = None
        if process is None:
            return
        try:
            process.wait(timeout=self.config.shutdown_timeout_ms / 1000)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    def stderr_summary(self) -> str:
        return " ".join(self._stderr)[-2_000:]

    def _stderr_loop(self, stream: BinaryIO) -> None:
        while True:
            line = stream.readline(2_001)
            if not line:
                return
            self._stderr.append(line.decode("utf-8", errors="replace").strip()[:2_000])


__all__ = ["LspProcess"]
