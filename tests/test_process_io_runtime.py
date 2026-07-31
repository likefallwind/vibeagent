from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vibeagent import process_io_runtime, process_runtime, process_wait_runtime
from vibeagent.agent_approval_preview import approval_preview_summary
from vibeagent.agent_tool_results import build_tool_result_payload
from vibeagent.types import (
    CheckRunCommandsObservation,
    CheckWriteProcessObservation,
    CommandCheckObservation,
    RunCommandAction,
    RunCommandItem,
    RunCommandsAction,
    WriteProcessAction,
)


class ProcessIORuntimeModuleTests(unittest.TestCase):
    def test_process_runtime_reexports_io_runtime_helpers(self) -> None:
        self.assertIs(process_runtime.read_background_process, process_io_runtime.read_background_process)
        self.assertIs(process_runtime.wait_background_process, process_io_runtime.wait_background_process)
        self.assertIs(process_runtime.check_write_background_process, process_io_runtime.check_write_background_process)
        self.assertIs(process_runtime.write_background_process, process_io_runtime.write_background_process)
        self.assertIs(process_runtime.wait_persistent_process, process_wait_runtime.wait_persistent_process)
        self.assertIs(process_runtime.wait_background_process_output, process_wait_runtime.wait_background_process_output)
        self.assertIs(process_runtime.match_process_output, process_wait_runtime.match_process_output)
        self.assertIs(process_runtime.read_text_tail, process_wait_runtime.read_text_tail)
        self.assertIs(process_io_runtime.wait_persistent_process, process_wait_runtime.wait_persistent_process)
        self.assertIs(process_io_runtime.wait_background_process_output, process_wait_runtime.wait_background_process_output)
        self.assertIs(process_io_runtime.match_process_output, process_wait_runtime.match_process_output)
        self.assertIs(process_io_runtime.read_text_tail, process_wait_runtime.read_text_tail)

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
        self.assertTrue(check_write.content_sha256)
        self.assertEqual(write.kind, "write_process")
        self.assertFalse(write.ok)
        self.assertIn("Unknown background process id", write.message)
        self.assertEqual(write.content_sha256, check_write.content_sha256)

    def test_write_process_preview_matches_approval_by_content_hash(self) -> None:
        observation = CheckWriteProcessObservation(
            kind="check_write_process",
            process_id="proc-1",
            pid=123,
            ok=True,
            running=True,
            command="python3 app.py",
            cwd=".",
            content_chars=6,
            content_sha256=process_io_runtime.write_process_content_sha256("alpha\n"),
            message="Can write 6 character(s) to process proc-1.",
        )

        matching_preview = approval_preview_summary(
            WriteProcessAction(type="write_process", process_id="proc-1", content="alpha\n"),
            [observation],
        )
        mismatched_same_length_preview = approval_preview_summary(
            WriteProcessAction(type="write_process", process_id="proc-1", content="bravo\n"),
            [observation],
        )

        self.assertIn("Can write 6 character", matching_preview or "")
        self.assertIsNone(mismatched_same_length_preview)
        self.assertNotIn("content_sha256", build_tool_result_payload(observation))

    def test_run_command_preview_matches_default_execution_parameters(self) -> None:
        observation = CommandCheckObservation(
            kind="command_check",
            ok=True,
            command="python3 -m unittest",
            cwd=".",
            cwd_ok=True,
            blocked=False,
            block_reason=None,
            executable_available=True,
            missing_tool=None,
            message="Command can run.",
        )

        matching_preview = approval_preview_summary(
            RunCommandAction(type="run_command", command="python3 -m unittest"),
            [observation],
        )
        custom_timeout_preview = approval_preview_summary(
            RunCommandAction(type="run_command", command="python3 -m unittest", timeout_ms=100),
            [observation],
        )

        self.assertIn("Command can run", matching_preview or "")
        self.assertIsNone(custom_timeout_preview)

    def test_run_commands_preview_matches_approval_by_command_parameters(self) -> None:
        command = RunCommandItem(command="python3 -m unittest", timeout_ms=1000)
        observation = CheckRunCommandsObservation(
            kind="check_run_commands",
            ok=True,
            checks=[
                CommandCheckObservation(
                    kind="command_check",
                    ok=True,
                    command=command.command,
                    cwd=".",
                    cwd_ok=True,
                    blocked=False,
                    block_reason=None,
                    executable_available=True,
                    missing_tool=None,
                    message="Command can run.",
                )
            ],
            commands=[command],
            message="Preflighted 1 command(s); 0 failed.",
        )

        matching_preview = approval_preview_summary(
            RunCommandsAction(type="run_commands", commands=[command]),
            [observation],
        )
        mismatched_timeout_preview = approval_preview_summary(
            RunCommandsAction(
                type="run_commands",
                commands=[RunCommandItem(command="python3 -m unittest", timeout_ms=2000)],
            ),
            [observation],
        )

        self.assertIn("commands=1", matching_preview or "")
        self.assertIsNone(mismatched_timeout_preview)
        self.assertNotIn("commands", build_tool_result_payload(observation))


if __name__ == "__main__":
    unittest.main()
