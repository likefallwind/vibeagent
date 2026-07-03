import unittest

from vibeagent import workspace_edit_ops
from vibeagent import workspace_file_path_ops


class WorkspaceFilePathOpsTests(unittest.TestCase):
    def test_workspace_edit_ops_reexports_file_path_helpers(self) -> None:
        self.assertIs(workspace_edit_ops.delete_project_file, workspace_file_path_ops.delete_project_file)
        self.assertIs(workspace_edit_ops.preview_delete_project_file, workspace_file_path_ops.preview_delete_project_file)
        self.assertIs(workspace_edit_ops.delete_project_files, workspace_file_path_ops.delete_project_files)
        self.assertIs(workspace_edit_ops.preview_delete_project_files, workspace_file_path_ops.preview_delete_project_files)
        self.assertIs(workspace_edit_ops.build_delete_files, workspace_file_path_ops.build_delete_files)
        self.assertIs(workspace_edit_ops.build_delete_file, workspace_file_path_ops.build_delete_file)
        self.assertIs(workspace_edit_ops.move_project_file, workspace_file_path_ops.move_project_file)
        self.assertIs(workspace_edit_ops.preview_move_project_file, workspace_file_path_ops.preview_move_project_file)
        self.assertIs(workspace_edit_ops.move_project_files, workspace_file_path_ops.move_project_files)
        self.assertIs(workspace_edit_ops.preview_move_project_files, workspace_file_path_ops.preview_move_project_files)
        self.assertIs(workspace_edit_ops.prepare_project_file_transfers, workspace_file_path_ops.prepare_project_file_transfers)
        self.assertIs(workspace_edit_ops.copy_project_file, workspace_file_path_ops.copy_project_file)
        self.assertIs(workspace_edit_ops.preview_copy_project_file, workspace_file_path_ops.preview_copy_project_file)
        self.assertIs(workspace_edit_ops.copy_project_files, workspace_file_path_ops.copy_project_files)
        self.assertIs(workspace_edit_ops.preview_copy_project_files, workspace_file_path_ops.preview_copy_project_files)
        self.assertIs(workspace_edit_ops.prepare_project_file_copies, workspace_file_path_ops.prepare_project_file_copies)
        self.assertIs(workspace_edit_ops.prepare_project_file_transfer, workspace_file_path_ops.prepare_project_file_transfer)


if __name__ == "__main__":
    unittest.main()
