from __future__ import annotations

import errno
import os
from pathlib import Path
import selectors
import stat
import struct
import subprocess
import sys

from .process_pty import MAX_PROCESS_STDIN_BYTES


def run_pty_relay(stdin_path: Path, argv: tuple[str, ...]) -> int:
    import fcntl
    import pty
    import termios

    fifo_reader = _open_fifo(stdin_path, os.O_RDONLY | os.O_NONBLOCK)
    fifo_keeper = _open_fifo(stdin_path, os.O_WRONLY | os.O_NONBLOCK)
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    os.set_blocking(master, False)
    try:
        child = subprocess.Popen(
            argv,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True,
        )
    except BaseException:
        os.close(slave)
        os.close(master)
        os.close(fifo_keeper)
        os.close(fifo_reader)
        _remove_stdin_path(stdin_path)
        raise
    os.close(slave)

    selector = selectors.DefaultSelector()
    selector.register(fifo_reader, selectors.EVENT_READ, "stdin")
    selector.register(master, selectors.EVENT_READ, "pty")
    pending = bytearray()
    master_open = True
    fifo_registered = True
    try:
        while master_open:
            events = selector.select(timeout=0.05)
            for key, mask in events:
                if key.data == "stdin" and mask & selectors.EVENT_READ:
                    try:
                        chunk = os.read(
                            fifo_reader,
                            MAX_PROCESS_STDIN_BYTES - len(pending),
                        )
                    except BlockingIOError:
                        chunk = b""
                    if chunk:
                        pending.extend(chunk)
                        selector.modify(
                            master,
                            selectors.EVENT_READ | selectors.EVENT_WRITE,
                            "pty",
                        )
                        if len(pending) >= MAX_PROCESS_STDIN_BYTES:
                            selector.unregister(fifo_reader)
                            fifo_registered = False
                elif key.data == "pty":
                    if mask & selectors.EVENT_READ:
                        try:
                            chunk = os.read(master, 65_536)
                        except OSError as error:
                            if error.errno != errno.EIO:
                                raise
                            chunk = b""
                        if chunk:
                            sys.stdout.buffer.write(chunk)
                            sys.stdout.buffer.flush()
                        else:
                            master_open = False
                            break
                    if pending and mask & selectors.EVENT_WRITE:
                        try:
                            written = os.write(master, pending)
                        except BlockingIOError:
                            written = 0
                        if written:
                            del pending[:written]
                            if not fifo_registered:
                                selector.register(fifo_reader, selectors.EVENT_READ, "stdin")
                                fifo_registered = True
                        if not pending:
                            selector.modify(master, selectors.EVENT_READ, "pty")
            if child.poll() is not None and not events:
                try:
                    chunk = os.read(master, 65_536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    chunk = b""
                if chunk:
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
                else:
                    master_open = False
        returncode = child.wait()
        return returncode if returncode >= 0 else 128 - returncode
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        selector.close()
        os.close(master)
        os.close(fifo_keeper)
        os.close(fifo_reader)
        _remove_stdin_path(stdin_path)


def _open_fifo(path: Path, access_flags: int) -> int:
    flags = access_flags
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISFIFO(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077 != 0
        ):
            raise OSError("unsafe persistent stdin transport")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _remove_stdin_path(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) < 3 or values[1] != "--":
        print("Invalid PTY relay invocation.", file=sys.stderr)
        return 2
    return run_pty_relay(Path(values[0]), tuple(values[2:]))


if __name__ == "__main__":
    raise SystemExit(main())
