from __future__ import annotations

import unittest

from vibeagent import workspace_edit_ops
from vibeagent import workspace_patch_ops


class WorkspacePatchOpsTests(unittest.TestCase):
    def test_workspace_edit_ops_reexports_patch_helpers(self) -> None:
        self.assertIs(workspace_edit_ops.patch_project_file, workspace_patch_ops.patch_project_file)
        self.assertIs(workspace_edit_ops.check_project_patch, workspace_patch_ops.check_project_patch)
        self.assertIs(workspace_edit_ops.patch_project_files, workspace_patch_ops.patch_project_files)
        self.assertIs(workspace_edit_ops.check_project_patches, workspace_patch_ops.check_project_patches)
        self.assertIs(workspace_edit_ops.split_unified_patch_by_file, workspace_patch_ops.split_unified_patch_by_file)
        self.assertIs(workspace_edit_ops.is_file_header_at, workspace_patch_ops.is_file_header_at)
        self.assertIs(workspace_edit_ops.parse_unified_diff_path, workspace_patch_ops.parse_unified_diff_path)
        self.assertIs(workspace_edit_ops.apply_unified_patch, workspace_patch_ops.apply_unified_patch)
        self.assertIs(workspace_edit_ops.parse_unified_patch_hunks, workspace_patch_ops.parse_unified_patch_hunks)

    def test_patch_helpers_parse_file_sections_and_apply_hunks(self) -> None:
        patch = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n"

        self.assertEqual(workspace_patch_ops.parse_unified_diff_path("a/app.py\n"), "app.py")
        self.assertEqual(workspace_patch_ops.parse_unified_diff_path("/dev/null\n"), None)
        self.assertEqual(
            workspace_patch_ops.split_unified_patch_by_file(patch),
            [("app.py", patch, "modify")],
        )
        self.assertEqual(workspace_patch_ops.apply_unified_patch("old\n", patch), "new\n")


if __name__ == "__main__":
    unittest.main()
