from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_stash_commands, git_stash_drop_commands


class GitStashDropCommandsTests(unittest.TestCase):
    def test_git_stash_commands_keeps_drop_exports(self) -> None:
        self.assertIs(git_stash_commands.get_check_stash_drop_report, git_stash_drop_commands.get_check_stash_drop_report)
        self.assertIs(git_stash_commands.get_check_stash_drop_text, git_stash_drop_commands.get_check_stash_drop_text)
        self.assertIs(git_stash_commands.get_stash_drop_report, git_stash_drop_commands.get_stash_drop_report)
        self.assertIs(git_stash_commands.get_stash_drop_text, git_stash_drop_commands.get_stash_drop_text)

    def test_stash_drop_reports_usage_for_missing_stash_ref(self) -> None:
        root = Path("/tmp/vibeagent-stash-drop").resolve()

        check_report = git_stash_drop_commands.get_check_stash_drop_report(root)
        drop_report = git_stash_drop_commands.get_stash_drop_report(root, " ")

        self.assertFalse(check_report["ok"])
        self.assertIn("Usage: /check-stash-drop <stash@{N}>", check_report["message"])
        self.assertFalse(drop_report["ok"])
        self.assertIn("Usage: /stash-drop <stash@{N}>", drop_report["message"])

    def test_check_stash_drop_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_stash_drop",
            ok=True,
            stash_ref="stash@{0}",
            summary="stash@{0}: WIP on main: save work",
            patch="+line\n",
            message="Stash stash@{0} can be dropped.",
        )
        root = Path("/tmp/vibeagent-stash-drop").resolve()

        with patch("vibeagent.git_stash_drop_commands._execute_action", return_value=observation) as execute_action:
            report = git_stash_drop_commands.get_check_stash_drop_report(root, "stash@{0}")
            text = git_stash_drop_commands.get_check_stash_drop_text(root, "stash@{0}")

        self.assertTrue(report["ok"])
        self.assertEqual(report["stashRef"], "stash@{0}")
        self.assertEqual(report["summary"], "stash@{0}: WIP on main: save work")
        self.assertEqual(report["patch"]["chars"], 6)
        self.assertIn("Check stash drop:", text)
        self.assertIn("summary: stash@{0}: WIP on main: save work", text)
        execute_action.assert_called()

    def test_stash_drop_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="git_stash_drop",
            ok=True,
            stash_ref="stash@{0}",
            summary="stash@{0}: WIP on main: save work",
            patch="+line\n",
            message="Dropped stash@{0}.",
            remaining_total=2,
        )
        root = Path("/tmp/vibeagent-stash-drop").resolve()

        with patch("vibeagent.git_stash_drop_commands._execute_action", return_value=observation) as execute_action:
            report = git_stash_drop_commands.get_stash_drop_report(root, "stash@{0}")
            text = git_stash_drop_commands.get_stash_drop_text(root, "stash@{0}")

        self.assertTrue(report["ok"])
        self.assertEqual(report["stashRef"], "stash@{0}")
        self.assertEqual(report["patch"]["text"], "+line\n")
        self.assertEqual(report["remainingTotal"], 2)
        self.assertIn("Stash drop:", text)
        self.assertIn("remainingTotal: 2", text)
        execute_action.assert_called()


if __name__ == "__main__":
    unittest.main()
