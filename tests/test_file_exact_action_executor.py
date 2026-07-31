import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_approval_preview import approval_preview_summary
from vibeagent.file_exact_action_executor import execute_exact_file_action
from vibeagent.types import CheckEditFileAction, CheckMultiEditAction, EditFileAction, EditOperation, MultiEditAction
from vibeagent.workspace import create_run_workspace, write_run_file


class FileExactActionExecutorTests(unittest.TestCase):
    def test_execute_exact_file_action_previews_edit_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-exact-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "old\n")

            observation = execute_exact_file_action(
                workspace,
                CheckEditFileAction(type="check_edit_file", path="app.py", old="old", new="new"),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_edit_file")
            self.assertTrue(observation.ok)
            self.assertIn("Edit can apply", observation.message)
            self.assertEqual(observation.old, "old")
            self.assertEqual(observation.new, "new")
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "old\n")

            matching_preview = approval_preview_summary(
                EditFileAction(type="edit_file", path="app.py", old="old", new="new"),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                EditFileAction(type="edit_file", path="app.py", old="old", new="different"),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)

    def test_execute_exact_file_action_applies_multi_edit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-exact-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "old\nagain\n")

            observation = execute_exact_file_action(
                workspace,
                MultiEditAction(
                    type="multi_edit_file",
                    path="app.py",
                    edits=[
                        EditOperation(old="old", new="new"),
                        EditOperation(old="again", new="done"),
                    ],
                ),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "multi_edit_file")
            self.assertTrue(observation.ok)
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "new\ndone\n")

    def test_exact_multi_edit_preview_matches_approval_by_edit_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-exact-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "old\nagain\n")
            edits = [EditOperation(old="old", new="new"), EditOperation(old="again", new="done")]

            observation = execute_exact_file_action(
                workspace,
                CheckMultiEditAction(type="check_multi_edit_file", path="app.py", edits=edits),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_multi_edit_file")
            self.assertEqual(observation.edits, edits)
            matching_preview = approval_preview_summary(
                MultiEditAction(type="multi_edit_file", path="app.py", edits=edits),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                MultiEditAction(
                    type="multi_edit_file",
                    path="app.py",
                    edits=[EditOperation(old="old", new="other"), EditOperation(old="again", new="done")],
                ),
                [observation],
            )

        self.assertIn("diffChars=", matching_preview or "")
        self.assertIsNone(mismatched_preview)

    def test_execute_exact_file_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-exact-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_exact_file_action(workspace, object()))


if __name__ == "__main__":
    unittest.main()
