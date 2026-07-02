import unittest

from vibeagent import workspace_git_branch_ops, workspace_git_ops


class WorkspaceGitBranchOpsTests(unittest.TestCase):
    def test_workspace_git_ops_reexports_branch_helpers(self) -> None:
        self.assertIs(workspace_git_ops.validate_git_branch_name, workspace_git_branch_ops.validate_git_branch_name)
        self.assertIs(workspace_git_ops.git_branch_exists, workspace_git_branch_ops.git_branch_exists)
        self.assertIs(workspace_git_ops.read_git_current_branch, workspace_git_branch_ops.read_git_current_branch)
        self.assertIs(workspace_git_ops.git_status_has_non_runtime_changes, workspace_git_branch_ops.git_status_has_non_runtime_changes)
        self.assertIs(workspace_git_ops.read_git_head, workspace_git_branch_ops.read_git_head)
        self.assertIs(workspace_git_ops.normalize_git_index_paths, workspace_git_branch_ops.normalize_git_index_paths)

    def test_git_status_has_non_runtime_changes_ignores_runtime_files(self) -> None:
        self.assertFalse(workspace_git_branch_ops.git_status_has_non_runtime_changes("?? .vibeagent/sessions/run/events.jsonl\n"))
        self.assertTrue(
            workspace_git_branch_ops.git_status_has_non_runtime_changes(
                "?? .vibeagent/sessions/run/events.jsonl\n M src/app.py\n",
            )
        )


if __name__ == "__main__":
    unittest.main()
