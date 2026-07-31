from __future__ import annotations

import unittest
from types import SimpleNamespace

import vibeagent.agent_approval_preview_path_state as path_state


class ApprovalPreviewPathStateTests(unittest.TestCase):
    def test_observation_paths_collects_direct_items_and_transfers(self) -> None:
        observation = SimpleNamespace(
            path="app.py",
            definition_path="pkg/core.py",
            paths=["docs/a.md"],
            files=[SimpleNamespace(path="src/item.py")],
            inputs=[SimpleNamespace(path="generated.txt")],
            source="old.py",
            destination="new.py",
            transfers=[SimpleNamespace(source="src/a.py", destination="src/b.py")],
        )

        self.assertEqual(
            path_state.observation_paths(observation),
            frozenset(
                {
                    "app.py",
                    "pkg/core.py",
                    "docs/a.md",
                    "src/item.py",
                    "generated.txt",
                    "old.py",
                    "new.py",
                    "src/a.py",
                    "src/b.py",
                }
            ),
        )

    def test_approval_preview_paths_treats_patch_files_as_workspace_wide(self) -> None:
        action = SimpleNamespace(type="patch_files", patch="diff --git a/app.py b/app.py\n")
        preview = SimpleNamespace(kind="check_patches", patch="diff --git a/app.py b/app.py\n")

        self.assertIsNone(path_state.approval_preview_paths(action))
        self.assertIsNone(path_state.approval_preview_paths(preview))

    def test_file_preview_invalidated_by_same_or_nested_file_mutation(self) -> None:
        same_path = path_state.file_preview_invalidated_by_file_mutation(
            "check_edit_file",
            "write_file",
            frozenset({"src/app.py"}),
            SimpleNamespace(kind="write_file", path="./src/app.py"),
        )
        nested_path = path_state.file_preview_invalidated_by_file_mutation(
            "check_edit_file",
            "write_file",
            frozenset({"src"}),
            SimpleNamespace(kind="write_file", path="src/app.py"),
        )
        unrelated_path = path_state.file_preview_invalidated_by_file_mutation(
            "check_edit_file",
            "write_file",
            frozenset({"src/app.py"}),
            SimpleNamespace(kind="write_file", path="docs/readme.md"),
        )

        self.assertTrue(same_path)
        self.assertTrue(nested_path)
        self.assertFalse(unrelated_path)

    def test_preview_search_uses_path_specific_file_invalidations(self) -> None:
        self.assertTrue(
            path_state.preview_search_invalidated(
                "check_edit_file",
                "write_file",
                frozenset({"src/app.py"}),
                SimpleNamespace(kind="write_file", path="src/app.py"),
            )
        )
        self.assertFalse(
            path_state.preview_search_invalidated(
                "check_edit_file",
                "write_file",
                frozenset({"src/app.py"}),
                SimpleNamespace(kind="write_file", path="docs/readme.md"),
            )
        )


if __name__ == "__main__":
    unittest.main()
