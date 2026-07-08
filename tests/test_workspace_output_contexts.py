import unittest

from vibeagent import workspace_file_context, workspace_file_read, workspace_output_contexts


class WorkspaceOutputContextsTests(unittest.TestCase):
    def test_workspace_file_read_reexports_context_helpers(self) -> None:
        self.assertIs(
            workspace_file_read.read_project_file_context_result,
            workspace_file_context.read_project_file_context_result,
        )
        self.assertIs(
            workspace_file_read.read_project_file_tail_result,
            workspace_file_context.read_project_file_tail_result,
        )

    def test_workspace_file_read_reexports_output_context_helpers(self) -> None:
        self.assertIs(
            workspace_file_read.read_output_contexts_result,
            workspace_output_contexts.read_output_contexts_result,
        )
        self.assertIs(
            workspace_file_read.extract_output_line_references,
            workspace_output_contexts.extract_output_line_references,
        )


if __name__ == "__main__":
    unittest.main()
