from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_stash_commands, git_stash_save_commands


class GitStashSaveCommandsTests(unittest.TestCase):
    def test_git_stash_commands_keeps_save_exports(self) -> None:
        self.assertIs(git_stash_commands.get_check_stash_report, git_stash_save_commands.get_check_stash_report)
        self.assertIs(git_stash_commands.get_check_stash_text, git_stash_save_commands.get_check_stash_text)
        self.assertIs(git_stash_commands.get_stash_report, git_stash_save_commands.get_stash_report)
        self.assertIs(git_stash_commands.get_stash_text, git_stash_save_commands.get_stash_text)
        self.assertIs(git_stash_commands.parse_stash_argument, git_stash_save_commands.parse_stash_argument)

    def test_parse_stash_argument_validates_options_and_message(self) -> None:
        self.assertEqual(git_stash_save_commands.parse_stash_argument(None), (None, False))
        self.assertEqual(git_stash_save_commands.parse_stash_argument("--include-untracked save work"), ("save work", True))
        self.assertEqual(git_stash_save_commands.parse_stash_argument("-u 'quoted message'"), ("quoted message", True))
        with self.assertRaisesRegex(ValueError, "unsupported option"):
            git_stash_save_commands.parse_stash_argument("--bad")
        with self.assertRaises(ValueError):
            git_stash_save_commands.parse_stash_argument("'unterminated")

    def test_check_stash_report_serializes_observation(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_stash",
            ok=True,
            message_text="save work",
            include_untracked=True,
            status=" M app.py",
            diff="+line\n",
            message="Stash can be saved.",
        )
        root = Path("/tmp/vibeagent-stash-save").resolve()

        with patch("vibeagent.git_stash_save_commands._execute_action", return_value=observation) as execute_action:
            report = git_stash_save_commands.get_check_stash_report(root, "--include-untracked save work")
            text = git_stash_save_commands.get_check_stash_text(root, "--include-untracked save work")

        self.assertTrue(report["ok"])
        self.assertEqual(report["messageText"], "save work")
        self.assertTrue(report["includeUntracked"])
        self.assertEqual(report["stashRef"], "")
        self.assertEqual(report["diff"]["chars"], 6)
        self.assertIn("Check stash:", text)
        self.assertIn("includeUntracked: yes", text)
        execute_action.assert_called()

    def test_stash_report_serializes_observation_and_usage_error(self) -> None:
        observation = SimpleNamespace(
            kind="git_stash",
            ok=True,
            message_text="save work",
            include_untracked=False,
            stash_ref="stash@{0}",
            status=" M app.py",
            diff="+line\n",
            message="Saved stash@{0}.",
        )
        root = Path("/tmp/vibeagent-stash-save").resolve()

        with patch("vibeagent.git_stash_save_commands._execute_action", return_value=observation) as execute_action:
            report = git_stash_save_commands.get_stash_report(root, "save work")
            text = git_stash_save_commands.get_stash_text(root, "save work")
            usage = git_stash_save_commands.get_stash_report(root, "--bad")

        self.assertTrue(report["ok"])
        self.assertEqual(report["stashRef"], "stash@{0}")
        self.assertEqual(report["diff"]["text"], "+line\n")
        self.assertIn("Stash:", text)
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /stash [--include-untracked] [message]", usage["message"])
        execute_action.assert_called()


if __name__ == "__main__":
    unittest.main()
