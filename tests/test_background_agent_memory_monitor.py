from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent import background_agent_memory_monitor as monitor
from vibeagent.background_agent_store import ensure_private_directory, write_private_json
from vibeagent.process_registry import read_process_start_ticks
from vibeagent.tool_memory_limit import ToolMemoryLaunch
from vibeagent.tool_memory_systemd import ToolMemoryResult


AGENT_ID = "0123456789ab"
LIMIT_BYTES = 64 * 1024 * 1024
UNIT = f"vibeagent-tool-{'a' * 32}.service"


class BackgroundAgentMemoryMonitorTests(unittest.TestCase):
    def test_oom_result_survives_launcher_exit_and_cleans_private_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-memory-monitor-") as base:
            root = Path(base).resolve()
            payload_path, environment_path, stderr_path, exit_code_path = self._payload(root)
            with (
                patch.object(monitor, "tool_memory_unit_running", return_value=False),
                patch.object(
                    monitor,
                    "inspect_tool_memory_result",
                    return_value=ToolMemoryResult(
                        result="oom-kill",
                        memory_peak_bytes=LIMIT_BYTES,
                    ),
                ) as inspect,
            ):
                result = monitor.run_monitor(payload_path)

            self.assertEqual(result, 0)
            self.assertIn(
                "VIBEAGENT_BACKGROUND_AGENT_MEMORY_LIMIT=64 MiB",
                stderr_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(exit_code_path.read_text(encoding="utf-8"), "1\n")
            self.assertFalse(payload_path.exists())
            self.assertFalse(environment_path.exists())
            self.assertEqual(inspect.call_args.args[0].unit, UNIT)

    def test_existing_worker_exit_code_is_not_replaced_on_service_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-memory-monitor-") as base:
            root = Path(base).resolve()
            payload_path, environment_path, stderr_path, exit_code_path = self._payload(root)
            stderr_path.write_text("worker diagnostic\n", encoding="utf-8")
            exit_code_path.write_text("7\n", encoding="utf-8")
            with (
                patch.object(monitor, "tool_memory_unit_running", return_value=False),
                patch.object(
                    monitor,
                    "inspect_tool_memory_result",
                    return_value=ToolMemoryResult(result="exit-code"),
                ),
            ):
                result = monitor.run_monitor(payload_path)

            self.assertEqual(result, 0)
            self.assertEqual(stderr_path.read_text(encoding="utf-8"), "worker diagnostic\n")
            self.assertEqual(exit_code_path.read_text(encoding="utf-8"), "7\n")
            self.assertFalse(payload_path.exists())
            self.assertFalse(environment_path.exists())

    def test_service_failure_records_fallback_when_worker_wrote_no_exit_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-memory-monitor-") as base:
            root = Path(base).resolve()
            payload_path, environment_path, stderr_path, exit_code_path = self._payload(root)
            with (
                patch.object(monitor, "tool_memory_unit_running", return_value=False),
                patch.object(
                    monitor,
                    "inspect_tool_memory_result",
                    return_value=ToolMemoryResult(result="signal"),
                ),
            ):
                result = monitor.run_monitor(payload_path)

            self.assertEqual(result, 0)
            self.assertEqual(exit_code_path.read_text(encoding="utf-8"), "1\n")
            self.assertIn(
                "service failed before recording an exit code: signal",
                stderr_path.read_text(encoding="utf-8"),
            )
            self.assertFalse(payload_path.exists())
            self.assertFalse(environment_path.exists())

    def test_launcher_payload_and_monitor_environment_exclude_credentials(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-memory-monitor-") as base:
            root = Path(base).resolve()
            logs = ensure_private_directory(
                root / ".vibeagent" / "background-agents" / "logs"
            )
            environment_path = self._environment_file()
            launch = ToolMemoryLaunch(
                argv=("systemd-run", "worker"),
                unit=UNIT,
                limit_bytes=LIMIT_BYTES,
                environment_path=environment_path,
                systemctl="/usr/bin/systemctl",
            )
            worker = Mock(pid=os.getpid())
            spawned = Mock()
            with (
                patch.dict(
                    os.environ,
                    {
                        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
                        "MINIMAX_API_KEY": "secret-value",
                    },
                    clear=True,
                ),
                patch.object(monitor.subprocess, "Popen", return_value=spawned) as popen,
                patch.object(monitor.threading, "Thread") as thread,
            ):
                monitor.start_background_agent_memory_monitor(
                    root,
                    AGENT_ID,
                    launch,
                    worker,
                    stderr_path=logs / f"{AGENT_ID}.stderr.log",
                    exit_code_path=logs / f"{AGENT_ID}.exitcode",
                )

            payloads = tuple(
                (root / ".vibeagent" / "background-agents" / "launch").glob(
                    f"{AGENT_ID}-memory-*.json"
                )
            )
            self.assertEqual(len(payloads), 1)
            payload_text = payloads[0].read_text(encoding="utf-8")
            self.assertNotIn("secret-value", payload_text)
            self.assertEqual(stat.S_IMODE(payloads[0].stat().st_mode), 0o600)
            self.assertEqual(
                popen.call_args.kwargs["env"],
                {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
            )
            thread.return_value.start.assert_called_once_with()
            payloads[0].unlink()
            environment_path.unlink(missing_ok=True)

    @staticmethod
    def _environment_file() -> Path:
        descriptor, raw_path = tempfile.mkstemp(
            prefix="vibeagent-tool-env-",
            suffix=".json",
        )
        os.close(descriptor)
        path = Path(raw_path)
        path.chmod(0o600)
        path.write_text("{}\n", encoding="utf-8")
        return path

    @classmethod
    def _payload(cls, root: Path) -> tuple[Path, Path, Path, Path]:
        launch_root = ensure_private_directory(
            root / ".vibeagent" / "background-agents" / "launch"
        )
        logs = ensure_private_directory(
            root / ".vibeagent" / "background-agents" / "logs"
        )
        environment_path = cls._environment_file()
        stderr_path = logs / f"{AGENT_ID}.stderr.log"
        exit_code_path = logs / f"{AGENT_ID}.exitcode"
        stderr_path.write_text("", encoding="utf-8")
        payload_path = launch_root / f"{AGENT_ID}-memory-test.json"
        write_private_json(
            payload_path,
            {
                "schemaVersion": 1,
                "agentId": AGENT_ID,
                "projectRoot": root.as_posix(),
                "unit": UNIT,
                "limitBytes": LIMIT_BYTES,
                "environmentPath": environment_path.as_posix(),
                "systemctl": "/usr/bin/systemctl",
                "workerPid": os.getpid(),
                "workerStartTicks": read_process_start_ticks(os.getpid()),
                "stderrPath": stderr_path.relative_to(root).as_posix(),
                "exitCodePath": exit_code_path.relative_to(root).as_posix(),
            },
            exclusive=True,
        )
        return payload_path, environment_path, stderr_path, exit_code_path


if __name__ == "__main__":
    unittest.main()
