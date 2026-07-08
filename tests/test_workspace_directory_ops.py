import unittest

from vibeagent import workspace_directory_ops, workspace_edit_ops


class WorkspaceDirectoryOpsTests(unittest.TestCase):
    def test_workspace_edit_ops_reexports_directory_helpers(self) -> None:
        self.assertIs(workspace_edit_ops.move_project_directory, workspace_directory_ops.move_project_directory)
        self.assertIs(workspace_edit_ops.preview_move_project_directory, workspace_directory_ops.preview_move_project_directory)
        self.assertIs(workspace_edit_ops.move_project_directories, workspace_directory_ops.move_project_directories)
        self.assertIs(workspace_edit_ops.preview_move_project_directories, workspace_directory_ops.preview_move_project_directories)
        self.assertIs(workspace_edit_ops.prepare_project_directory_move, workspace_directory_ops.prepare_project_directory_move)
        self.assertIs(workspace_edit_ops.copy_project_directory, workspace_directory_ops.copy_project_directory)
        self.assertIs(workspace_edit_ops.preview_copy_project_directory, workspace_directory_ops.preview_copy_project_directory)
        self.assertIs(workspace_edit_ops.copy_project_directories, workspace_directory_ops.copy_project_directories)
        self.assertIs(workspace_edit_ops.preview_copy_project_directories, workspace_directory_ops.preview_copy_project_directories)
        self.assertIs(workspace_edit_ops.prepare_project_directory_copy, workspace_directory_ops.prepare_project_directory_copy)
        self.assertIs(
            workspace_edit_ops.validate_project_directory_transfer_batch,
            workspace_directory_ops.validate_project_directory_transfer_batch,
        )
        self.assertIs(workspace_edit_ops.create_project_directory, workspace_directory_ops.create_project_directory)
        self.assertIs(workspace_edit_ops.preview_create_project_directory, workspace_directory_ops.preview_create_project_directory)
        self.assertIs(workspace_edit_ops.create_project_directories, workspace_directory_ops.create_project_directories)
        self.assertIs(workspace_edit_ops.preview_create_project_directories, workspace_directory_ops.preview_create_project_directories)
        self.assertIs(workspace_edit_ops.delete_project_empty_directory, workspace_directory_ops.delete_project_empty_directory)
        self.assertIs(
            workspace_edit_ops.preview_delete_project_empty_directory,
            workspace_directory_ops.preview_delete_project_empty_directory,
        )
        self.assertIs(workspace_edit_ops.delete_project_empty_directories, workspace_directory_ops.delete_project_empty_directories)
        self.assertIs(
            workspace_edit_ops.preview_delete_project_empty_directories,
            workspace_directory_ops.preview_delete_project_empty_directories,
        )


if __name__ == "__main__":
    unittest.main()
