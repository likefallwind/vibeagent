import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_approval_preview import approval_preview_summary
from vibeagent.file_line_action_executor import execute_line_file_action
from vibeagent.types import (
    AppendFileAction,
    CheckAppendFileAction,
    CheckInsertLinesAction,
    CheckReplaceLinesAction,
    InsertLinesAction,
    ReplaceLinesAction,
)
from vibeagent.workspace import create_run_workspace, write_run_file


class FileLineActionExecutorTests(unittest.TestCase):
    def test_execute_line_file_action_previews_replace_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-line-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\ntwo\n")

            observation = execute_line_file_action(
                workspace,
                CheckReplaceLinesAction(
                    type="check_replace_lines",
                    path="app.py",
                    start_line=2,
                    end_line=2,
                    content="changed\n",
                ),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_replace_lines")
            self.assertTrue(observation.ok)
            self.assertIn("Line replacement can apply", observation.message)
            self.assertEqual(observation.content, "changed\n")
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "one\ntwo\n")

            matching_preview = approval_preview_summary(
                ReplaceLinesAction(
                    type="replace_lines",
                    path="app.py",
                    start_line=2,
                    end_line=2,
                    content="changed\n",
                ),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                ReplaceLinesAction(
                    type="replace_lines",
                    path="app.py",
                    start_line=2,
                    end_line=2,
                    content="different\n",
                ),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)

    def test_execute_line_file_action_inserts_lines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-line-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\nthree\n")

            observation = execute_line_file_action(
                workspace,
                InsertLinesAction(type="insert_lines", path="app.py", line=2, content="two\n"),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "insert_lines")
            self.assertTrue(observation.ok)
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "one\ntwo\nthree\n")

    def test_line_insert_preview_matches_approval_by_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-line-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\nthree\n")

            observation = execute_line_file_action(
                workspace,
                CheckInsertLinesAction(type="check_insert_lines", path="app.py", line=2, content="two\n"),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_insert_lines")
            self.assertEqual(observation.content, "two\n")
            matching_preview = approval_preview_summary(
                InsertLinesAction(type="insert_lines", path="app.py", line=2, content="two\n"),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                InsertLinesAction(type="insert_lines", path="app.py", line=2, content="other\n"),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)

    def test_append_preview_matches_approval_by_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-line-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "notes.txt", "one\n")

            observation = execute_line_file_action(
                workspace,
                CheckAppendFileAction(type="check_append_file", path="notes.txt", content="two\n"),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_append_file")
            self.assertEqual(observation.content, "two\n")
            matching_preview = approval_preview_summary(
                AppendFileAction(type="append_file", path="notes.txt", content="two\n"),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                AppendFileAction(type="append_file", path="notes.txt", content="other\n"),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)

    def test_execute_line_file_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-line-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_line_file_action(workspace, object()))


if __name__ == "__main__":
    unittest.main()
