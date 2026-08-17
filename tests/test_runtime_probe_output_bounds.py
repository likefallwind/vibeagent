from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.dynamic_workflow_node import ensure_node_workflow_runtime
from vibeagent.tool_memory_limit import ToolMemoryLaunch
from vibeagent.tool_memory_systemd import (
    inspect_tool_memory_result,
    stop_tool_memory_unit,
    tool_memory_unit_running,
)
from vibeagent.workspace_environment_info import read_runtime_tool_info


UNIT = "vibeagent-tool-0123456789abcdef0123456789abcdef.service"


class RuntimeProbeOutputBoundsTests(unittest.TestCase):
    def test_node_version_probe_accepts_supported_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-node-probe-") as base:
            executable = Path(base) / "node"
            self._write_executable(executable, "print('v22.1.0')\n")
            with patch("vibeagent.dynamic_workflow_node.shutil.which", return_value=str(executable)):
                ensure_node_workflow_runtime()

    def test_node_version_probe_bounds_oversized_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-node-probe-") as base:
            executable = Path(base) / "node"
            self._write_executable(
                executable,
                "import os\n"
                "chunk = bytes([120]) * 65536\n"
                "for _ in range(32):\n"
                "    os.write(1, chunk)\n"
                "os.write(1, b'\\nv22.1.0\\n')\n",
            )
            with patch("vibeagent.dynamic_workflow_node.shutil.which", return_value=str(executable)):
                with self.assertRaisesRegex(ValueError, "Node.js 22 or newer") as raised:
                    ensure_node_workflow_runtime()

        self.assertLess(len(str(raised.exception)), 4_200)

    def test_environment_tool_probe_uses_resolved_path_and_bounds_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-tool-probe-") as base:
            executable = Path(base) / "probe"
            self._write_executable(
                executable,
                "import os\n"
                "chunk = bytes([121]) * 65536\n"
                "for _ in range(32):\n"
                "    os.write(1, chunk)\n"
                "os.write(1, b'\\nprobe 1.0\\n')\n",
            )
            with patch("vibeagent.workspace_environment_info.shutil.which", return_value=str(executable)):
                result = read_runtime_tool_info("probe", ["probe", "--version"])

        self.assertTrue(result["available"])
        self.assertEqual(result["path"], str(executable))
        self.assertIsInstance(result["version"], str)
        self.assertLessEqual(len(str(result["message"])), 4_000)

    def test_systemd_probe_bounds_output_and_preserves_status_parsing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-systemd-probe-") as base:
            root = Path(base)
            executable = root / "systemctl"
            environment_path = root / "environment"
            self._write_executable(
                executable,
                "import os, sys\n"
                "if 'show' in sys.argv:\n"
                "    chunk = bytes([122]) * 65536\n"
                "    for _ in range(32):\n"
                "        os.write(1, chunk)\n"
                "    os.write(1, b'\\nResult=oom-kill\\nExecMainCode=2\\nExecMainStatus=9\\nMemoryPeak=123456\\n')\n"
                "if 'is-active' in sys.argv:\n"
                "    sys.exit(3)\n",
            )
            launch = ToolMemoryLaunch(
                argv=("systemd-run",),
                unit=UNIT,
                limit_bytes=1024,
                environment_path=environment_path,
                systemctl=str(executable),
            )
            environment = {"PATH": os.environ.get("PATH", "")}

            result = inspect_tool_memory_result(launch, environment)
            running = tool_memory_unit_running(UNIT, environment, systemctl=str(executable))
            stopped = stop_tool_memory_unit(UNIT, environment, systemctl=str(executable))

        self.assertTrue(result.exceeded)
        self.assertEqual(result.main_code, 2)
        self.assertEqual(result.main_status, 9)
        self.assertEqual(result.memory_peak_bytes, 123456)
        self.assertFalse(running)
        self.assertTrue(stopped)

    def test_environment_probe_keeps_timeout_failure_shape(self) -> None:
        with (
            patch("vibeagent.workspace_environment_info.shutil.which", return_value="/tool"),
            patch(
                "vibeagent.workspace_environment_info.run_bounded_subprocess",
                side_effect=subprocess.TimeoutExpired(("/tool", "--version"), 2),
            ),
        ):
            result = read_runtime_tool_info("tool", ["tool", "--version"])

        self.assertTrue(result["available"])
        self.assertIsNone(result["version"])
        self.assertIn("timed out", str(result["message"]))

    @staticmethod
    def _write_executable(path: Path, body: str) -> None:
        path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
