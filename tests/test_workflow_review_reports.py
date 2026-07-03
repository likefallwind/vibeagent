import unittest

from vibeagent import workflow_commands
from vibeagent import workflow_review_reports


class WorkflowReviewReportsTests(unittest.TestCase):
    def test_workflow_commands_reexports_review_report_helpers(self) -> None:
        self.assertIs(workflow_commands.final_review_status_checks, workflow_review_reports.final_review_status_checks)
        self.assertIs(workflow_commands.final_review_common_report, workflow_review_reports.final_review_common_report)
        self.assertIs(
            workflow_commands.serialize_focused_review_command,
            workflow_review_reports.serialize_focused_review_command,
        )
        self.assertIs(workflow_commands.local_final_review_workspace, workflow_review_reports.local_final_review_workspace)


if __name__ == "__main__":
    unittest.main()
