from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_commands, git_restore_commands


class GitRestoreCommandsTests(unittest.TestCase):
    def test_git_commands_keeps_restore_exports(self) -> None:
        self.assertIs(git_commands.get_check_restore_report, git_restore_commands.get_check_restore_report)
        self.assertIs(git_commands.get_check_restore_text, git_restore_commands.get_check_restore_text)
        self.assertIs(git_commands.get_restore_report, git_restore_commands.get_restore_report)
        self.assertIs(git_commands.get_restore_text, git_restore_commands.get_restore_text)

    def test_restore_reports_usage_for_missing_paths_and_validates_max_chars(self) -> None:
        root = Path("/tmp/vibeagent-git-restore").resolve()

        check_report = git_restore_commands.get_check_restore_report(root)
        restore_report = git_restore_commands.get_restore_report(root, [])

        self.assertFalse(check_report["ok"])
        self.assertIn("Usage: /check-restore <path...>", check_report["message"])
        self.assertFalse(restore_report["ok"])
        self.assertIn("Usage: /restore <path...>", restore_report["message"])
        with self.assertRaisesRegex(ValueError, "at least 100"):
            git_restore_commands.get_restore_report(root, "app.py", max_diff_chars=99)

    def test_check_restore_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_restore",
            ok=True,
            paths=["app.py"],
            diff="+new\n",
            status=" M app.py",
            message="Path can be restored.",
        )
        root = Path("/tmp/vibeagent-git-restore").resolve()

        with patch("vibeagent.git_restore_commands._execute_action", return_value=observation) as execute_action:
            report = git_restore_commands.get_check_restore_report(root, "app.py")
            text = git_restore_commands.get_check_restore_text(root, "app.py")

        self.assertTrue(report["ok"])
        self.assertEqual(report["paths"]["items"], ["app.py"])
        self.assertEqual(report["diff"]["chars"], 5)
        self.assertEqual(report["statusText"], " M app.py")
        self.assertIn("Check restore:", text)
        self.assertIn("diffChars: 5", text)
        execute_action.assert_called()

    def test_restore_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="git_restore",
            ok=True,
            paths=["app.py", "tests/test_app.py"],
            diff="+new\n",
            status="",
            message="Restored 2 path(s).",
        )
        root = Path("/tmp/vibeagent-git-restore").resolve()

        with patch("vibeagent.git_restore_commands._execute_action", return_value=observation) as execute_action:
            report = git_restore_commands.get_restore_report(root, ["app.py", "tests/test_app.py"])
            text = git_restore_commands.get_restore_text(root, ["app.py", "tests/test_app.py"])

        self.assertTrue(report["ok"])
        self.assertEqual(report["paths"]["shown"], 2)
        self.assertEqual(report["diff"]["text"], "+new\n")
        self.assertEqual(report["statusText"], "")
        self.assertIn("Restore:", text)
        self.assertIn("status: none", text)
        execute_action.assert_called()


if __name__ == "__main__":
    unittest.main()
