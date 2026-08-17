from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from vibeagent import background_agent_process as process_runtime
from vibeagent import background_agent_runtime as runtime
from vibeagent import background_agent_store as store
from vibeagent.background_agent_config import read_background_agent_config
from vibeagent.background_agent_memory import (
    BACKGROUND_AGENT_MEMORY_LIMIT_ENV,
    resolve_background_agent_memory_limit,
    validate_background_agent_memory_limit_bytes,
)
from vibeagent.background_agent_types import BackgroundAgentRecord, BackgroundAgentView
from vibeagent.cli_args import parse_args
from vibeagent.cli_background_agent_launch import launch_background_agent_from_cli
from vibeagent.cli_validation import validate_cli_args
from vibeagent.tool_memory_limit import ToolMemoryLaunch, ToolMemoryLimitError


LIMIT_BYTES = 256 * 1024 * 1024


def _systemd_user_memory_available() -> bool:
    systemd_run = shutil.which("systemd-run")
    if not sys.platform.startswith("linux") or systemd_run is None:
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


class BackgroundAgentMemoryTests(unittest.TestCase):
    def test_resolves_cli_environment_and_explicit_disable(self) -> None:
        environment = {BACKGROUND_AGENT_MEMORY_LIMIT_ENV: "128MiB"}

        self.assertEqual(
            resolve_background_agent_memory_limit(None, environment),
            128 * 1024 * 1024,
        )
        self.assertEqual(
            resolve_background_agent_memory_limit("256M", environment),
            LIMIT_BYTES,
        )
        self.assertIsNone(resolve_background_agent_memory_limit("off", environment))
        self.assertIsNone(resolve_background_agent_memory_limit(None, {}))
        with self.assertRaisesRegex(
            ToolMemoryLimitError,
            BACKGROUND_AGENT_MEMORY_LIMIT_ENV,
        ):
            resolve_background_agent_memory_limit("invalid", {})

    def test_validation_rejects_non_positive_or_excessive_values(self) -> None:
        self.assertEqual(
            validate_background_agent_memory_limit_bytes(LIMIT_BYTES),
            LIMIT_BYTES,
        )
        self.assertIsNone(validate_background_agent_memory_limit_bytes(None))
        for value in (0, -1, True, 1.5, "256M", 1024**5 + 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_background_agent_memory_limit_bytes(value)

    def test_cli_option_requires_background_agent_or_dashboard(self) -> None:
        standalone = parse_args(["--background-memory-limit", "256M", "inspect"])
        background = parse_args(
            ["--background", "--background-memory-limit", "256M", "inspect"]
        )
        dashboard = parse_args(["agents", "--background-memory-limit", "256M"])
        interactive = parse_args(["--background-memory-limit", "256M"])

        self.assertIn("requires", validate_cli_args(standalone) or "")
        self.assertIsNone(validate_cli_args(background))
        self.assertIsNone(validate_cli_args(dashboard))
        self.assertIsNone(validate_cli_args(interactive))

    def test_cli_launch_resolves_and_reports_memory_limit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-memory-cli-") as base:
            root = Path(base).resolve()
            argv = [
                "--background",
                "--background-memory-limit",
                "256MiB",
                "--cwd",
                root.as_posix(),
                "inspect",
            ]
            args = parse_args(argv)
            view = self._view(root, memory_limit_bytes=LIMIT_BYTES)
            output = io.StringIO()
            with (
                patch(
                    "vibeagent.cli_background_agent_launch.launch_background_agent",
                    return_value=view,
                ) as launch,
                redirect_stdout(output),
            ):
                exit_code = launch_background_agent_from_cli(argv, args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(launch.call_args.kwargs["memory_limit_bytes"], LIMIT_BYTES)
        self.assertIn("memory: 256 MiB", output.getvalue())

    def test_launch_and_respawn_persist_limit_and_replace_memory_unit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-memory-") as base:
            root = Path(base).resolve()
            first_process = Mock(pid=12_345)
            second_process = Mock(pid=23_456)
            first_launch = self._memory_launch(root, "1" * 32)
            second_launch = self._memory_launch(root, "2" * 32)
            with (
                patch.object(
                    process_runtime,
                    "prepare_memory_launch",
                    side_effect=(first_launch, second_launch),
                ) as prepare,
                patch.object(
                    process_runtime.subprocess,
                    "Popen",
                    side_effect=(first_process, second_process),
                ) as popen,
                patch.object(process_runtime, "wait_for_tool_memory_service", return_value=None),
                patch.object(
                    process_runtime,
                    "start_background_agent_memory_monitor",
                ) as monitor,
                patch.object(runtime, "read_process_start_ticks", side_effect=(77, 88)),
                patch.object(store, "persistent_process_running", return_value=True),
            ):
                launched = runtime.launch_background_agent(
                    root,
                    root,
                    [
                        "--background",
                        "--background-memory-limit",
                        "256M",
                        "inspect",
                    ],
                    task_summary="inspect",
                    session_name=None,
                    memory_limit_bytes=LIMIT_BYTES,
                )
                launched.record.exit_code_path.write_text("0\n", encoding="utf-8")
                respawned, disposition = runtime.send_background_agent_message(
                    root,
                    launched.record.id,
                    "continue",
                )
                persisted = runtime.get_background_agent(root, launched.record.id)

            assert respawned is not None
            config = read_background_agent_config(root, launched.record.id)

        self.assertEqual(disposition, "respawned")
        self.assertEqual(launched.record.memory_unit, first_launch.unit)
        self.assertEqual(respawned.record.memory_unit, second_launch.unit)
        self.assertEqual(respawned.record.memory_limit_bytes, LIMIT_BYTES)
        self.assertEqual(persisted, respawned)
        self.assertNotIn("--background-memory-limit", config.base_argv)
        self.assertEqual(prepare.call_count, 2)
        self.assertTrue(
            all(call.kwargs["limit_bytes"] == LIMIT_BYTES for call in prepare.call_args_list)
        )
        self.assertEqual(popen.call_args_list[0].args[0], first_launch.argv)
        self.assertEqual(popen.call_args_list[1].args[0], second_launch.argv)
        self.assertEqual(monitor.call_count, 2)
        self.assertEqual(monitor.call_args_list[0].args[2], first_launch)
        self.assertEqual(monitor.call_args_list[1].args[2], second_launch)

    @unittest.skipUnless(
        _systemd_user_memory_available(),
        "requires a running user systemd manager",
    )
    def test_real_limited_worker_records_failure_and_cgroup_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-memory-real-") as base:
            root = Path(base).resolve()
            with patch.dict(
                os.environ,
                {"MINIMAX_API_KEY": "", "MINIMAX_API": "", "minimax_api": ""},
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "--provider", "minimax", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                    memory_limit_bytes=128 * 1024 * 1024,
                )
                deadline = time.monotonic() + 5
                while (
                    store.read_background_agent_exit_code(view.record.exit_code_path)
                    is None
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.02)
                current, stdout, stderr = runtime.read_background_agent_logs(
                    root,
                    view.record.id,
                )
                if current is not None and current.status in {"running", "needs-input"}:
                    runtime.stop_background_agent(root, view.record.id)
                unit = view.record.memory_unit
                assert unit is not None
                monitor_deadline = time.monotonic() + 5
                launch_root = store.background_agent_runtime_root(root) / "launch"
                while time.monotonic() < monitor_deadline:
                    pending = tuple(launch_root.glob(f"{view.record.id}-memory-*.json"))
                    failed = subprocess.run(
                        ("systemctl", "--user", "is-failed", "--quiet", unit),
                        text=True,
                        capture_output=True,
                        timeout=2,
                        check=False,
                    ).returncode == 0
                    if not pending and not failed:
                        break
                    time.sleep(0.02)

        assert current is not None
        self.assertEqual(current.status, "failed")
        self.assertEqual(current.record.memory_limit_bytes, 128 * 1024 * 1024)
        self.assertIsNotNone(current.record.memory_unit)
        self.assertIn("Missing MiniMax API key", stdout)
        self.assertEqual(stderr, "")
        self.assertFalse(pending)
        self.assertFalse(failed)

    @staticmethod
    def _memory_launch(root: Path, digest: str) -> ToolMemoryLaunch:
        return ToolMemoryLaunch(
            argv=("systemd-run", f"--unit=vibeagent-tool-{digest}.service", "worker"),
            unit=f"vibeagent-tool-{digest}.service",
            limit_bytes=LIMIT_BYTES,
            environment_path=root / f"environment-{digest}.json",
            systemctl="systemctl",
        )

    @staticmethod
    def _view(root: Path, *, memory_limit_bytes: int) -> BackgroundAgentView:
        logs = root / ".vibeagent" / "background-agents" / "logs"
        return BackgroundAgentView(
            record=BackgroundAgentRecord(
                id="0123456789ab",
                project_root=root,
                invocation_root=root,
                pid=1234,
                start_ticks=77,
                started_at="2026-08-17T00:00:00+00:00",
                task_summary="inspect",
                session_name="background-0123456789ab",
                stdout_path=logs / "0123456789ab.stdout.log",
                stderr_path=logs / "0123456789ab.stderr.log",
                exit_code_path=logs / "0123456789ab.exitcode",
                stopped_path=logs / "0123456789ab.stopped",
                memory_unit=f"vibeagent-tool-{'a' * 32}.service",
                memory_limit_bytes=memory_limit_bytes,
            ),
            status="running",
            exit_code=None,
        )


if __name__ == "__main__":
    unittest.main()
