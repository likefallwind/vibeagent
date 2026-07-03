from __future__ import annotations

import unittest

from vibeagent import workflow_change_commands, workflow_commands


class WorkflowChangeCommandsTests(unittest.TestCase):
    def test_workflow_commands_reexports_change_commands(self) -> None:
        self.assertIs(workflow_commands.get_changes_report, workflow_change_commands.get_changes_report)
        self.assertIs(workflow_commands.get_changes_text, workflow_change_commands.get_changes_text)
        self.assertIs(workflow_commands.format_changes_report_text, workflow_change_commands.format_changes_report_text)


if __name__ == "__main__":
    unittest.main()
