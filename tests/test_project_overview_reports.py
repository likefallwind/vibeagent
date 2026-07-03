import unittest

from vibeagent import project_commands
from vibeagent import project_overview_reports


class ProjectOverviewReportsTests(unittest.TestCase):
    def test_project_commands_reexports_overview_report_helpers(self) -> None:
        self.assertIs(project_commands.format_overview_report_text, project_overview_reports.format_overview_report_text)
        self.assertIs(
            project_commands._format_project_command_report_item,
            project_overview_reports.format_project_command_report_item,
        )


if __name__ == "__main__":
    unittest.main()
