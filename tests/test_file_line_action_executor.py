import tempfile
import unittest
from pathlib import Path

from vibeagent.file_line_action_executor import execute_line_file_action
from vibeagent.types import CheckReplaceLinesAction, InsertLinesAction
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
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "one\ntwo\n")

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

    def test_execute_line_file_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-line-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_line_file_action(workspace, object()))


if __name__ == "__main__":
    unittest.main()
