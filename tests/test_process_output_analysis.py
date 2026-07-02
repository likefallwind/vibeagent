from __future__ import annotations

import unittest

from vibeagent import process_output_analysis, process_runtime
from vibeagent.types import CommandResult, ReadProcessObservation


class ProcessOutputAnalysisModuleTests(unittest.TestCase):
    def test_process_runtime_reexports_output_analysis_helpers(self) -> None:
        self.assertIs(
            process_runtime.attach_output_analysis_to_command_result,
            process_output_analysis.attach_output_analysis_to_command_result,
        )
        self.assertIs(
            process_runtime.attach_output_analysis_to_process_observation,
            process_output_analysis.attach_output_analysis_to_process_observation,
        )
        self.assertIs(process_runtime.command_result_failed, process_output_analysis.command_result_failed)
        self.assertIs(process_runtime.process_observation_failed, process_output_analysis.process_observation_failed)

    def test_command_result_failed_matches_runtime_failure_semantics(self) -> None:
        ok = CommandResult(command="true", exit_code=0, stdout="", stderr="", timed_out=False, signal=None, timeout_ms=1000)
        failed = CommandResult(command="false", exit_code=1, stdout="", stderr="", timed_out=False, signal=None, timeout_ms=1000)
        unknown = CommandResult(command="blocked", exit_code=None, stdout="", stderr="", timed_out=False, signal=None, timeout_ms=1000)
        timed_out = CommandResult(command="sleep 10", exit_code=None, stdout="", stderr="", timed_out=True, signal=None, timeout_ms=1000)

        self.assertFalse(process_output_analysis.command_result_failed(ok))
        self.assertTrue(process_output_analysis.command_result_failed(failed))
        self.assertTrue(process_output_analysis.command_result_failed(unknown))
        self.assertTrue(process_output_analysis.command_result_failed(timed_out))

    def test_process_observation_failed_ignores_unknown_failed_reads_but_flags_exited_failures(self) -> None:
        missing = ReadProcessObservation(
            kind="read_process",
            process_id="missing",
            pid=None,
            ok=False,
            running=False,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=1000,
            message="Unknown background process id.",
        )
        running = ReadProcessObservation(
            kind="read_process",
            process_id="bg-1",
            pid=123,
            ok=True,
            running=True,
            exit_code=None,
            signal=None,
            stdout="",
            stderr="",
            max_output_chars=1000,
            message="Process bg-1 is running.",
        )
        failed = ReadProcessObservation(
            kind="read_process",
            process_id="bg-1",
            pid=123,
            ok=True,
            running=False,
            exit_code=2,
            signal=None,
            stdout="",
            stderr="ERROR app.py:1 failed\n",
            max_output_chars=1000,
            message="Process bg-1 exited.",
        )

        self.assertFalse(process_output_analysis.process_observation_failed(missing))
        self.assertFalse(process_output_analysis.process_observation_failed(running))
        self.assertTrue(process_output_analysis.process_observation_failed(failed))


if __name__ == "__main__":
    unittest.main()
