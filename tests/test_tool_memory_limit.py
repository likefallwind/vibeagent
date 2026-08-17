from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.command_output_observers import observe_command_output
from vibeagent.process_lifecycle import close_background_handles
from vibeagent.process_command_runtime import run_command
from vibeagent.process_io_runtime import wait_background_process
from vibeagent.process_runtime import BACKGROUND_PROCESSES, start_background_command
from vibeagent.process_registry import (
    read_persistent_process_exit_code,
    read_persistent_process_record,
)
from vibeagent.process_stop_runtime import stop_background_process
from vibeagent.tool_memory_exec import main as memory_exec_main
from vibeagent.tool_memory_limit import (
    MAX_TOOL_MEMORY_LIMIT_BYTES,
    TOOL_MEMORY_LIMIT_ENV,
    ToolMemoryLimitError,
    cleanup_tool_memory_launch,
    parse_tool_memory_limit,
    prepare_tool_memory_launch,
    valid_tool_memory_unit,
)
from vibeagent.workspace import create_run_workspace


def _systemd_user_memory_available() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    systemd_run = shutil.which("systemd-run")
    systemctl = shutil.which("systemctl")
    if systemd_run is None or systemctl is None:
        return False
    try:
        result = subprocess.run(
            (
                systemd_run,
                "--user",
                "--wait",
                "--pipe",
                "--quiet",
                "--property=MemoryMax=128M",
                "--property=MemorySwapMax=0",
                "true",
            ),
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


class ToolMemoryLimitTests(unittest.TestCase):
    def test_parses_byte_counts_and_binary_suffixes(self) -> None:
        self.assertIsNone(parse_tool_memory_limit({}))
        self.assertEqual(parse_tool_memory_limit({TOOL_MEMORY_LIMIT_ENV: "4096"}), 4096)
        self.assertEqual(parse_tool_memory_limit({TOOL_MEMORY_LIMIT_ENV: "64M"}), 64 * 1024**2)
        self.assertEqual(parse_tool_memory_limit({TOOL_MEMORY_LIMIT_ENV: "2GiB"}), 2 * 1024**3)

    def test_rejects_invalid_or_excessive_limits(self) -> None:
        for value in ("", "0", "-1", "1.5G", "unlimited"):
            with self.subTest(value=value), self.assertRaises(ToolMemoryLimitError):
                parse_tool_memory_limit({TOOL_MEMORY_LIMIT_ENV: value})
        with self.assertRaises(ToolMemoryLimitError):
            parse_tool_memory_limit(
                {TOOL_MEMORY_LIMIT_ENV: str(MAX_TOOL_MEMORY_LIMIT_BYTES + 1)}
            )

    def test_launch_uses_private_environment_file_without_secret_arguments(self) -> None:
        environment = dict(os.environ)
        environment.update(
            {
                TOOL_MEMORY_LIMIT_ENV: "128M",
                "VIBEAGENT_MEMORY_TEST_SECRET": "private-value",
            }
        )
        launch = prepare_tool_memory_launch(("sh", "-c", "true"), Path.cwd(), environment)
        self.assertIsNotNone(launch)
        assert launch is not None
        try:
            self.assertTrue(valid_tool_memory_unit(launch.unit))
            self.assertEqual(launch.environment_path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("private-value", " ".join(launch.argv))
            self.assertIn("--property=MemoryMax=134217728", launch.argv)
            self.assertIn("--property=MemorySwapMax=0", launch.argv)
            with patch("os.execvpe") as execvpe:
                self.assertEqual(
                    memory_exec_main(
                        [launch.environment_path.as_posix(), "--", "sh", "-c", "true"]
                    ),
                    125,
                )
            execvpe.assert_called_once()
            self.assertEqual(
                execvpe.call_args.args[2]["VIBEAGENT_MEMORY_TEST_SECRET"],
                "private-value",
            )
            self.assertFalse(launch.environment_path.exists())
        finally:
            cleanup_tool_memory_launch(launch)

    def test_invalid_limit_returns_command_setup_error_without_execution(self) -> None:
        environment = dict(os.environ)
        environment[TOOL_MEMORY_LIMIT_ENV] = "bad"

        result = run_command(Path.cwd(), "printf should-not-run", environment=environment)

        self.assertIsNone(result.exit_code)
        self.assertEqual(result.stdout, "")
        self.assertIn(TOOL_MEMORY_LIMIT_ENV, result.stderr)

    @unittest.skipUnless(
        _systemd_user_memory_available(),
        "requires a running user systemd manager",
    )
    def test_real_cgroup_preserves_environment_and_reports_oom(self) -> None:
        environment = dict(os.environ)
        environment.update(
            {
                TOOL_MEMORY_LIMIT_ENV: "128M",
                "VIBEAGENT_MEMORY_PROBE": "kept",
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-memory-limit-") as base:
            normal = run_command(
                base,
                "printf '%s:%s' \"$VIBEAGENT_MEMORY_PROBE\" \"$PWD\"",
                environment=environment,
            )
            environment[TOOL_MEMORY_LIMIT_ENV] = "48M"
            exceeded = run_command(
                base,
                (
                    "python3 -c 'x=bytearray(128*1024*1024); "
                    "x[::4096]=bytes([120])*(len(x)//4096)'"
                ),
                timeout_ms=10_000,
                environment=environment,
            )
            with observe_command_output(lambda _stdout, _stderr: None):
                timed_out = run_command(
                    base,
                    "python3 -c 'import time; time.sleep(10)'",
                    timeout_ms=50,
                    environment=environment,
                )

        self.assertEqual(normal.exit_code, 0, normal.stderr)
        self.assertEqual(normal.stdout, f"kept:{Path(base)}")
        self.assertNotEqual(exceeded.exit_code, 0)
        self.assertEqual(exceeded.signal, "SIGKILL")
        self.assertIn("exceeding CLAUDE_CODE_TOOL_MEMORY_LIMIT=48 MiB", exceeded.stderr)
        self.assertTrue(timed_out.timed_out)

    @unittest.skipUnless(
        _systemd_user_memory_available(),
        "requires a running user systemd manager",
    )
    def test_real_background_command_reports_oom_and_remains_stoppable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-memory-background-") as base:
            workspace = create_run_workspace(Path(base), "memory-background")
            with patch.dict(os.environ, {TOOL_MEMORY_LIMIT_ENV: "48M"}):
                started = start_background_command(
                    workspace,
                    (
                        "python3 -c 'x=bytearray(128*1024*1024); "
                        "x[::4096]=bytes([120])*(len(x)//4096)'"
                    ),
                )
                self.assertTrue(started.ok, started.message)
                try:
                    result = wait_background_process(
                        workspace.root,
                        started.process_id,
                        timeout_ms=10_000,
                    )
                    record = read_persistent_process_record(
                        workspace.root,
                        started.process_id,
                    )
                    persisted_exit_code = (
                        read_persistent_process_exit_code(record)
                        if record is not None
                        else None
                    )
                finally:
                    stop_background_process(workspace.root, started.process_id)

        self.assertTrue(result.ok, result.message)
        self.assertFalse(result.running)
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(persisted_exit_code, 1)
        self.assertIn("exceeding CLAUDE_CODE_TOOL_MEMORY_LIMIT=48 MiB", result.stderr)

    @unittest.skipUnless(
        _systemd_user_memory_available(),
        "requires a running user systemd manager",
    )
    def test_persistent_record_stops_memory_limited_service_after_runtime_detach(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-memory-persistent-") as base:
            workspace = create_run_workspace(Path(base), "memory-persistent")
            with patch.dict(os.environ, {TOOL_MEMORY_LIMIT_ENV: "128M"}):
                started = start_background_command(
                    workspace,
                    "python3 -c 'import time; time.sleep(30)'",
                )
                self.assertTrue(started.ok, started.message)
                background = BACKGROUND_PROCESSES.pop(started.process_id)
                close_background_handles(background)
                try:
                    stopped = stop_background_process(workspace.root, started.process_id)
                    background.process.wait(timeout=5)
                finally:
                    if background.process.poll() is None:
                        background.process.kill()

        self.assertTrue(stopped.ok, stopped.message)
        self.assertIn("Stopped process", stopped.message)


if __name__ == "__main__":
    unittest.main()
