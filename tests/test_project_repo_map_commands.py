import unittest

from vibeagent import project_commands
from vibeagent import project_repo_map_commands


class ProjectRepoMapCommandsTests(unittest.TestCase):
    def test_project_commands_reexports_repo_map_helpers(self) -> None:
        self.assertIs(project_commands.get_repo_map_report, project_repo_map_commands.get_repo_map_report)
        self.assertIs(project_commands.get_repo_map_text, project_repo_map_commands.get_repo_map_text)
        self.assertIs(project_commands.format_repo_map_report_text, project_repo_map_commands.format_repo_map_report_text)
        self.assertIs(project_commands.format_repo_map_symbols, project_repo_map_commands.format_repo_map_symbols)
        self.assertIs(project_commands.format_symbol_file, project_repo_map_commands.format_symbol_file)


if __name__ == "__main__":
    unittest.main()
