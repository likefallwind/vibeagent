from __future__ import annotations

import unittest
from pathlib import Path

from vibeagent import git_stash_commands, git_stash_report_helpers


class GitStashReportHelperTests(unittest.TestCase):
    def test_git_stash_commands_reexports_report_helpers(self) -> None:
        self.assertIs(git_stash_commands.format_git_stash_text, git_stash_report_helpers.format_git_stash_text)
        self.assertIs(git_stash_commands.format_git_stash_report_text, git_stash_report_helpers.format_git_stash_report_text)
        self.assertIs(git_stash_commands.format_git_stash_apply_text, git_stash_report_helpers.format_git_stash_apply_text)
        self.assertIs(
            git_stash_commands.format_git_stash_apply_report_text,
            git_stash_report_helpers.format_git_stash_apply_report_text,
        )
        self.assertIs(git_stash_commands.format_git_stash_drop_text, git_stash_report_helpers.format_git_stash_drop_text)
        self.assertIs(
            git_stash_commands.format_git_stash_drop_report_text,
            git_stash_report_helpers.format_git_stash_drop_report_text,
        )

    def test_stash_text_helper_clips_diff_and_validates_bounds(self) -> None:
        root = Path("/tmp/vibeagent-stash-report").resolve()
        rendered = git_stash_report_helpers.format_git_stash_text(
            "Stash",
            root,
            True,
            "save work",
            True,
            "stash@{0}",
            " M app.py",
            "x" * 150,
            "Saved stash.",
            100,
        )

        self.assertIn("Stash:", rendered)
        self.assertIn("includeUntracked: yes", rendered)
        self.assertIn("stashRef: stash@{0}", rendered)
        self.assertIn("diffChars: 150", rendered)
        self.assertIn("diffTruncated: yes", rendered)
        with self.assertRaisesRegex(ValueError, "at least 100"):
            git_stash_report_helpers.format_git_stash_text("Stash", root, True, "", False, "", "", "", "", 99)

    def test_apply_and_drop_formatters_render_optional_fields(self) -> None:
        root = Path("/tmp/vibeagent-stash-report").resolve()
        apply_text = git_stash_report_helpers.format_git_stash_apply_text(
            "Stash apply",
            root,
            True,
            "stash@{0}",
            False,
            "+new line\n",
            " M app.py",
            "Applied stash@{0}.",
            12_000,
        )
        drop_text = git_stash_report_helpers.format_git_stash_drop_text(
            "Stash drop",
            root,
            True,
            "stash@{0}",
            "stash@{0}: save work",
            "+new line\n",
            0,
            "Dropped stash@{0}.",
            12_000,
        )

        self.assertIn("worktreeClean: no", apply_text)
        self.assertIn("patchChars: 10", apply_text)
        self.assertIn("remainingTotal: 0", drop_text)
        self.assertIn("summary: stash@{0}: save work", drop_text)


if __name__ == "__main__":
    unittest.main()
