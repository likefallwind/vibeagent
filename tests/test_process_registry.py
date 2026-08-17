from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vibeagent import process_registry, process_runtime
from vibeagent.workspace_core import RunWorkspace


class ProcessRegistryModuleTests(unittest.TestCase):
    def test_process_runtime_keeps_registry_exports(self) -> None:
        self.assertIs(process_runtime.PersistentProcessRecord, process_registry.PersistentProcessRecord)
        self.assertIs(process_runtime.process_record_path, process_registry.process_record_path)
        self.assertIs(process_runtime.read_persistent_process_record, process_registry.read_persistent_process_record)
        self.assertIs(process_runtime.write_persistent_process_record, process_registry.write_persistent_process_record)
        self.assertIs(process_runtime.process_signal_name, process_registry.process_signal_name)

    def test_writes_and_reads_persistent_process_record_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            logs = root / ".vibeagent" / "runs" / "run-1"
            logs.mkdir(parents=True)
            stdout_path = logs / "stdout.log"
            stderr_path = logs / "stderr.log"
            exit_code_path = logs / "exit-code.txt"
            workspace = RunWorkspace(root=root, run_id="run-1", session_dir=root / ".vibeagent" / "sessions" / "run-1")

            process_registry.write_persistent_process_record(
                workspace,
                process_registry.PersistentProcessRecord(
                    id="bg-1",
                    command="python3 -m http.server",
                    cwd=".",
                    pid=12345,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    exit_code_path=exit_code_path,
                    start_ticks=99,
                    memory_unit="vibeagent-tool-0123456789abcdef0123456789abcdef.service",
                ),
            )

            record = process_registry.read_persistent_process_record(root, "bg-1")
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.id, "bg-1")
            self.assertEqual(record.command, "python3 -m http.server")
            self.assertEqual(record.pid, 12345)
            self.assertEqual(record.stdout_path, stdout_path.resolve())
            self.assertEqual(record.stderr_path, stderr_path.resolve())
            self.assertEqual(record.exit_code_path, exit_code_path.resolve())
            self.assertEqual(record.start_ticks, 99)
            self.assertEqual(
                record.memory_unit,
                "vibeagent-tool-0123456789abcdef0123456789abcdef.service",
            )

    def test_rejects_unsafe_registry_and_log_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            self.assertIsNone(process_registry.process_record_path(root, "../bg-1"))
            self.assertIsNone(process_registry.resolve_process_log_path(root, "../outside.log"))
            self.assertIsNone(
                process_registry.parse_persistent_process_record(
                    root,
                    {
                        "id": "../bg-1",
                        "command": "sleep 1",
                        "cwd": ".",
                        "pid": 1,
                        "stdout_path": "stdout.log",
                        "stderr_path": "stderr.log",
                    },
                )
            )

    def test_process_signal_name_handles_shell_and_negative_codes(self) -> None:
        self.assertEqual(process_registry.process_signal_name(-15), "SIGTERM")
        self.assertEqual(process_registry.process_signal_name(143), "SIGTERM")
        self.assertIsNone(process_registry.process_signal_name(1))


if __name__ == "__main__":
    unittest.main()
