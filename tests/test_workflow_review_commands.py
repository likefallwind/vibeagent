from __future__ import annotations

import unittest

from vibeagent import workflow_commands, workflow_review_commands


class WorkflowReviewCommandModuleTests(unittest.TestCase):
    def test_workflow_commands_reexports_review_helpers(self) -> None:
        self.assertIs(workflow_commands.get_review_report, workflow_review_commands.get_review_report)
        self.assertIs(workflow_commands.get_review_text, workflow_review_commands.get_review_text)
        self.assertIs(workflow_commands.format_review_report_text, workflow_review_commands.format_review_report_text)
        self.assertIs(workflow_commands.get_handoff_report, workflow_review_commands.get_handoff_report)
        self.assertIs(workflow_commands.get_handoff_text, workflow_review_commands.get_handoff_text)
        self.assertIs(workflow_commands.format_handoff_report_text, workflow_review_commands.format_handoff_report_text)
        self.assertIs(workflow_commands.get_handoff_plan_text, workflow_review_commands.get_handoff_plan_text)


if __name__ == "__main__":
    unittest.main()
