import unittest

from vibeagent import project_context_commands
from vibeagent import project_context_formatting


class ProjectContextFormattingTests(unittest.TestCase):
    def test_project_context_commands_reexports_formatting_helpers(self) -> None:
        self.assertIs(project_context_commands.format_project_command, project_context_formatting.format_project_command)
        self.assertIs(project_context_commands.format_commands_report_text, project_context_formatting.format_commands_report_text)
        self.assertIs(
            project_context_commands.format_related_tests_report_text,
            project_context_formatting.format_related_tests_report_text,
        )
        self.assertIs(
            project_context_commands.format_focused_test_commands_report_text,
            project_context_formatting.format_focused_test_commands_report_text,
        )
        self.assertIs(
            project_context_commands.format_check_focused_test_commands_report_text,
            project_context_formatting.format_check_focused_test_commands_report_text,
        )
        self.assertIs(
            project_context_commands.format_run_focused_test_commands_report_text,
            project_context_formatting.format_run_focused_test_commands_report_text,
        )
        self.assertIs(project_context_commands.format_manifests_report_text, project_context_formatting.format_manifests_report_text)
        self.assertIs(
            project_context_commands.format_instructions_report_text,
            project_context_formatting.format_instructions_report_text,
        )
        self.assertIs(project_context_commands.format_todos_report_text, project_context_formatting.format_todos_report_text)
        self.assertIs(project_context_commands.format_manifest_summary, project_context_formatting.format_manifest_summary)


if __name__ == "__main__":
    unittest.main()
