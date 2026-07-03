import unittest

from vibeagent import process_commands
from vibeagent import process_report_helpers
from vibeagent import process_stop_commands
from vibeagent import process_wait_write_commands


class ProcessReportHelpersTests(unittest.TestCase):
    def test_process_modules_share_report_helpers(self) -> None:
        self.assertIs(process_commands.format_env_report_text, process_report_helpers.format_env_report_text)
        self.assertIs(process_commands.format_processes_report_text, process_report_helpers.format_processes_report_text)
        self.assertIs(process_commands.format_process_report_text, process_report_helpers.format_process_report_text)
        self.assertIs(
            process_commands.format_process_output_contexts_report_text,
            process_report_helpers.format_process_output_contexts_report_text,
        )
        self.assertIs(
            process_commands.format_process_output_diagnostics_report_text,
            process_report_helpers.format_process_output_diagnostics_report_text,
        )
        self.assertIs(process_commands.process_status_text, process_report_helpers.process_status_text)
        self.assertIs(process_commands.serialize_process_info, process_report_helpers.serialize_process_info)
        self.assertIs(
            process_commands.serialize_command_output_analysis,
            process_report_helpers.serialize_command_output_analysis,
        )
        self.assertIs(
            process_commands.format_structured_command_output_analysis_lines,
            process_report_helpers.format_structured_command_output_analysis_lines,
        )
        self.assertIs(process_stop_commands.process_status_text, process_report_helpers.process_status_text)
        self.assertIs(process_stop_commands.serialize_process_info, process_report_helpers.serialize_process_info)
        self.assertIs(process_wait_write_commands.process_status_text, process_report_helpers.process_status_text)
        self.assertIs(
            process_wait_write_commands.serialize_command_output_analysis,
            process_report_helpers.serialize_command_output_analysis,
        )


if __name__ == "__main__":
    unittest.main()
