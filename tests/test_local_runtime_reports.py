import unittest

from vibeagent import local_runtime_commands
from vibeagent import local_runtime_reports
from vibeagent.types import CommandResult, OutputContextResult


class LocalRuntimeReportsTests(unittest.TestCase):
    def test_local_runtime_commands_reexports_report_helpers(self) -> None:
        self.assertIs(
            local_runtime_commands.empty_command_output_analysis,
            local_runtime_reports.empty_command_output_analysis,
        )
        self.assertIs(local_runtime_commands.serialize_command_result, local_runtime_reports.serialize_command_result)
        self.assertIs(local_runtime_commands.serialize_command_check, local_runtime_reports.serialize_command_check)
        self.assertIs(
            local_runtime_commands.serialize_command_output_analysis,
            local_runtime_reports.serialize_command_output_analysis,
        )
        self.assertIs(
            local_runtime_commands.format_structured_command_output_analysis_lines,
            local_runtime_reports.format_structured_command_output_analysis_lines,
        )
        self.assertIs(
            local_runtime_commands.validate_run_output_context_options,
            local_runtime_reports.validate_run_output_context_options,
        )
        self.assertIs(
            local_runtime_commands.format_command_check_report_text,
            local_runtime_reports.format_command_check_report_text,
        )
        self.assertIs(local_runtime_commands.format_run_report_text, local_runtime_reports.format_run_report_text)
        self.assertIs(
            local_runtime_commands.format_run_sequence_report_text,
            local_runtime_reports.format_run_sequence_report_text,
        )
        self.assertIs(
            local_runtime_commands.format_check_run_sequence_report_text,
            local_runtime_reports.format_check_run_sequence_report_text,
        )
        self.assertIs(
            local_runtime_commands.format_check_start_report_text,
            local_runtime_reports.format_check_start_report_text,
        )
        self.assertIs(local_runtime_commands.format_start_report_text, local_runtime_reports.format_start_report_text)

    def test_serialize_command_result_includes_duration_ms(self) -> None:
        result = CommandResult(
            command="python3 --version",
            exit_code=0,
            stdout="Python 3\n",
            stderr="",
            timed_out=False,
            signal=None,
            duration_ms=42,
        )

        payload = local_runtime_reports.serialize_command_result(result)

        self.assertEqual(payload["durationMs"], 42)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["clean"])

    def test_serialize_command_result_marks_source_output_contexts_not_clean(self) -> None:
        result = CommandResult(
            command="python3 -m unittest",
            exit_code=0,
            stdout="tests/test_app.py:3: warning\n",
            stderr="",
            timed_out=False,
            signal=None,
            output_contexts=[
                OutputContextResult(
                    path="tests/test_app.py",
                    line=3,
                    column=None,
                    raw="tests/test_app.py:3",
                    ok=True,
                    content="3: self.assertTrue(True)\n",
                    message="Read tests/test_app.py:3.",
                )
            ],
            output_context_total_refs=1,
        )

        payload = local_runtime_reports.serialize_command_result(result)

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["clean"])


if __name__ == "__main__":
    unittest.main()
