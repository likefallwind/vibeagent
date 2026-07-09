from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_commands, git_commit_commands


class GitCommitCommandsTests(unittest.TestCase):
    def test_git_commands_keeps_commit_exports(self) -> None:
        self.assertIs(git_commands.get_check_commit_report, git_commit_commands.get_check_commit_report)
        self.assertIs(git_commands.get_check_commit_text, git_commit_commands.get_check_commit_text)
        self.assertIs(git_commands.get_commit_report, git_commit_commands.get_commit_report)
        self.assertIs(git_commands.get_commit_text, git_commit_commands.get_commit_text)

    def test_commit_reports_usage_for_missing_message(self) -> None:
        root = Path("/tmp/vibeagent-git-commit").resolve()

        check_report = git_commit_commands.get_check_commit_report(root)
        commit_report = git_commit_commands.get_commit_report(root, " ")

        self.assertFalse(check_report["ok"])
        self.assertIn("Usage: /check-commit <message>", check_report["message"])
        self.assertFalse(commit_report["ok"])
        self.assertIn("Usage: /commit <message>", commit_report["message"])

    def test_check_commit_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_commit",
            ok=True,
            head_before="abc1234",
            head_after="abc1234",
            status="M  app.py",
            message="Commit can be created.",
        )
        root = Path("/tmp/vibeagent-git-commit").resolve()

        with patch("vibeagent.git_commit_commands._execute_action", return_value=observation) as execute_action:
            report = git_commit_commands.get_check_commit_report(root, "update app")
            text = git_commit_commands.get_check_commit_text(root, "update app")

        self.assertTrue(report["ok"])
        self.assertEqual(report["headBefore"], "abc1234")
        self.assertEqual(report["headAfter"], "abc1234")
        self.assertEqual(report["statusText"], "M  app.py")
        self.assertIn("Check commit:", text)
        self.assertIn("headBefore: abc1234", text)
        execute_action.assert_called()

    def test_commit_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="git_commit",
            ok=True,
            head_before="abc1234",
            head_after="def5678",
            status="",
            message="Committed changes.",
        )
        root = Path("/tmp/vibeagent-git-commit").resolve()

        with patch("vibeagent.git_commit_commands._execute_action", return_value=observation) as execute_action:
            report = git_commit_commands.get_commit_report(root, "update app")
            text = git_commit_commands.get_commit_text(root, "update app")

        self.assertTrue(report["ok"])
        self.assertEqual(report["headBefore"], "abc1234")
        self.assertEqual(report["headAfter"], "def5678")
        self.assertEqual(report["statusText"], "")
        self.assertIn("Commit:", text)
        self.assertIn("status: none", text)
        execute_action.assert_called()


if __name__ == "__main__":
    unittest.main()
