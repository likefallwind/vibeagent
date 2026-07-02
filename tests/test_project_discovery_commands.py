from __future__ import annotations

import unittest

from vibeagent import project_commands, project_discovery_commands


class ProjectDiscoveryCommandsTests(unittest.TestCase):
    def test_project_commands_keeps_discovery_command_exports(self) -> None:
        self.assertIs(project_commands.get_search_text, project_discovery_commands.get_search_text)
        self.assertIs(project_commands.get_search_report, project_discovery_commands.get_search_report)
        self.assertIs(project_commands.format_search_report_text, project_discovery_commands.format_search_report_text)
        self.assertIs(project_commands.get_search_contexts_text, project_discovery_commands.get_search_contexts_text)
        self.assertIs(project_commands.get_search_contexts_report, project_discovery_commands.get_search_contexts_report)
        self.assertIs(
            project_commands.format_search_contexts_report_text,
            project_discovery_commands.format_search_contexts_report_text,
        )
        self.assertIs(project_commands.get_find_files_text, project_discovery_commands.get_find_files_text)
        self.assertIs(project_commands.get_find_files_report, project_discovery_commands.get_find_files_report)
        self.assertIs(project_commands.format_find_files_report_text, project_discovery_commands.format_find_files_report_text)
        self.assertIs(project_commands.get_glob_text, project_discovery_commands.get_glob_text)
        self.assertIs(project_commands.get_glob_report, project_discovery_commands.get_glob_report)
        self.assertIs(project_commands.format_glob_report_text, project_discovery_commands.format_glob_report_text)
        self.assertIs(project_commands.get_tree_text, project_discovery_commands.get_tree_text)
        self.assertIs(project_commands.get_tree_report, project_discovery_commands.get_tree_report)
        self.assertIs(project_commands.format_tree_report_text, project_discovery_commands.format_tree_report_text)


if __name__ == "__main__":
    unittest.main()
