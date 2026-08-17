from __future__ import annotations

from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest

from vibeagent.process_pty import (
    MAX_PROCESS_STDIN_BYTES,
    prepare_process_pty_launch,
    process_stdin_available,
    write_process_stdin,
)
from vibeagent.process_pty_relay import main as relay_main


@unittest.skipUnless(os.name == "posix", "PTY transport requires POSIX")
class ProcessPtyTests(unittest.TestCase):
    def test_prepare_launch_creates_private_fifo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-pty-") as base:
            stdin_path = Path(base) / "process.stdin.fifo"

            argv = prepare_process_pty_launch(("python3", "app.py"), stdin_path)

            info = stdin_path.lstat()
            self.assertTrue(stat.S_ISFIFO(info.st_mode))
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
            self.assertTrue(process_stdin_available(stdin_path))
            self.assertEqual(argv[-4:], (stdin_path.as_posix(), "--", "python3", "app.py"))

    def test_write_rejects_non_fifo_and_oversized_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-pty-") as base:
            stdin_path = Path(base) / "process.stdin.fifo"
            stdin_path.write_text("not a fifo", encoding="utf-8")

            self.assertEqual(
                write_process_stdin(stdin_path, "hello\n"),
                "persistent stdin transport is unavailable",
            )
            self.assertIn(
                "exceeds",
                write_process_stdin(stdin_path, "x" * (MAX_PROCESS_STDIN_BYTES + 1)) or "",
            )

    def test_relay_main_requires_explicit_separator_and_command(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = relay_main(["stdin.fifo", "python3"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid PTY relay invocation", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
