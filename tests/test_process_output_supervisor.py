from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.process_background_limits import (
    BACKGROUND_TASKS_DISABLED_ENV,
    background_output_exceeded_message,
    prepare_background_output_launch,
)
from vibeagent.process_lifecycle import close_background_handles
from vibeagent.process_io_runtime import wait_background_process
from vibeagent.process_output_supervisor import run_output_supervisor
from vibeagent.process_registry import read_persistent_process_exit_code, read_persistent_process_record
from vibeagent.process_runtime import BACKGROUND_PROCESSES, start_background_command
from vibeagent.process_stop_runtime import stop_background_process
from vibeagent.workspace import create_run_workspace


def _create_private_file(path: Path) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)


class ProcessOutputSupervisorTests(unittest.TestCase):
    def test_prepare_launch_keeps_paths_limit_and_exact_argv(self) -> None:
        launch = prepare_background_output_launch(
            ("python3", "app.py"),
            stdout_path=Path("stdout.log"),
            stderr_path=Path("stderr.log"),
            exit_code_path=Path("exit.txt"),
            max_output_bytes=1024,
        )

        self.assertEqual(
            launch[-7:],
            ("1024", "stdout.log", "stderr.log", "exit.txt", "--", "python3", "app.py"),
        )

    def test_supervisor_preserves_streams_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-limit-") as base:
            root = Path(base)
            stdout_path = root / "stdout.log"
            stderr_path = root / "stderr.log"
            exit_code_path = root / "exit.txt"
            _create_private_file(stdout_path)
            _create_private_file(stderr_path)
            code = "import sys; print('alpha'); print('beta', file=sys.stderr); raise SystemExit(7)"

            exit_code = run_output_supervisor(
                4096,
                stdout_path,
                stderr_path,
                exit_code_path,
                (sys.executable, "-c", code),
            )

            self.assertEqual(exit_code, 7)
            self.assertEqual(stdout_path.read_text(encoding="utf-8"), "alpha\n")
            self.assertEqual(stderr_path.read_text(encoding="utf-8"), "beta\n")
            self.assertEqual(exit_code_path.read_text(encoding="utf-8"), "7\n")

    def test_supervisor_caps_combined_output_and_terminates_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-limit-") as base:
            root = Path(base)
            stdout_path = root / "stdout.log"
            stderr_path = root / "stderr.log"
            exit_code_path = root / "exit.txt"
            _create_private_file(stdout_path)
            _create_private_file(stderr_path)
            code = (
                "import os, time; "
                "os.write(1, b'a' * 800); os.write(2, b'b' * 800); time.sleep(10)"
            )

            exit_code = run_output_supervisor(
                1024,
                stdout_path,
                stderr_path,
                exit_code_path,
                (sys.executable, "-c", code),
            )

            stdout = stdout_path.read_bytes()
            stderr = stderr_path.read_bytes()
            marker = f"\n{background_output_exceeded_message(1024)}\n".encode()
            self.assertEqual(exit_code, 1)
            self.assertTrue(stderr.endswith(marker))
            self.assertEqual(len(stdout) + len(stderr) - len(marker), 1024)
            self.assertEqual(exit_code_path.read_text(encoding="utf-8"), "1\n")

    def test_supervisor_tracks_output_from_descendants_after_parent_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-limit-") as base:
            root = Path(base)
            stdout_path = root / "stdout.log"
            stderr_path = root / "stderr.log"
            exit_code_path = root / "exit.txt"
            _create_private_file(stdout_path)
            _create_private_file(stderr_path)
            grandchild = "import os\nwhile True: os.write(1, b'x' * 256)"
            code = (
                "import subprocess, sys; "
                f"subprocess.Popen([sys.executable, '-c', {grandchild!r}])"
            )

            exit_code = run_output_supervisor(
                1024,
                stdout_path,
                stderr_path,
                exit_code_path,
                (sys.executable, "-c", code),
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(len(stdout_path.read_bytes()), 1024)
            self.assertIn("combined background output exceeded", stderr_path.read_text())

    def test_background_start_rejects_disabled_and_invalid_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-limit-") as base:
            workspace = create_run_workspace(base, "disabled")
            with patch.dict(os.environ, {BACKGROUND_TASKS_DISABLED_ENV: "1"}):
                disabled = start_background_command(workspace, "printf nope")
            invalid = start_background_command(
                workspace,
                "printf nope",
                output_limit_bytes=0,
            )

        self.assertFalse(disabled.ok)
        self.assertIn(BACKGROUND_TASKS_DISABLED_ENV, disabled.message)
        self.assertFalse(invalid.ok)
        self.assertIn("must be positive", invalid.message)

    def test_real_background_command_uses_combined_output_limit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-limit-") as base:
            workspace = create_run_workspace(base, "output-limit")
            command = (
                "python3 -c \"import os, time; "
                "os.write(1, b'a' * 800); os.write(2, b'b' * 800); time.sleep(10)\""
            )
            started = start_background_command(
                workspace,
                command,
                output_limit_bytes=1024,
            )
            self.assertTrue(started.ok, started.message)
            try:
                result = wait_background_process(
                    workspace.root,
                    started.process_id,
                    timeout_ms=5000,
                    max_output_chars=4000,
                )
                record = read_persistent_process_record(workspace.root, started.process_id)
                persisted_exit_code = (
                    read_persistent_process_exit_code(record) if record is not None else None
                )
            finally:
                stop_background_process(workspace.root, started.process_id)

        self.assertTrue(result.ok, result.message)
        self.assertFalse(result.running)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(persisted_exit_code, 1)
        self.assertIn("combined background output exceeded 1 KiB", result.stderr)

    @unittest.skipUnless(os.name == "posix", "PTY-backed jobs require POSIX")
    def test_pty_background_limit_cleans_persistent_stdin_fifo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-output-limit-") as base:
            workspace = create_run_workspace(base, "pty-output-limit")
            command = (
                "python3 -c \"import os, time; "
                "os.write(1, b'x' * 2048); time.sleep(10)\""
            )
            started = start_background_command(
                workspace,
                command,
                pty_backed=True,
                output_limit_bytes=1024,
            )
            self.assertTrue(started.ok, started.message)
            record = read_persistent_process_record(workspace.root, started.process_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertIsNotNone(record.stdin_path)
            assert record.stdin_path is not None
            stdin_path = record.stdin_path
            background = BACKGROUND_PROCESSES.pop(started.process_id)
            try:
                background.process.wait(timeout=5)
                result = wait_background_process(
                    workspace.root,
                    started.process_id,
                    timeout_ms=5000,
                    max_output_chars=4000,
                )
            finally:
                stop_background_process(workspace.root, started.process_id)
                close_background_handles(background)

        self.assertFalse(result.running)
        self.assertEqual(result.exit_code, 1)
        self.assertFalse(stdin_path.exists())


if __name__ == "__main__":
    unittest.main()
