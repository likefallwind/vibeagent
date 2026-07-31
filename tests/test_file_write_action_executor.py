import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_approval_preview import approval_preview_summary
from vibeagent.agent_tool_results import build_tool_result_payload
from vibeagent.file_write_action_executor import execute_write_file_action
from vibeagent.types import CheckWriteFileAction, CheckWriteFilesAction, WriteFileAction, WriteFileItem, WriteFilesAction
from vibeagent.workspace import create_run_workspace


class FileWriteActionExecutorTests(unittest.TestCase):
    def test_execute_write_file_action_previews_single_file_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-write-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            observation = execute_write_file_action(
                workspace,
                CheckWriteFileAction(type="check_write_file", path="note.txt", content="hello\n"),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_write_file")
            self.assertTrue(observation.ok)
            self.assertIn("Write can apply", observation.message)
            self.assertEqual(observation.content, "hello\n")
            self.assertFalse(Path(base, "note.txt").exists())

            matching_preview = approval_preview_summary(
                WriteFileAction(type="write_file", path="note.txt", content="hello\n"),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                WriteFileAction(type="write_file", path="note.txt", content="different\n"),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)

    def test_execute_write_file_action_writes_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-write-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            observation = execute_write_file_action(
                workspace,
                WriteFilesAction(
                    type="write_files",
                    files=[
                        WriteFileItem(path="pkg/a.py", content="A = 1\n"),
                        WriteFileItem(path="pkg/b.py", content="B = 2\n"),
                    ],
                ),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "write_files")
            self.assertTrue(observation.ok)
            self.assertEqual(Path(base, "pkg", "a.py").read_text(encoding="utf-8"), "A = 1\n")
            self.assertEqual(Path(base, "pkg", "b.py").read_text(encoding="utf-8"), "B = 2\n")

    def test_write_files_preview_matches_approval_by_file_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-write-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            files = [
                WriteFileItem(path="pkg/a.py", content="A = 1\n"),
                WriteFileItem(path="pkg/b.py", content="B = 2\n"),
            ]

            observation = execute_write_file_action(
                workspace,
                CheckWriteFilesAction(type="check_write_files", files=files),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_write_files")
            self.assertEqual(observation.inputs, files)
            matching_preview = approval_preview_summary(
                WriteFilesAction(type="write_files", files=files),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                WriteFilesAction(
                    type="write_files",
                    files=[
                        WriteFileItem(path="pkg/a.py", content="A = 1\n"),
                        WriteFileItem(path="pkg/b.py", content="B = 3\n"),
                    ],
                ),
                [observation],
            )

            self.assertIn("fileDiffs=", matching_preview or "")
            self.assertIsNone(mismatched_preview)
            self.assertNotIn("inputs", build_tool_result_payload(observation))

    def test_execute_write_file_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-write-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_write_file_action(workspace, object()))


if __name__ == "__main__":
    unittest.main()
