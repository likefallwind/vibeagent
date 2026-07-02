import tempfile
import unittest
from pathlib import Path

from vibeagent import workspace_edit_ops, workspace_json_edit_ops
from vibeagent.workspace_core import create_run_workspace


class WorkspaceJsonEditOpsTests(unittest.TestCase):
    def test_workspace_edit_ops_reexports_json_helpers(self) -> None:
        self.assertIs(workspace_edit_ops.json_set_project_file, workspace_json_edit_ops.json_set_project_file)
        self.assertIs(workspace_edit_ops.preview_json_set_project_file, workspace_json_edit_ops.preview_json_set_project_file)
        self.assertIs(workspace_edit_ops.json_remove_project_file, workspace_json_edit_ops.json_remove_project_file)
        self.assertIs(workspace_edit_ops.preview_json_remove_project_file, workspace_json_edit_ops.preview_json_remove_project_file)
        self.assertIs(workspace_edit_ops.json_patch_project_file, workspace_json_edit_ops.json_patch_project_file)
        self.assertIs(workspace_edit_ops.preview_json_patch_project_file, workspace_json_edit_ops.preview_json_patch_project_file)
        self.assertIs(workspace_edit_ops.build_json_set, workspace_json_edit_ops.build_json_set)
        self.assertIs(workspace_edit_ops.build_json_remove, workspace_json_edit_ops.build_json_remove)
        self.assertIs(workspace_edit_ops.build_json_patch, workspace_json_edit_ops.build_json_patch)
        self.assertIs(workspace_edit_ops.parse_json_pointer, workspace_json_edit_ops.parse_json_pointer)
        self.assertIs(workspace_edit_ops.parse_json_array_index, workspace_json_edit_ops.parse_json_array_index)

    def test_json_helpers_preview_and_apply_file_edits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-json-edit-") as base:
            workspace = create_run_workspace(base, "test-run")
            target = Path(base) / "package.json"
            target.write_text('{"scripts":{"test":"old"},"keywords":["one"]}\n', encoding="utf-8")

            preview_target, preview_diff = workspace_json_edit_ops.preview_json_set_project_file(
                workspace,
                "package.json",
                "/scripts/test",
                "python -m unittest",
            )
            set_target, set_diff = workspace_json_edit_ops.json_set_project_file(
                workspace,
                "package.json",
                "/scripts/test",
                "python -m unittest",
            )
            patch_target, patch_diff = workspace_json_edit_ops.json_patch_project_file(
                workspace,
                "package.json",
                [{"op": "add", "path": "/keywords/-", "value": "two"}],
            )
            remove_target, remove_diff = workspace_json_edit_ops.json_remove_project_file(
                workspace,
                "package.json",
                "/keywords/0",
            )

            self.assertEqual(preview_target, target)
            self.assertEqual(set_target, target)
            self.assertEqual(patch_target, target)
            self.assertEqual(remove_target, target)
            self.assertIn("+    \"test\": \"python -m unittest\"", preview_diff)
            self.assertIn("+    \"test\": \"python -m unittest\"", set_diff)
            self.assertIn("+    \"two\"", patch_diff)
            self.assertIn("-    \"one\",", remove_diff)
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{\n  "scripts": {\n    "test": "python -m unittest"\n  },\n  "keywords": [\n    "two"\n  ]\n}\n',
            )

    def test_json_pointer_helpers_validate_paths(self) -> None:
        document = {"items": [{"name": "old"}]}

        self.assertEqual(workspace_json_edit_ops.parse_json_pointer("/items/0/name"), ["items", "0", "name"])
        workspace_json_edit_ops.set_json_pointer_value(document, "/items/0/name", "new")
        workspace_json_edit_ops.add_json_pointer_value(document, "/items/-", {"name": "extra"})

        self.assertEqual(document, {"items": [{"name": "new"}, {"name": "extra"}]})
        with self.assertRaisesRegex(ValueError, "JSON pointer must start"):
            workspace_json_edit_ops.parse_json_pointer("items/0")
        with self.assertRaisesRegex(ValueError, "out of range"):
            workspace_json_edit_ops.parse_json_array_index("2", 1, allow_append=False)


if __name__ == "__main__":
    unittest.main()
