import unittest

from vibeagent import local_runtime_commands
from vibeagent import local_runtime_reports
from vibeagent.types import CommandResult


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


if __name__ == "__main__":
    unittest.main()
