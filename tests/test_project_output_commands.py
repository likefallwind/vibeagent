from __future__ import annotations

import unittest

from vibeagent import project_commands, project_output_commands


class ProjectOutputCommandModuleTests(unittest.TestCase):
    def test_project_commands_keeps_output_command_exports(self) -> None:
        self.assertIs(project_commands.get_output_contexts_text, project_output_commands.get_output_contexts_text)
        self.assertIs(project_commands.get_output_contexts_report, project_output_commands.get_output_contexts_report)
        self.assertIs(project_commands.format_output_contexts_report_text, project_output_commands.format_output_contexts_report_text)
        self.assertIs(project_commands.get_output_diagnostics_text, project_output_commands.get_output_diagnostics_text)
        self.assertIs(project_commands.get_output_diagnostics_report, project_output_commands.get_output_diagnostics_report)
        self.assertIs(
            project_commands.format_output_diagnostics_report_text,
            project_output_commands.format_output_diagnostics_report_text,
        )
        self.assertIs(project_commands.get_python_traceback_text, project_output_commands.get_python_traceback_text)
        self.assertIs(project_commands.get_python_traceback_report, project_output_commands.get_python_traceback_report)
        self.assertIs(
            project_commands.format_python_traceback_report_text,
            project_output_commands.format_python_traceback_report_text,
        )


if __name__ == "__main__":
    unittest.main()
