from __future__ import annotations

import unittest

from vibeagent import project_commands, project_output_commands, project_output_reports, project_output_validation


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

    def test_project_output_commands_reexports_report_formatters(self) -> None:
        self.assertIs(
            project_output_commands.format_output_contexts_report_text,
            project_output_reports.format_output_contexts_report_text,
        )
        self.assertIs(
            project_output_commands.format_output_diagnostics_report_text,
            project_output_reports.format_output_diagnostics_report_text,
        )
        self.assertIs(
            project_output_commands.format_python_traceback_report_text,
            project_output_reports.format_python_traceback_report_text,
        )

    def test_project_output_validation_matches_command_error_text(self) -> None:
        self.assertEqual(
            project_output_commands.get_output_contexts_text("not-used", "app.py:1", context_lines=-1),
            project_output_validation.validate_output_context_options(
                project_output_commands.OUTPUT_CONTEXTS_USAGE,
                text="app.py:1",
                context_lines=-1,
                max_contexts=20,
                max_bytes_per_context=20_000,
            ),
        )
        self.assertEqual(
            project_output_commands.get_output_diagnostics_text("not-used", "app.py:1", max_diagnostics=0),
            project_output_validation.validate_output_diagnostic_options(
                project_output_commands.OUTPUT_DIAGNOSTICS_USAGE,
                text="app.py:1",
                context_lines=2,
                max_diagnostics=0,
                max_contexts=20,
                max_bytes_per_context=20_000,
            ),
        )


if __name__ == "__main__":
    unittest.main()
