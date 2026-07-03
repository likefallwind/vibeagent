import unittest

from vibeagent import workspace_git_ops, workspace_git_remote_ops


class WorkspaceGitRemoteOpsTests(unittest.TestCase):
    def test_workspace_git_ops_reexports_remote_helpers(self) -> None:
        self.assertIs(workspace_git_ops.read_git_info, workspace_git_remote_ops.read_git_info)
        self.assertIs(workspace_git_ops.preview_fetch_git_remote, workspace_git_remote_ops.preview_fetch_git_remote)
        self.assertIs(workspace_git_ops.fetch_git_remote, workspace_git_remote_ops.fetch_git_remote)
        self.assertIs(workspace_git_ops.preview_pull_git_upstream, workspace_git_remote_ops.preview_pull_git_upstream)
        self.assertIs(workspace_git_ops.pull_git_upstream, workspace_git_remote_ops.pull_git_upstream)
        self.assertIs(workspace_git_ops.preview_push_git_upstream, workspace_git_remote_ops.preview_push_git_upstream)
        self.assertIs(workspace_git_ops.push_git_upstream, workspace_git_remote_ops.push_git_upstream)
        self.assertIs(workspace_git_ops.read_git_upstream_parts, workspace_git_remote_ops.read_git_upstream_parts)
        self.assertIs(workspace_git_ops.select_git_fetch_remote, workspace_git_remote_ops.select_git_fetch_remote)


if __name__ == "__main__":
    unittest.main()
