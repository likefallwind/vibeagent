from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vibeagent import process_io_runtime, process_runtime


class ProcessIORuntimeModuleTests(unittest.TestCase):
    def test_process_runtime_reexports_io_runtime_helpers(self) -> None:
        self.assertIs(process_runtime.read_background_process, process_io_runtime.read_background_process)
        self.assertIs(process_runtime.wait_background_process, process_io_runtime.wait_background_process)
        self.assertIs(process_runtime.check_write_background_process, process_io_runtime.check_write_background_process)
        self.assertIs(process_runtime.write_background_process, process_io_runtime.write_background_process)
        self.assertIs(process_runtime.wait_persistent_process, process_io_runtime.wait_persistent_process)
        self.assertIs(process_runtime.wait_background_process_output, process_io_runtime.wait_background_process_output)
        self.assertIs(process_runtime.match_process_output, process_io_runtime.match_process_output)
        self.assertIs(process_runtime.read_text_tail, process_io_runtime.read_text_tail)

    def test_match_process_output_supports_plain_and_regex_patterns(self) -> None:
        self.assertEqual(
            process_io_runtime.match_process_output(
                "server ready\n",
                "",
                stdout_contains="ready",
                stderr_contains=None,
                regex=False,
            ),
            (True, "stdout", "ready"),
        )
        self.assertEqual(
            process_io_runtime.match_process_output(
                "",
                "ERROR app.py:2 failed\n",
                stdout_contains=None,
                stderr_contains=r"app\.py:\d+",
                regex=True,
            ),
            (True, "stderr", r"app\.py:\d+"),
        )
        self.assertEqual(
            process_io_runtime.match_process_output(
                "booting\n",
                "",
                stdout_contains="ready",
                stderr_contains=None,
                regex=False,
            ),
            (False, None, None),
        )

    def test_read_text_tail_returns_bounded_file_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.log"
            path.write_text("0123456789", encoding="utf-8")

            self.assertEqual(process_io_runtime.read_text_tail(path, 4), "6789")
            self.assertEqual(process_io_runtime.read_text_tail(Path(tmp) / "missing.log", 4), "")

    def test_missing_process_reports_unknown_for_read_wait_and_write_paths(self) -> None:
        root = Path("/tmp/vibeagent-missing-io-process").resolve()

        read = process_io_runtime.read_background_process(root, "missing")
        wait = process_io_runtime.wait_background_process(root, "missing", timeout_ms=100)
        check_write = process_io_runtime.check_write_background_process(root, "missing", "hello\n")
        write = process_io_runtime.write_background_process(root, "missing", "hello\n")

        self.assertEqual(read.kind, "read_process")
        self.assertFalse(read.ok)
        self.assertIn("Unknown background process id", read.message)
        self.assertEqual(wait.kind, "wait_process")
        self.assertFalse(wait.ok)
        self.assertIn("Unknown background process id", wait.message)
        self.assertEqual(check_write.kind, "check_write_process")
        self.assertFalse(check_write.ok)
        self.assertIn("Unknown background process id", check_write.message)
        self.assertEqual(write.kind, "write_process")
        self.assertFalse(write.ok)
        self.assertIn("Unknown background process id", write.message)


if __name__ == "__main__":
    unittest.main()
