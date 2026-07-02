import unittest

from vibeagent import workspace_git_ops, workspace_git_stash_ops


class WorkspaceGitStashOpsTests(unittest.TestCase):
    def test_workspace_git_ops_reexports_stash_helpers(self) -> None:
        self.assertIs(workspace_git_ops.read_git_stashes, workspace_git_stash_ops.read_git_stashes)
        self.assertIs(workspace_git_ops.preview_stash_git_changes, workspace_git_stash_ops.preview_stash_git_changes)
        self.assertIs(workspace_git_ops.stash_git_changes, workspace_git_stash_ops.stash_git_changes)
        self.assertIs(workspace_git_ops.preview_apply_git_stash, workspace_git_stash_ops.preview_apply_git_stash)
        self.assertIs(workspace_git_ops.apply_git_stash, workspace_git_stash_ops.apply_git_stash)
        self.assertIs(workspace_git_ops.preview_drop_git_stash, workspace_git_stash_ops.preview_drop_git_stash)
        self.assertIs(workspace_git_ops.drop_git_stash, workspace_git_stash_ops.drop_git_stash)
        self.assertIs(workspace_git_ops.parse_git_stash_list, workspace_git_stash_ops.parse_git_stash_list)
        self.assertIs(workspace_git_ops.validate_git_stash_ref, workspace_git_stash_ops.validate_git_stash_ref)
        self.assertIs(workspace_git_ops.git_stash_candidate_paths, workspace_git_stash_ops.git_stash_candidate_paths)


if __name__ == "__main__":
    unittest.main()
