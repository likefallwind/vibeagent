from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_commands, git_index_commands


class GitIndexCommandsTests(unittest.TestCase):
    def test_git_commands_keeps_index_exports(self) -> None:
        self.assertIs(git_commands.get_check_stage_report, git_index_commands.get_check_stage_report)
        self.assertIs(git_commands.get_check_stage_text, git_index_commands.get_check_stage_text)
        self.assertIs(git_commands.get_stage_report, git_index_commands.get_stage_report)
        self.assertIs(git_commands.get_stage_text, git_index_commands.get_stage_text)
        self.assertIs(git_commands.get_check_unstage_report, git_index_commands.get_check_unstage_report)
        self.assertIs(git_commands.get_check_unstage_text, git_index_commands.get_check_unstage_text)
        self.assertIs(git_commands.get_unstage_report, git_index_commands.get_unstage_report)
        self.assertIs(git_commands.get_unstage_text, git_index_commands.get_unstage_text)

    def test_stage_reports_usage_for_missing_paths(self) -> None:
        root = Path("/tmp/vibeagent-git-index").resolve()

        check_report = git_index_commands.get_check_stage_report(root)
        stage_report = git_index_commands.get_stage_report(root, [])

        self.assertFalse(check_report["ok"])
        self.assertIn("Usage: /check-stage <path...>", check_report["message"])
        self.assertFalse(stage_report["ok"])
        self.assertIn("Usage: /stage <path...>", stage_report["message"])

    def test_stage_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="git_stage",
            ok=True,
            paths=["app.py", "tests/test_app.py"],
            status="M  app.py",
            message="Staged 2 path(s).",
        )
        root = Path("/tmp/vibeagent-git-index").resolve()

        with patch("vibeagent.git_index_commands._execute_action", return_value=observation) as execute_action:
            report = git_index_commands.get_stage_report(root, ["app.py", "tests/test_app.py"])
            text = git_index_commands.get_stage_text(root, ["app.py", "tests/test_app.py"])

        self.assertTrue(report["ok"])
        self.assertEqual(report["paths"]["shown"], 2)
        self.assertEqual(report["paths"]["items"], ["app.py", "tests/test_app.py"])
        self.assertEqual(report["statusText"], "M  app.py")
        self.assertIn("Stage:", text)
        self.assertIn("paths: 2", text)
        execute_action.assert_called()

    def test_unstage_report_serializes_observation_and_usage(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_unstage",
            ok=True,
            paths=["app.py"],
            status="MM app.py",
            message="Path can be unstaged.",
        )
        root = Path("/tmp/vibeagent-git-index").resolve()

        with patch("vibeagent.git_index_commands._execute_action", return_value=observation) as execute_action:
            report = git_index_commands.get_check_unstage_report(root, "app.py")
            text = git_index_commands.get_check_unstage_text(root, "app.py")
            usage = git_index_commands.get_unstage_report(root)

        self.assertTrue(report["ok"])
        self.assertEqual(report["paths"]["items"], ["app.py"])
        self.assertEqual(report["statusText"], "MM app.py")
        self.assertIn("Check unstage:", text)
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /unstage <path...>", usage["message"])
        execute_action.assert_called()


if __name__ == "__main__":
    unittest.main()
