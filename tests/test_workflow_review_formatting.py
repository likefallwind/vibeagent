import unittest

from vibeagent import workflow_commands
from vibeagent import workflow_review_formatting


class WorkflowReviewFormattingTests(unittest.TestCase):
    def test_workflow_commands_reexports_review_formatting_helpers(self) -> None:
        self.assertIs(workflow_commands.filter_handoff_status, workflow_review_formatting.filter_handoff_status)
        self.assertIs(workflow_commands.is_runtime_status_path, workflow_review_formatting.is_runtime_status_path)
        self.assertIs(workflow_commands.format_review_file, workflow_review_formatting.format_review_file)
        self.assertIs(workflow_commands.format_review_check, workflow_review_formatting.format_review_check)
        self.assertIs(workflow_commands.format_check_location, workflow_review_formatting.format_check_location)


if __name__ == "__main__":
    unittest.main()
