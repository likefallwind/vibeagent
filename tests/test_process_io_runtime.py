from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vibeagent import (
    process_background_lookup,
    process_io_helpers,
    process_io_runtime,
    process_read_runtime,
    process_runtime,
    process_wait_runtime,
    process_write_runtime,
)
from vibeagent.agent_approval_preview import approval_preview_summary, command_check_fingerprint_payload
from vibeagent.agent_tool_results import build_tool_result_payload
from vibeagent.process_registry import PersistentProcessRecord
from vibeagent.types import (
    CheckFocusedTestCommandsObservation,
    CheckRunCommandsObservation,
    CheckSuggestedChecksObservation,
    CheckStartCommandObservation,
    CheckWriteProcessObservation,
    CommandCheckObservation,
    FocusedTestCommand,
    RunCommandAction,
    RunCommandItem,
    RunCommandsAction,
    RunFocusedTestCommandsAction,
    RunSuggestedChecksAction,
    StartCommandAction,
    SuggestedCheck,
    WriteProcessAction,
)


class ProcessIORuntimeModuleTests(unittest.TestCase):
    def test_process_runtime_reexports_io_runtime_helpers(self) -> None:
        self.assertIs(process_runtime.read_background_process, process_io_runtime.read_background_process)
        self.assertIs(process_runtime.wait_background_process, process_io_runtime.wait_background_process)
        self.assertIs(process_runtime.check_write_background_process, process_io_runtime.check_write_background_process)
        self.assertIs(process_runtime.write_background_process, process_io_runtime.write_background_process)
        self.assertIs(process_io_runtime.read_background_process, process_read_runtime.read_background_process)
        self.assertIs(process_runtime.wait_persistent_process, process_wait_runtime.wait_persistent_process)
        self.assertIs(process_runtime.wait_background_process_output, process_wait_runtime.wait_background_process_output)
        self.assertIs(process_runtime.match_process_output, process_wait_runtime.match_process_output)
        self.assertIs(process_runtime.read_text_tail, process_wait_runtime.read_text_tail)
        self.assertIs(process_io_runtime.wait_persistent_process, process_wait_runtime.wait_persistent_process)
        self.assertIs(process_io_runtime.wait_background_process_output, process_wait_runtime.wait_background_process_output)
        self.assertIs(process_io_runtime.match_process_output, process_wait_runtime.match_process_output)
        self.assertIs(process_io_runtime.read_text_tail, process_wait_runtime.read_text_tail)
        self.assertIs(process_io_runtime.write_process_content_sha256, process_io_helpers.write_process_content_sha256)
        self.assertIs(process_io_runtime._filter_output_lines, process_io_helpers.filter_output_lines)
        self.assertIs(process_io_runtime._background_processes, process_background_lookup.background_processes)

    def test_process_write_runtime_builds_unavailable_observations(self) -> None:
        record = PersistentProcessRecord(
            id="proc-1",
            command="python app.py",
            cwd=".",
            pid=123,
            stdout_path=Path("out.log"),
            stderr_path=Path("err.log"),
        )
        content_sha256 = process_io_helpers.write_process_content_sha256("hello\n")

        check = process_write_runtime.persistent_check_write_observation(
            process_id="proc-1",
            record=record,
            running=True,
            content="hello\n",
            content_sha256=content_sha256,
        )
        write = process_write_runtime.persistent_write_observation(
            process_id="proc-1",
            record=record,
            running=False,
            content="hello\n",
            content_sha256=content_sha256,
        )
        unknown = process_write_runtime.unknown_write_observation(
            process_id="missing",
            content="hello\n",
            content_sha256=content_sha256,
        )

        self.assertEqual(check.kind, "check_write_process")
        self.assertFalse(check.ok)
        self.assertIn("stdin is only available", check.message)
        self.assertEqual(write.kind, "write_process")
        self.assertFalse(write.running)
        self.assertIn("process has exited", write.message)
        self.assertEqual(unknown.message, "Unknown background process id.")

    def test_process_io_helpers_hash_and_filter_output(self) -> None:
        self.assertEqual(
            process_io_helpers.write_process_content_sha256("alpha\n"),
            process_io_runtime.write_process_content_sha256("alpha\n"),
        )
        self.assertEqual(
            process_io_helpers.filter_output_lines("ok\nERROR app.py:1\nok again\n", r"ERROR|again"),
            "ERROR app.py:1\nok again\n",
        )
        self.assertEqual(process_io_helpers.filter_output_lines("all\nlines\n", None), "all\nlines\n")

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

    def test_run_command_preview_matches_normalized_cwd(self) -> None:
        observation = CommandCheckObservation(
            kind="command_check",
            ok=True,
            command="npm test",
            cwd="web",
            cwd_ok=True,
            blocked=False,
            block_reason=None,
            executable_available=True,
            missing_tool=None,
            message="Command can run.",
        )

        matching_preview = approval_preview_summary(
            RunCommandAction(type="run_command", command="npm test", cwd="./web"),
            [observation],
        )

        self.assertIn("Command can run", matching_preview or "")

    def test_command_check_fingerprint_payload_normalizes_cwd(self) -> None:
        first = command_check_fingerprint_payload(
            [
                CommandCheckObservation(
                    kind="command_check",
                    ok=True,
                    command="npm test",
                    cwd="./web",
                    cwd_ok=True,
                    blocked=False,
                    block_reason=None,
                    executable_available=True,
                    missing_tool=None,
                    message="Command can run.",
                )
            ]
        )
        second = command_check_fingerprint_payload(
            [
                CommandCheckObservation(
                    kind="command_check",
                    ok=True,
                    command="npm test",
                    cwd="web",
                    cwd_ok=True,
                    blocked=False,
                    block_reason=None,
                    executable_available=True,
                    missing_tool=None,
                    message="Command can run.",
                )
            ]
        )

        self.assertEqual(first, second)
        self.assertIn('"cwd":"web"', first)

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

    def test_start_command_preview_matches_default_output_limit(self) -> None:
        observation = CheckStartCommandObservation(
            kind="check_start_command",
            ok=True,
            command="python3 -m http.server",
            cwd=".",
            cwd_ok=True,
            blocked=False,
            block_reason=None,
            executable_available=True,
            missing_tool=None,
            message="Command can run.",
        )

        matching_preview = approval_preview_summary(
            StartCommandAction(type="start_command", command="python3 -m http.server"),
            [observation],
        )
        custom_output_limit_preview = approval_preview_summary(
            StartCommandAction(type="start_command", command="python3 -m http.server", max_output_chars=1000),
            [observation],
        )

        self.assertIn("Command can run", matching_preview or "")
        self.assertIsNone(custom_output_limit_preview)

    def test_start_command_preview_matches_normalized_cwd(self) -> None:
        observation = CheckStartCommandObservation(
            kind="check_start_command",
            ok=True,
            command="python3 -m http.server",
            cwd="web",
            cwd_ok=True,
            blocked=False,
            block_reason=None,
            executable_available=True,
            missing_tool=None,
            message="Command can run.",
        )

        matching_preview = approval_preview_summary(
            StartCommandAction(type="start_command", command="python3 -m http.server", cwd="./web"),
            [observation],
        )

        self.assertIn("Command can run", matching_preview or "")

    def test_run_suggested_checks_preview_matches_runtime_options(self) -> None:
        observation = CheckSuggestedChecksObservation(
            kind="check_suggested_checks",
            ok=True,
            checks=[
                CommandCheckObservation(
                    kind="command_check",
                    ok=True,
                    command="python -m unittest discover -s tests",
                    cwd=".",
                    cwd_ok=True,
                    blocked=False,
                    block_reason=None,
                    executable_available=True,
                    missing_tool=None,
                    message="Command can run.",
                )
            ],
            suggested_checks=[
                SuggestedCheck(
                    command="python -m unittest discover -s tests",
                    cwd=".",
                    source="tests",
                    reason="unittest tests found",
                )
            ],
            total=1,
            truncated=False,
            max_commands=1,
            message="Preflighted 1/1 suggested check command(s); 0 failed; all available.",
        )

        matching_preview = approval_preview_summary(
            RunSuggestedChecksAction(type="run_suggested_checks", max_commands=1),
            [observation],
        )
        custom_timeout_preview = approval_preview_summary(
            RunSuggestedChecksAction(type="run_suggested_checks", max_commands=1, timeout_ms=1000),
            [observation],
        )

        self.assertIn("commands=1", matching_preview or "")
        self.assertIsNone(custom_timeout_preview)

    def test_run_focused_test_commands_preview_matches_runtime_options(self) -> None:
        observation = CheckFocusedTestCommandsObservation(
            kind="check_focused_test_commands",
            ok=True,
            checks=[
                CommandCheckObservation(
                    kind="command_check",
                    ok=True,
                    command="python -m unittest tests.test_app",
                    cwd=".",
                    cwd_ok=True,
                    blocked=False,
                    block_reason=None,
                    executable_available=True,
                    missing_tool=None,
                    message="Command can run.",
                )
            ],
            focused_commands=[
                FocusedTestCommand(
                    command="python -m unittest tests.test_app",
                    cwd=".",
                    test_path="tests/test_app.py",
                    source="related_tests",
                    reason="related test",
                )
            ],
            target_paths=["app.py"],
            total=1,
            truncated=False,
            max_commands=1,
            related_tests_total=1,
            message="Preflighted 1/1 focused test command(s); 0 failed; all available.",
            requested_paths=["app.py"],
        )

        matching_preview = approval_preview_summary(
            RunFocusedTestCommandsAction(type="run_focused_test_commands", paths=["app.py"], max_commands=1),
            [observation],
        )
        custom_output_preview = approval_preview_summary(
            RunFocusedTestCommandsAction(
                type="run_focused_test_commands",
                paths=["app.py"],
                max_commands=1,
                max_output_chars=1000,
            ),
            [observation],
        )

        self.assertIn("commands=1", matching_preview or "")
        self.assertIsNone(custom_output_preview)


if __name__ == "__main__":
    unittest.main()
