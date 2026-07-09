from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_commands, git_switch_commands


class GitSwitchCommandsTests(unittest.TestCase):
    def test_git_commands_keeps_switch_exports(self) -> None:
        self.assertIs(git_commands.get_check_switch_report, git_switch_commands.get_check_switch_report)
        self.assertIs(git_commands.get_check_switch_text, git_switch_commands.get_check_switch_text)
        self.assertIs(git_commands.get_switch_report, git_switch_commands.get_switch_report)
        self.assertIs(git_commands.get_switch_text, git_switch_commands.get_switch_text)
        self.assertIs(git_commands.parse_switch_argument, git_switch_commands.parse_switch_argument)

    def test_parse_switch_argument_validates_branch_and_create_flag(self) -> None:
        self.assertEqual(git_switch_commands.parse_switch_argument("main"), ("main", False))
        self.assertEqual(git_switch_commands.parse_switch_argument("--create feature/demo"), ("feature/demo", True))
        self.assertEqual(git_switch_commands.parse_switch_argument("-c 'feature/demo'"), ("feature/demo", True))
        with self.assertRaisesRegex(ValueError, "branch is required"):
            git_switch_commands.parse_switch_argument(None)
        with self.assertRaisesRegex(ValueError, "unsupported option"):
            git_switch_commands.parse_switch_argument("--bad main")
        with self.assertRaisesRegex(ValueError, "only one branch"):
            git_switch_commands.parse_switch_argument("main feature")

    def test_check_switch_report_serializes_observation_and_usage(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_switch",
            ok=True,
            branch="feature/demo",
            create=True,
            current_before="main",
            branch_exists=False,
            worktree_clean=True,
            status="",
            message="Branch can be created.",
        )
        root = Path("/tmp/vibeagent-git-switch").resolve()

        with patch("vibeagent.git_switch_commands._execute_action", return_value=observation) as execute_action:
            report = git_switch_commands.get_check_switch_report(root, "--create feature/demo")
            text = git_switch_commands.get_check_switch_text(root, "--create feature/demo")
            usage = git_switch_commands.get_check_switch_report(root)

        self.assertTrue(report["ok"])
        self.assertEqual(report["branch"], "feature/demo")
        self.assertTrue(report["create"])
        self.assertFalse(report["branchExists"])
        self.assertTrue(report["worktreeClean"])
        self.assertIn("Check switch:", text)
        self.assertIn("branchExists: no", text)
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /check-switch [--create] <branch>", usage["message"])
        execute_action.assert_called()

    def test_switch_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="git_switch",
            ok=True,
            branch="feature/demo",
            create=False,
            current_before="main",
            current_after="feature/demo",
            status="",
            message="Switched branch.",
        )
        root = Path("/tmp/vibeagent-git-switch").resolve()

        with patch("vibeagent.git_switch_commands._execute_action", return_value=observation) as execute_action:
            report = git_switch_commands.get_switch_report(root, "feature/demo")
            text = git_switch_commands.get_switch_text(root, "feature/demo")

        self.assertTrue(report["ok"])
        self.assertEqual(report["branch"], "feature/demo")
        self.assertEqual(report["currentBefore"], "main")
        self.assertEqual(report["currentAfter"], "feature/demo")
        self.assertIn("Switch:", text)
        self.assertIn("currentAfter: feature/demo", text)
        execute_action.assert_called()


if __name__ == "__main__":
    unittest.main()
