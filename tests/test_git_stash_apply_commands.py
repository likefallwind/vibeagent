from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_stash_apply_commands, git_stash_commands


class GitStashApplyCommandsTests(unittest.TestCase):
    def test_git_stash_commands_keeps_apply_exports(self) -> None:
        self.assertIs(git_stash_commands.get_check_stash_apply_report, git_stash_apply_commands.get_check_stash_apply_report)
        self.assertIs(git_stash_commands.get_check_stash_apply_text, git_stash_apply_commands.get_check_stash_apply_text)
        self.assertIs(git_stash_commands.get_stash_apply_report, git_stash_apply_commands.get_stash_apply_report)
        self.assertIs(git_stash_commands.get_stash_apply_text, git_stash_apply_commands.get_stash_apply_text)

    def test_stash_apply_reports_usage_for_missing_stash_ref(self) -> None:
        root = Path("/tmp/vibeagent-stash-apply").resolve()

        check_report = git_stash_apply_commands.get_check_stash_apply_report(root)
        apply_report = git_stash_apply_commands.get_stash_apply_report(root, " ")

        self.assertFalse(check_report["ok"])
        self.assertIn("Usage: /check-stash-apply <stash@{N}>", check_report["message"])
        self.assertFalse(apply_report["ok"])
        self.assertIn("Usage: /stash-apply <stash@{N}>", apply_report["message"])

    def test_check_stash_apply_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_stash_apply",
            ok=True,
            stash_ref="stash@{0}",
            patch="+line\n",
            status=" M app.py",
            message="Stash stash@{0} can be applied.",
            worktree_clean=True,
        )
        root = Path("/tmp/vibeagent-stash-apply").resolve()

        with patch("vibeagent.git_stash_apply_commands._execute_action", return_value=observation) as execute_action:
            report = git_stash_apply_commands.get_check_stash_apply_report(root, "stash@{0}")
            text = git_stash_apply_commands.get_check_stash_apply_text(root, "stash@{0}")

        self.assertTrue(report["ok"])
        self.assertEqual(report["stashRef"], "stash@{0}")
        self.assertEqual(report["patch"]["chars"], 6)
        self.assertEqual(report["statusText"], " M app.py")
        self.assertTrue(report["worktreeClean"])
        self.assertIn("Check stash apply:", text)
        self.assertIn("worktreeClean: yes", text)
        execute_action.assert_called()

    def test_stash_apply_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="git_stash_apply",
            ok=True,
            stash_ref="stash@{0}",
            patch="+line\n",
            status=" M app.py",
            message="Applied stash@{0}.",
        )
        root = Path("/tmp/vibeagent-stash-apply").resolve()

        with patch("vibeagent.git_stash_apply_commands._execute_action", return_value=observation) as execute_action:
            report = git_stash_apply_commands.get_stash_apply_report(root, "stash@{0}")
            text = git_stash_apply_commands.get_stash_apply_text(root, "stash@{0}")

        self.assertTrue(report["ok"])
        self.assertEqual(report["stashRef"], "stash@{0}")
        self.assertEqual(report["patch"]["text"], "+line\n")
        self.assertNotIn("worktreeClean", report)
        self.assertIn("Stash apply:", text)
        self.assertIn("patchChars: 6", text)
        execute_action.assert_called()


if __name__ == "__main__":
    unittest.main()
