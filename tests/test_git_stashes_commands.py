from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vibeagent import git_stash_commands, git_stashes_commands


class GitStashesCommandsTests(unittest.TestCase):
    def test_git_stash_commands_keeps_stashes_exports(self) -> None:
        self.assertIs(git_stash_commands.get_stashes_report, git_stashes_commands.get_stashes_report)
        self.assertIs(git_stash_commands.get_stashes_text, git_stashes_commands.get_stashes_text)
        self.assertIs(git_stash_commands.format_stashes_report_text, git_stashes_commands.format_stashes_report_text)
        self.assertIs(git_stash_commands.parse_stashes_request, git_stashes_commands.parse_stashes_request)

    def test_parse_stashes_request_validates_optional_count(self) -> None:
        self.assertEqual(git_stashes_commands.parse_stashes_request(None), 20)
        self.assertEqual(git_stashes_commands.parse_stashes_request("5"), 5)
        with self.assertRaisesRegex(ValueError, "invalid count"):
            git_stashes_commands.parse_stashes_request("abc")
        with self.assertRaisesRegex(ValueError, "expected optional count"):
            git_stashes_commands.parse_stashes_request("1 2")
        with self.assertRaisesRegex(ValueError, "at least 1"):
            git_stashes_commands.parse_stashes_request("0")
        with self.assertRaisesRegex(ValueError, "at most 100"):
            git_stashes_commands.parse_stashes_request("101")

    def test_get_stashes_report_serializes_entries_and_usage(self) -> None:
        observation = SimpleNamespace(
            kind="git_stashes",
            ok=True,
            entries=[
                SimpleNamespace(name="stash@{0}", summary="stash@{0}: WIP on main: save work"),
                SimpleNamespace(name="stash@{1}", summary="stash@{1}: WIP on main: older"),
            ],
            total=2,
            truncated=False,
            message="Found 2 stash entry(s).",
        )
        root = Path("/tmp/vibeagent-stashes").resolve()
        with patch("vibeagent.git_stashes_commands._execute_action", return_value=observation) as execute_action:
            report = git_stashes_commands.get_stashes_report(root, "2", max_entries=5)
            text = git_stashes_commands.format_stashes_report_text(report)
            usage = git_stashes_commands.get_stashes_report(root, "bad")

        self.assertTrue(report["ok"])
        self.assertEqual(report["maxEntries"], 2)
        self.assertEqual(report["entries"]["shown"], 2)
        self.assertEqual(report["entries"]["items"][0]["name"], "stash@{0}")
        self.assertIn("Stashes:", text)
        self.assertIn("stash@{1}", text)
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /stashes", usage["message"])
        execute_action.assert_called_once()


if __name__ == "__main__":
    unittest.main()
