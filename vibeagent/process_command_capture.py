from __future__ import annotations

from dataclasses import dataclass, field
import subprocess
import tempfile
from threading import Event, Lock, Thread
import time
from typing import BinaryIO, Callable, TextIO

from .command_output_observers import CommandOutputObserver


OUTPUT_READ_CHUNK_CHARS = 64 * 1024
PROCESS_WAIT_POLL_SECONDS = 0.05
MAX_COMPLETE_OUTPUT_BYTES = 64 * 1024**2


@dataclass
class BoundedTextCapture:
    max_chars: int
    preserve_complete: bool = False
    max_complete_bytes: int = MAX_COMPLETE_OUTPUT_BYTES
    total_chars: int = field(default=0, init=False)
    total_bytes: int = field(default=0, init=False)
    complete_overflow: bool = field(default=False, init=False)
    _prefix: str = field(default="", init=False, repr=False)
    _tail: str = field(default="", init=False, repr=False)
    _last_character: str = field(default="", init=False, repr=False)
    _complete: BinaryIO | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_chars < 1:
            raise ValueError("Command output character limit must be positive.")
        if self.max_complete_bytes < 1:
            raise ValueError("Complete command output byte limit must be positive.")
        if self.preserve_complete:
            self._complete = tempfile.TemporaryFile(mode="w+b")

    def append(self, chunk: str) -> None:
        if not chunk:
            return
        encoded = chunk.encode("utf-8")
        if self._complete is not None:
            if self.total_bytes + len(encoded) <= self.max_complete_bytes:
                self._complete.write(encoded)
            else:
                self.complete_overflow = True
                self._complete.close()
                self._complete = None
        self.total_chars += len(chunk)
        self.total_bytes += len(encoded)
        self._last_character = chunk[-1]

        prefix_remaining = self.max_chars - len(self._prefix)
        if prefix_remaining > 0:
            self._prefix += chunk[:prefix_remaining]

        tail_chars = _tail_character_count(self.max_chars)
        if tail_chars > 0:
            self._tail = (self._tail + chunk)[-tail_chars:]

    def render(self, *, prefix: str = "", suffix: str = "") -> tuple[str, bool]:
        total_chars = len(prefix) + self.total_chars + len(suffix)
        if total_chars <= self.max_chars:
            return f"{prefix}{self._prefix}{suffix}", False

        marker = truncation_marker(self.max_chars)
        if self.max_chars <= len(marker) + 2:
            return f"{prefix}{self._prefix}{suffix}"[: self.max_chars], True
        keep = self.max_chars - len(marker)
        head_chars = keep // 2
        tail_chars = keep - head_chars
        raw_tail = self._prefix if self.total_chars <= self.max_chars else self._tail
        head = f"{prefix}{self._prefix}{suffix}"[:head_chars]
        tail = f"{prefix}{raw_tail}{suffix}"[-tail_chars:]
        return f"{head}{marker}{tail}", True

    @property
    def ends_with_newline(self) -> bool:
        return self._last_character == "\n"

    @property
    def complete_stream(self) -> BinaryIO | None:
        if self._complete is not None:
            self._complete.flush()
            self._complete.seek(0)
        return self._complete

    def close(self) -> None:
        if self._complete is not None:
            self._complete.close()
            self._complete = None


@dataclass
class CommandOutputCapture:
    stdout: BoundedTextCapture
    stderr: BoundedTextCapture
    timed_out: bool

    def close(self) -> None:
        self.stdout.close()
        self.stderr.close()


def capture_command_output(
    process: subprocess.Popen[str],
    *,
    timeout_ms: int,
    max_output_chars: int,
    observer: CommandOutputObserver | None,
    preserve_complete: bool,
    terminate: Callable[[], None],
    max_complete_output_bytes: int = MAX_COMPLETE_OUTPUT_BYTES,
) -> CommandOutputCapture:
    stdout = BoundedTextCapture(
        max_output_chars,
        preserve_complete=preserve_complete,
        max_complete_bytes=max_complete_output_bytes,
    )
    try:
        stderr = BoundedTextCapture(
            max_output_chars,
            preserve_complete=preserve_complete,
            max_complete_bytes=max_complete_output_bytes,
        )
    except BaseException:
        stdout.close()
        raise

    failed = Event()
    errors: list[BaseException] = []
    error_lock = Lock()

    def read_stream(stream: TextIO | None, capture: BoundedTextCapture, *, is_stdout: bool) -> None:
        if stream is None:
            return
        try:
            while not failed.is_set():
                chunk = stream.readline(OUTPUT_READ_CHUNK_CHARS)
                if not chunk:
                    return
                capture.append(chunk)
                if observer is not None:
                    observer(chunk if is_stdout else "", "" if is_stdout else chunk)
        except BaseException as error:
            with error_lock:
                if not errors:
                    errors.append(error)
            failed.set()
        finally:
            stream.close()

    readers = (
        Thread(target=read_stream, args=(process.stdout, stdout), kwargs={"is_stdout": True}, daemon=True),
        Thread(target=read_stream, args=(process.stderr, stderr), kwargs={"is_stdout": False}, daemon=True),
    )
    for reader in readers:
        reader.start()

    timed_out = False
    deadline = time.monotonic() + timeout_ms / 1000
    try:
        while process.poll() is None or any(reader.is_alive() for reader in readers):
            if failed.is_set():
                terminate()
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                terminate()
                break
            failed.wait(min(PROCESS_WAIT_POLL_SECONDS, remaining))
        process.wait()
        for reader in readers:
            reader.join()
        if errors:
            raise errors[0]
        return CommandOutputCapture(stdout=stdout, stderr=stderr, timed_out=timed_out)
    except BaseException:
        terminate()
        try:
            process.wait()
        except BaseException:
            pass
        for reader in readers:
            reader.join(timeout=1)
        stdout.close()
        stderr.close()
        raise


def truncation_marker(max_chars: int) -> str:
    return f"\n[truncated to {max_chars} chars: showing head and tail]\n"


def truncate_command_output(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    marker = truncation_marker(max_chars)
    if max_chars <= len(marker) + 2:
        return value[:max_chars], True
    keep = max_chars - len(marker)
    head = keep // 2
    tail = keep - head
    return f"{value[:head]}{marker}{value[-tail:]}", True


def _tail_character_count(max_chars: int) -> int:
    marker = truncation_marker(max_chars)
    if max_chars <= len(marker) + 2:
        return 0
    keep = max_chars - len(marker)
    return keep - keep // 2


__all__ = [
    "BoundedTextCapture",
    "CommandOutputCapture",
    "MAX_COMPLETE_OUTPUT_BYTES",
    "OUTPUT_READ_CHUNK_CHARS",
    "capture_command_output",
    "truncate_command_output",
]
