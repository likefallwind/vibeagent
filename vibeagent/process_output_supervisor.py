from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
from threading import Event, Lock, Thread
import time
from typing import BinaryIO

from .process_background_limits import background_output_exceeded_message


OUTPUT_CHUNK_BYTES = 64 * 1024


@dataclass
class OutputBudget:
    max_bytes: int
    used_bytes: int = 0
    exceeded: Event = field(default_factory=Event)
    failed: Event = field(default_factory=Event)
    failure_message: str | None = None
    lock: Lock = field(default_factory=Lock)

    def reserve(self, requested: int) -> int:
        with self.lock:
            remaining = max(0, self.max_bytes - self.used_bytes)
            allowed = min(requested, remaining)
            self.used_bytes += allowed
            if requested > allowed:
                self.exceeded.set()
            return allowed

    def fail(self, error: BaseException) -> None:
        with self.lock:
            if self.failure_message is None:
                self.failure_message = str(error)
            self.failed.set()


def run_output_supervisor(
    max_output_bytes: int,
    stdout_path: Path,
    stderr_path: Path,
    exit_code_path: Path,
    argv: tuple[str, ...],
) -> int:
    if max_output_bytes < 1 or not argv:
        raise ValueError("Invalid background output supervisor invocation.")
    stdout_log = _open_private_log_append(stdout_path)
    try:
        stderr_log = _open_private_log_append(stderr_path)
    except BaseException:
        stdout_log.close()
        raise

    child: subprocess.Popen[bytes] | None = None
    previous_signal_handlers: dict[int, object] = {}
    readers: tuple[Thread, ...] = ()
    try:
        child = subprocess.Popen(
            argv,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            start_new_session=os.name != "nt",
        )
        assert child.stdout is not None
        assert child.stderr is not None
        budget = OutputBudget(max_output_bytes)
        readers = (
            _start_reader(child.stdout, stdout_log, budget, "stdout"),
            _start_reader(child.stderr, stderr_log, budget, "stderr"),
        )
        received_signal, previous_signal_handlers = _install_signal_forwarders(child)

        while child.poll() is None or any(reader.is_alive() for reader in readers):
            if budget.exceeded.is_set() or budget.failed.is_set():
                break
            time.sleep(0.02)
        if budget.exceeded.is_set() or budget.failed.is_set():
            _terminate_child_tree(child)
        returncode = child.wait()
        for reader in readers:
            reader.join()

        if budget.exceeded.is_set():
            message = background_output_exceeded_message(max_output_bytes)
            stderr_log.write(f"\n{message}\n".encode("utf-8"))
            stderr_log.flush()
            _write_exit_code_if_missing(exit_code_path, 1)
            return 1
        if budget.failed.is_set():
            _write_exit_code_if_missing(exit_code_path, 125)
            return 125
        _terminate_child_tree(child)
        if received_signal[0] is not None:
            normalized = 128 + received_signal[0]
        else:
            normalized = returncode if returncode >= 0 else 128 - returncode
        _write_exit_code_if_missing(exit_code_path, normalized)
        return normalized
    finally:
        if child is not None and (
            child.poll() is None or any(reader.is_alive() for reader in readers)
        ):
            _terminate_child_tree(child)
        for reader in readers:
            reader.join(timeout=0.5)
        if child is not None:
            for stream in (child.stdout, child.stderr):
                if stream is not None:
                    stream.close()
        for signum, handler in previous_signal_handlers.items():
            signal.signal(signum, handler)
        stdout_log.close()
        stderr_log.close()


def _start_reader(
    source: BinaryIO,
    destination: BinaryIO,
    budget: OutputBudget,
    stream_name: str,
) -> Thread:
    def copy_output() -> None:
        try:
            while not budget.exceeded.is_set() and not budget.failed.is_set():
                chunk = source.read(OUTPUT_CHUNK_BYTES)
                if not chunk:
                    return
                allowed = budget.reserve(len(chunk))
                if allowed:
                    destination.write(chunk[:allowed])
                    destination.flush()
                if allowed < len(chunk):
                    return
        except (OSError, ValueError) as error:
            budget.fail(error)

    thread = Thread(
        target=copy_output,
        name=f"background-output-{stream_name}",
        daemon=True,
    )
    thread.start()
    return thread


def _install_signal_forwarders(
    child: subprocess.Popen[bytes],
) -> tuple[list[int | None], dict[int, object]]:
    received: list[int | None] = [None]
    previous: dict[int, object] = {}

    def forward(signum: int, _frame: object) -> None:
        received[0] = signum
        _terminate_child_tree(child)

    for signum in (signal.SIGTERM, signal.SIGINT):
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, forward)
    return received, previous


def _terminate_child_tree(child: subprocess.Popen[bytes]) -> None:
    if os.name == "nt" and child.poll() is not None:
        return
    try:
        if os.name == "nt":
            child.terminate()
        else:
            os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 0.4
    while child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    try:
        if os.name == "nt":
            child.kill()
        else:
            os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _open_private_log_append(path: Path) -> BinaryIO:
    flags = os.O_WRONLY | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        owner_ok = not hasattr(os, "getuid") or info.st_uid == os.getuid()
        if (
            not stat.S_ISREG(info.st_mode)
            or not owner_ok
            or stat.S_IMODE(info.st_mode) & 0o077 != 0
        ):
            raise OSError("unsafe background process log")
    except BaseException:
        os.close(descriptor)
        raise
    return os.fdopen(descriptor, "ab", buffering=0)


def _write_exit_code_if_missing(path: Path, exit_code: int) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:
        return
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"{exit_code}\n")


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) < 6 or values[4] != "--" or not values[0].isdecimal():
        print("Invalid background output supervisor invocation.", file=sys.stderr)
        return 125
    stderr_path = Path(values[2])
    exit_code_path = Path(values[3])
    try:
        return run_output_supervisor(
            int(values[0]),
            Path(values[1]),
            stderr_path,
            exit_code_path,
            tuple(values[5:]),
        )
    except (OSError, ValueError) as error:
        message = f"Background output supervisor error: {error}"
        print(message, file=sys.stderr)
        try:
            with _open_private_log_append(stderr_path) as handle:
                handle.write(f"{message}\n".encode("utf-8"))
        except OSError:
            pass
        _write_exit_code_if_missing(exit_code_path, 125)
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
