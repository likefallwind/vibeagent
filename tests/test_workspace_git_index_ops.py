import unittest

from vibeagent import workspace_git_index_ops, workspace_git_ops


class WorkspaceGitIndexOpsTests(unittest.TestCase):
    def test_workspace_git_ops_reexports_index_helpers(self) -> None:
        self.assertIs(workspace_git_ops.stage_git_paths, workspace_git_index_ops.stage_git_paths)
        self.assertIs(workspace_git_ops.preview_stage_git_paths, workspace_git_index_ops.preview_stage_git_paths)
        self.assertIs(workspace_git_ops.unstage_git_paths, workspace_git_index_ops.unstage_git_paths)
        self.assertIs(workspace_git_ops.preview_unstage_git_paths, workspace_git_index_ops.preview_unstage_git_paths)
        self.assertIs(workspace_git_ops.preview_restore_git_paths, workspace_git_index_ops.preview_restore_git_paths)
        self.assertIs(workspace_git_ops.restore_git_paths, workspace_git_index_ops.restore_git_paths)
        self.assertIs(workspace_git_ops.validate_git_tracked_paths, workspace_git_index_ops.validate_git_tracked_paths)
        self.assertIs(workspace_git_ops.commit_staged_changes, workspace_git_index_ops.commit_staged_changes)
        self.assertIs(
            workspace_git_ops.preview_commit_staged_changes,
            workspace_git_index_ops.preview_commit_staged_changes,
        )
        self.assertIs(workspace_git_ops.preview_switch_git_branch, workspace_git_index_ops.preview_switch_git_branch)
        self.assertIs(workspace_git_ops.switch_git_branch, workspace_git_index_ops.switch_git_branch)


if __name__ == "__main__":
    unittest.main()
