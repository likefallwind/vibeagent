import stat
import tempfile
import unittest
from pathlib import Path

from vibeagent.file_directory_action_executor import execute_directory_file_action
from vibeagent.file_directory_copy_action_executor import execute_directory_copy_action
from vibeagent.file_directory_move_action_executor import execute_directory_move_action
from vibeagent.file_executable_action_executor import execute_executable_file_action
from vibeagent.types import CheckSetExecutableAction, SetExecutableAction
from vibeagent.workspace import create_run_workspace


class FileExecutableActionExecutorTests(unittest.TestCase):
    def test_execute_executable_file_action_previews_and_applies_mode_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-executable-executor-") as base:
            root = Path(base)
            script = root / "tool.sh"
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o644)
            workspace = create_run_workspace(root, "test-run")

            preview = execute_executable_file_action(
                workspace,
                CheckSetExecutableAction(type="check_set_executable", path="tool.sh", executable=True),
            )
            applied = execute_executable_file_action(
                workspace,
                SetExecutableAction(type="set_executable", path="tool.sh", executable=True),
            )
            executable = bool(script.stat().st_mode & stat.S_IXUSR)

        self.assertIsNotNone(preview)
        self.assertEqual(preview.kind, "check_set_executable")
        self.assertTrue(preview.ok)
        self.assertEqual(preview.mode_before, "0644")
        self.assertEqual(preview.mode_after, "0755")
        self.assertIsNotNone(applied)
        self.assertEqual(applied.kind, "set_executable")
        self.assertTrue(applied.ok)
        self.assertTrue(executable)

    def test_directory_file_executor_delegates_executable_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-executable-executor-") as base:
            root = Path(base)
            (root / "tool.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            workspace = create_run_workspace(root, "test-run")

            observation = execute_directory_file_action(
                workspace,
                CheckSetExecutableAction(type="check_set_executable", path="tool.sh", executable=True),
            )

        self.assertIsNotNone(observation)
        self.assertEqual(observation.kind, "check_set_executable")

    def test_execute_executable_file_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-executable-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_executable_file_action(workspace, object()))

    def test_execute_directory_move_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-directory-move-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_directory_move_action(workspace, object()))

    def test_execute_directory_copy_action_returns_none_for_unhandled_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-directory-copy-executor-") as base:
            workspace = create_run_workspace(base, "test-run")

            self.assertIsNone(execute_directory_copy_action(workspace, object()))


if __name__ == "__main__":
    unittest.main()
