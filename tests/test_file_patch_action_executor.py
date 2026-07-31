import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_approval_preview import approval_preview_summary
from vibeagent.file_patch_action_executor import execute_patch_file_action
from vibeagent.types import CheckPatchAction, CheckPatchesAction, CheckRegexReplaceAction, PatchFileAction, PatchFilesAction, RegexReplaceAction
from vibeagent.workspace import create_run_workspace, write_run_file


class FilePatchActionExecutorTests(unittest.TestCase):
    def test_execute_patch_file_action_previews_regex_replace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-patch-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "value = 'old'\n")

            observation = execute_patch_file_action(
                workspace,
                CheckRegexReplaceAction(
                    type="check_regex_replace",
                    path="app.py",
                    pattern="old",
                    replacement="new",
                ),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_regex_replace")
            self.assertTrue(observation.ok)
            self.assertEqual(observation.replacements, 1)
            self.assertEqual(observation.replacement, "new")
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "value = 'old'\n")

            matching_preview = approval_preview_summary(
                RegexReplaceAction(type="regex_replace", path="app.py", pattern="old", replacement="new"),
                [observation],
            )
            mismatched_replacement_preview = approval_preview_summary(
                RegexReplaceAction(type="regex_replace", path="app.py", pattern="old", replacement="different"),
                [observation],
            )
            mismatched_flag_preview = approval_preview_summary(
                RegexReplaceAction(
                    type="regex_replace",
                    path="app.py",
                    pattern="old",
                    replacement="new",
                    case_sensitive=False,
                ),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_replacement_preview)
            self.assertIsNone(mismatched_flag_preview)

    def test_execute_patch_file_action_applies_single_file_patch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-patch-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "old\n")

            observation = execute_patch_file_action(
                workspace,
                PatchFileAction(type="patch_file", path="app.py", patch="@@ -1 +1 @@\n-old\n+new\n"),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "patch_file")
            self.assertTrue(observation.ok)
            self.assertIn("Patched app.py", observation.message)
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "new\n")

    def test_patch_file_preview_matches_approval_by_patch_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-patch-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "old\n")
            patch = "@@ -1 +1 @@\n-old\n+new\n"

            observation = execute_patch_file_action(
                workspace,
                CheckPatchAction(type="check_patch", path="app.py", patch=patch),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_patch")
            self.assertTrue(observation.ok)
            self.assertEqual(observation.patch, patch)
            matching_preview = approval_preview_summary(
                PatchFileAction(type="patch_file", path="app.py", patch=patch),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                PatchFileAction(type="patch_file", path="app.py", patch="@@ -1 +1 @@\n-old\n+other\n"),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)

    def test_patch_files_preview_matches_approval_by_patch_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-patch-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "a.txt", "old a\n")
            write_run_file(workspace, "b.txt", "old b\n")
            patch = (
                "--- a/a.txt\n"
                "+++ b/a.txt\n"
                "@@ -1 +1 @@\n"
                "-old a\n"
                "+new a\n"
                "--- a/b.txt\n"
                "+++ b/b.txt\n"
                "@@ -1 +1 @@\n"
                "-old b\n"
                "+new b\n"
            )

            observation = execute_patch_file_action(
                workspace,
                CheckPatchesAction(type="check_patches", patch=patch),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_patches")
            self.assertTrue(observation.ok)
            self.assertEqual(observation.patch, patch)
            matching_preview = approval_preview_summary(
                PatchFilesAction(type="patch_files", patch=patch),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                PatchFilesAction(type="patch_files", patch=patch.replace("new b", "other b")),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)

    def test_execute_patch_file_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-patch-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_patch_file_action(workspace, object()))


if __name__ == "__main__":
    unittest.main()
