from __future__ import annotations

import signal
import unittest
from pathlib import Path

from vibeagent import process_lifecycle, process_runtime, process_stop_runtime


class ProcessStopRuntimeModuleTests(unittest.TestCase):
    def test_process_runtime_reexports_stop_runtime_helpers(self) -> None:
        self.assertIs(process_runtime.list_background_processes, process_stop_runtime.list_background_processes)
        self.assertIs(process_runtime.check_stop_all_background_processes, process_stop_runtime.check_stop_all_background_processes)
        self.assertIs(process_runtime.check_stop_background_process, process_stop_runtime.check_stop_background_process)
        self.assertIs(process_runtime.stop_all_background_processes, process_stop_runtime.stop_all_background_processes)
        self.assertIs(process_runtime.stop_background_process, process_stop_runtime.stop_background_process)

    def test_process_runtime_reexports_lifecycle_helpers(self) -> None:
        self.assertIs(process_runtime._close_background_handles, process_lifecycle.close_background_handles)
        self.assertIs(process_runtime._terminate_process, process_lifecycle.terminate_process)
        self.assertIs(process_runtime._signal_name, process_lifecycle.signal_name)

    def test_stop_runtime_reports_unknown_process_without_mutating_registry(self) -> None:
        root = Path("/tmp/vibeagent-missing-process").resolve()

        check = process_stop_runtime.check_stop_background_process(root, "missing")
        stopped = process_stop_runtime.stop_background_process(root, "missing")
        listed = process_stop_runtime.list_background_processes(root)

        self.assertEqual(check.kind, "check_stop_process")
        self.assertFalse(check.ok)
        self.assertIn("Unknown background process id", check.message)
        self.assertEqual(stopped.kind, "stop_process")
        self.assertFalse(stopped.ok)
        self.assertIn("Unknown background process id", stopped.message)
        self.assertEqual(listed.kind, "list_processes")
        self.assertEqual(listed.processes, [])

    def test_lifecycle_signal_name_decodes_negative_return_codes(self) -> None:
        self.assertEqual(process_lifecycle.signal_name(-signal.SIGTERM), "SIGTERM")
        self.assertIsNone(process_lifecycle.signal_name(1))


if __name__ == "__main__":
    unittest.main()
