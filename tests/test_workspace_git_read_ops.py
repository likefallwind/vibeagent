import unittest

from vibeagent import workspace_git_ops
from vibeagent import workspace_git_read_ops


class WorkspaceGitReadOpsTests(unittest.TestCase):
    def test_workspace_git_ops_reexports_read_helpers(self) -> None:
        self.assertIs(workspace_git_ops.read_git_diff, workspace_git_read_ops.read_git_diff)
        self.assertIs(workspace_git_ops.read_git_diff_hunks, workspace_git_read_ops.read_git_diff_hunks)
        self.assertIs(workspace_git_ops.parse_git_diff_hunks, workspace_git_read_ops.parse_git_diff_hunks)
        self.assertIs(workspace_git_ops.parse_git_diff_file_path, workspace_git_read_ops.parse_git_diff_file_path)
        self.assertIs(workspace_git_ops.read_git_log, workspace_git_read_ops.read_git_log)
        self.assertIs(workspace_git_ops.read_git_show, workspace_git_read_ops.read_git_show)
        self.assertIs(workspace_git_ops.read_git_blame, workspace_git_read_ops.read_git_blame)


if __name__ == "__main__":
    unittest.main()
