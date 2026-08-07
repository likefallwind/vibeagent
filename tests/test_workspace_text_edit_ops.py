import unittest

from vibeagent import workspace_edit_ops, workspace_line_edit_ops, workspace_regex_edit_ops, workspace_text_edit_ops


class WorkspaceTextEditOpsModuleTests(unittest.TestCase):
    def test_workspace_edit_ops_reexports_text_edit_helpers(self) -> None:
        self.assertIs(workspace_edit_ops.write_run_file, workspace_text_edit_ops.write_run_file)
        self.assertIs(workspace_edit_ops.preview_write_run_file, workspace_text_edit_ops.preview_write_run_file)
        self.assertIs(workspace_edit_ops.write_run_files, workspace_text_edit_ops.write_run_files)
        self.assertIs(workspace_edit_ops.preview_write_run_files, workspace_text_edit_ops.preview_write_run_files)
        self.assertIs(workspace_edit_ops.edit_project_file, workspace_text_edit_ops.edit_project_file)
        self.assertIs(workspace_edit_ops.preview_edit_project_file, workspace_text_edit_ops.preview_edit_project_file)
        self.assertIs(workspace_edit_ops.multi_edit_project_file, workspace_text_edit_ops.multi_edit_project_file)
        self.assertIs(workspace_edit_ops.preview_multi_edit_project_file, workspace_text_edit_ops.preview_multi_edit_project_file)
        self.assertIs(workspace_edit_ops.replace_project_file_lines, workspace_text_edit_ops.replace_project_file_lines)
        self.assertIs(workspace_edit_ops.preview_replace_project_file_lines, workspace_text_edit_ops.preview_replace_project_file_lines)
        self.assertIs(workspace_edit_ops.insert_project_file_lines, workspace_text_edit_ops.insert_project_file_lines)
        self.assertIs(workspace_edit_ops.preview_insert_project_file_lines, workspace_text_edit_ops.preview_insert_project_file_lines)
        self.assertIs(workspace_text_edit_ops.replace_project_file_lines, workspace_line_edit_ops.replace_project_file_lines)
        self.assertIs(workspace_text_edit_ops.preview_replace_project_file_lines, workspace_line_edit_ops.preview_replace_project_file_lines)
        self.assertIs(workspace_text_edit_ops.build_replace_lines, workspace_line_edit_ops.build_replace_lines)
        self.assertIs(workspace_text_edit_ops.insert_project_file_lines, workspace_line_edit_ops.insert_project_file_lines)
        self.assertIs(workspace_text_edit_ops.preview_insert_project_file_lines, workspace_line_edit_ops.preview_insert_project_file_lines)
        self.assertIs(workspace_text_edit_ops.build_insert_lines, workspace_line_edit_ops.build_insert_lines)
        self.assertIs(workspace_edit_ops.append_project_file, workspace_text_edit_ops.append_project_file)
        self.assertIs(workspace_edit_ops.preview_append_project_file, workspace_text_edit_ops.preview_append_project_file)
        self.assertIs(workspace_edit_ops.regex_replace_project_file, workspace_text_edit_ops.regex_replace_project_file)
        self.assertIs(workspace_edit_ops.preview_regex_replace_project_file, workspace_text_edit_ops.preview_regex_replace_project_file)
        self.assertIs(workspace_text_edit_ops.regex_replace_project_file, workspace_regex_edit_ops.regex_replace_project_file)
        self.assertIs(workspace_text_edit_ops.preview_regex_replace_project_file, workspace_regex_edit_ops.preview_regex_replace_project_file)
        self.assertIs(workspace_text_edit_ops.build_regex_replacement, workspace_regex_edit_ops.build_regex_replacement)


if __name__ == "__main__":
    unittest.main()
