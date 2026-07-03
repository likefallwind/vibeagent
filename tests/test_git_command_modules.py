from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import git_commands
from vibeagent.git_read_commands import (
    format_blame_report_text,
    format_git_status_report_text,
    get_blame_report,
    get_git_status_report,
    parse_log_request,
)
from vibeagent.git_sync_commands import (
    format_git_fetch_report_text,
    format_git_pull_report_text,
    format_git_push_report_text,
    format_git_sync_preview_report_text,
    get_check_fetch_report,
    get_check_pull_report,
    get_check_push_report,
    get_fetch_report,
    get_pull_report,
    get_push_report,
    parse_optional_remote_argument,
)
from vibeagent.git_stash_commands import (
    format_git_stash_apply_report_text,
    format_git_stash_drop_report_text,
    format_git_stash_report_text,
    format_stashes_report_text,
    get_check_stash_apply_report,
    get_check_stash_apply_text,
    get_check_stash_drop_report,
    get_check_stash_drop_text,
    get_check_stash_report,
    get_check_stash_text,
    get_stash_apply_report,
    get_stash_apply_text,
    get_stash_drop_report,
    get_stash_drop_text,
    get_stash_report,
    get_stash_text,
    get_stashes_report,
    get_stashes_text,
    parse_stash_argument,
    parse_stashes_request,
)
from vibeagent.git_local_report_helpers import (
    format_git_commit_report_text,
    format_git_index_report_text,
    format_git_restore_report_text,
    format_git_switch_report_text,
)


class GitCommandModuleTests(unittest.TestCase):
    def test_git_commands_reexports_read_helpers(self) -> None:
        self.assertIs(git_commands.get_git_status_report, get_git_status_report)
        self.assertIs(git_commands.format_git_status_report_text, format_git_status_report_text)
        self.assertIs(git_commands.get_blame_report, get_blame_report)
        self.assertIs(git_commands.format_blame_report_text, format_blame_report_text)
        self.assertIs(git_commands.parse_log_request, parse_log_request)

    def test_git_commands_reexports_sync_helpers(self) -> None:
        self.assertIs(git_commands.get_check_fetch_report, get_check_fetch_report)
        self.assertIs(git_commands.get_fetch_report, get_fetch_report)
        self.assertIs(git_commands.get_check_pull_report, get_check_pull_report)
        self.assertIs(git_commands.get_pull_report, get_pull_report)
        self.assertIs(git_commands.get_check_push_report, get_check_push_report)
        self.assertIs(git_commands.get_push_report, get_push_report)
        self.assertIs(git_commands.format_git_fetch_report_text, format_git_fetch_report_text)
        self.assertIs(git_commands.format_git_sync_preview_report_text, format_git_sync_preview_report_text)
        self.assertIs(git_commands.format_git_pull_report_text, format_git_pull_report_text)
        self.assertIs(git_commands.format_git_push_report_text, format_git_push_report_text)
        self.assertIs(git_commands.parse_optional_remote_argument, parse_optional_remote_argument)

    def test_git_commands_reexports_stash_helpers(self) -> None:
        self.assertIs(git_commands.get_stashes_report, get_stashes_report)
        self.assertIs(git_commands.get_stashes_text, get_stashes_text)
        self.assertIs(git_commands.format_stashes_report_text, format_stashes_report_text)
        self.assertIs(git_commands.get_check_stash_report, get_check_stash_report)
        self.assertIs(git_commands.get_check_stash_text, get_check_stash_text)
        self.assertIs(git_commands.get_stash_report, get_stash_report)
        self.assertIs(git_commands.get_stash_text, get_stash_text)
        self.assertIs(git_commands.get_check_stash_apply_report, get_check_stash_apply_report)
        self.assertIs(git_commands.get_check_stash_apply_text, get_check_stash_apply_text)
        self.assertIs(git_commands.get_stash_apply_report, get_stash_apply_report)
        self.assertIs(git_commands.get_stash_apply_text, get_stash_apply_text)
        self.assertIs(git_commands.get_check_stash_drop_report, get_check_stash_drop_report)
        self.assertIs(git_commands.get_check_stash_drop_text, get_check_stash_drop_text)
        self.assertIs(git_commands.get_stash_drop_report, get_stash_drop_report)
        self.assertIs(git_commands.get_stash_drop_text, get_stash_drop_text)
        self.assertIs(git_commands.format_git_stash_report_text, format_git_stash_report_text)
        self.assertIs(git_commands.format_git_stash_apply_report_text, format_git_stash_apply_report_text)
        self.assertIs(git_commands.format_git_stash_drop_report_text, format_git_stash_drop_report_text)
        self.assertIs(git_commands.parse_stash_argument, parse_stash_argument)
        self.assertIs(git_commands.parse_stashes_request, parse_stashes_request)

    def test_git_commands_reexports_local_report_helpers(self) -> None:
        self.assertIs(git_commands.format_git_index_report_text, format_git_index_report_text)
        self.assertIs(git_commands.format_git_commit_report_text, format_git_commit_report_text)
        self.assertIs(git_commands.format_git_restore_report_text, format_git_restore_report_text)
        self.assertIs(git_commands.format_git_switch_report_text, format_git_switch_report_text)

    def test_stash_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        root = Path(".").resolve()
        stashes_report = {"ok": True, "message": "stashes"}
        stash_report = {"ok": True, "message": "stash"}
        with (
            patch("vibeagent.git_commands.get_stashes_report", return_value=stashes_report) as get_stashes,
            patch("vibeagent.git_commands.format_stashes_report_text", return_value="stashes rendered") as format_stashes,
            patch("vibeagent.git_commands.get_stash_apply_report", return_value=stash_report) as get_apply,
            patch("vibeagent.git_commands.format_git_stash_apply_report_text", return_value="apply rendered") as format_apply,
        ):
            self.assertEqual(get_stashes_text(root, "2", max_entries=5), "stashes rendered")
            self.assertEqual(get_stash_apply_text(root, "stash@{0}"), "apply rendered")

        get_stashes.assert_called_once_with(root, "2", max_entries=5)
        format_stashes.assert_called_once_with(stashes_report)
        get_apply.assert_called_once_with(root, "stash@{0}", max_patch_chars=12_000)
        format_apply.assert_called_once_with("Stash apply", stash_report)


if __name__ == "__main__":
    unittest.main()
