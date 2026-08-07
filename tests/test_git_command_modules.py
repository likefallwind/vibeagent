from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import git_commands
from vibeagent import git_history_commands, git_history_report_helpers, git_index_report_helpers, git_local_report_helpers
from vibeagent.git_read_commands import (
    _clip,
    _indent_block,
    clip_with_flag,
    format_blame_report_text,
    format_branches_report_text,
    format_git_conflicts_report_text,
    format_git_info_report_text,
    format_git_status_report_text,
    format_log_report_text,
    format_show_report_text,
    get_blame_report,
    get_blame_text,
    get_git_status_report,
    get_log_report,
    get_log_text,
    get_show_report,
    get_show_text,
    parse_log_request,
    parse_show_request,
)
from vibeagent.git_history_commands import (
    get_blame_report as history_get_blame_report,
    get_blame_text as history_get_blame_text,
    get_log_report as history_get_log_report,
    get_log_text as history_get_log_text,
    get_show_report as history_get_show_report,
    get_show_text as history_get_show_text,
    parse_log_request as history_parse_log_request,
    parse_show_request as history_parse_show_request,
)
from vibeagent.git_read_report_helpers import (
    clip,
    clip_with_flag as report_clip_with_flag,
    format_blame_report_text as report_format_blame_report_text,
    format_branches_report_text as report_format_branches_report_text,
    format_git_conflicts_report_text as report_format_git_conflicts_report_text,
    format_git_info_report_text as report_format_git_info_report_text,
    format_git_status_report_text as report_format_git_status_report_text,
    format_log_report_text as report_format_log_report_text,
    format_show_report_text as report_format_show_report_text,
    indent_block,
)
from vibeagent.git_sync_commands import (
    format_git_fetch_report_text,
    format_git_pull_report_text,
    format_git_push_report_text,
    format_git_sync_preview_report_text,
    get_check_fetch_report,
    get_check_fetch_text,
    get_check_pull_report,
    get_check_pull_text,
    get_check_push_report,
    get_check_push_text,
    get_fetch_report,
    get_fetch_text,
    get_pull_report,
    get_pull_text,
    get_push_report,
    get_push_text,
    parse_optional_remote_argument,
)
from vibeagent.git_sync_report_helpers import (
    format_git_fetch_report_text as sync_report_format_git_fetch_report_text,
    format_git_pull_report_text as sync_report_format_git_pull_report_text,
    format_git_push_report_text as sync_report_format_git_push_report_text,
    format_git_sync_preview_report_text as sync_report_format_git_sync_preview_report_text,
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

    def test_git_read_commands_reexports_history_helpers(self) -> None:
        self.assertIs(get_log_report, history_get_log_report)
        self.assertIs(get_log_text, history_get_log_text)
        self.assertIs(get_show_report, history_get_show_report)
        self.assertIs(get_show_text, history_get_show_text)
        self.assertIs(get_blame_report, history_get_blame_report)
        self.assertIs(get_blame_text, history_get_blame_text)
        self.assertIs(parse_log_request, history_parse_log_request)
        self.assertIs(parse_show_request, history_parse_show_request)

    def test_git_history_commands_reexports_report_helpers(self) -> None:
        self.assertIs(git_history_commands._split_nonempty_lines, git_history_report_helpers.split_nonempty_lines)
        self.assertIs(git_history_commands._usage_error, git_history_report_helpers.usage_error)
        self.assertIs(git_history_commands._git_output_payload, git_history_report_helpers.git_output_payload)
        self.assertIs(git_history_commands._git_log_items, git_history_report_helpers.git_log_items)

    def test_git_history_report_helpers_parse_output_payloads(self) -> None:
        self.assertEqual(git_history_report_helpers.split_nonempty_lines("one\n\n two \n"), ["one", " two "])
        self.assertEqual(
            git_history_report_helpers.git_output_payload("a\nb\n", truncated=True, max_output_chars=1000),
            {"text": "a\nb\n", "chars": 4, "lines": 2, "truncated": True, "maxOutputChars": 1000},
        )
        self.assertEqual(
            git_history_report_helpers.git_log_items("abc123 subject line\n\ndef456 another\n"),
            [
                {"hash": "abc123", "subject": "subject line", "raw": "abc123 subject line"},
                {"hash": "def456", "subject": "another", "raw": "def456 another"},
            ],
        )

    def test_git_history_text_helpers_resolve_compatibility_patch_targets(self) -> None:
        root = Path(".").resolve()
        log_report = {"ok": True, "message": "log"}
        show_report = {"ok": True, "message": "show"}
        blame_report = {"ok": True, "message": "blame"}
        with (
            patch("vibeagent.git_commands.get_log_report", return_value=log_report) as get_log,
            patch("vibeagent.git_commands.format_log_report_text", return_value="log rendered") as format_log,
            patch("vibeagent.git_commands.get_show_report", return_value=show_report) as get_show,
            patch("vibeagent.git_commands.format_show_report_text", return_value="show rendered") as format_show,
            patch("vibeagent.git_commands.get_blame_report", return_value=blame_report) as get_blame,
            patch("vibeagent.git_commands.format_blame_report_text", return_value="blame rendered") as format_blame,
        ):
            self.assertEqual(history_get_log_text(root, "src/app.py", max_count=3), "log rendered")
            self.assertEqual(history_get_show_text(root, "HEAD src/app.py", max_output_chars=2_000), "show rendered")
            self.assertEqual(history_get_blame_text(root, "src/app.py", max_output_chars=3_000), "blame rendered")

        get_log.assert_called_once_with(root, "src/app.py", max_count=3)
        format_log.assert_called_once_with(log_report)
        get_show.assert_called_once_with(root, "HEAD src/app.py", rev=None, path=None, max_output_chars=2_000)
        format_show.assert_called_once_with(show_report)
        get_blame.assert_called_once_with(root, "src/app.py", line_range=None, max_output_chars=3_000)
        format_blame.assert_called_once_with(blame_report)

    def test_git_read_commands_reexports_report_helpers(self) -> None:
        self.assertIs(_clip, clip)
        self.assertIs(_indent_block, indent_block)
        self.assertIs(clip_with_flag, report_clip_with_flag)
        self.assertIs(format_git_status_report_text, report_format_git_status_report_text)
        self.assertIs(format_git_conflicts_report_text, report_format_git_conflicts_report_text)
        self.assertIs(format_git_info_report_text, report_format_git_info_report_text)
        self.assertIs(format_branches_report_text, report_format_branches_report_text)
        self.assertIs(format_log_report_text, report_format_log_report_text)
        self.assertIs(format_show_report_text, report_format_show_report_text)
        self.assertIs(format_blame_report_text, report_format_blame_report_text)

    def test_git_commands_reexports_sync_helpers(self) -> None:
        self.assertIs(git_commands.get_check_fetch_report, get_check_fetch_report)
        self.assertIs(git_commands.get_check_fetch_text, get_check_fetch_text)
        self.assertIs(git_commands.get_fetch_report, get_fetch_report)
        self.assertIs(git_commands.get_fetch_text, get_fetch_text)
        self.assertIs(git_commands.get_check_pull_report, get_check_pull_report)
        self.assertIs(git_commands.get_check_pull_text, get_check_pull_text)
        self.assertIs(git_commands.get_pull_report, get_pull_report)
        self.assertIs(git_commands.get_pull_text, get_pull_text)
        self.assertIs(git_commands.get_check_push_report, get_check_push_report)
        self.assertIs(git_commands.get_check_push_text, get_check_push_text)
        self.assertIs(git_commands.get_push_report, get_push_report)
        self.assertIs(git_commands.get_push_text, get_push_text)
        self.assertIs(git_commands.format_git_fetch_report_text, format_git_fetch_report_text)
        self.assertIs(git_commands.format_git_sync_preview_report_text, format_git_sync_preview_report_text)
        self.assertIs(git_commands.format_git_pull_report_text, format_git_pull_report_text)
        self.assertIs(git_commands.format_git_push_report_text, format_git_push_report_text)
        self.assertIs(git_commands.parse_optional_remote_argument, parse_optional_remote_argument)

    def test_git_sync_commands_reexports_report_helpers(self) -> None:
        self.assertIs(format_git_fetch_report_text, sync_report_format_git_fetch_report_text)
        self.assertIs(format_git_sync_preview_report_text, sync_report_format_git_sync_preview_report_text)
        self.assertIs(format_git_pull_report_text, sync_report_format_git_pull_report_text)
        self.assertIs(format_git_push_report_text, sync_report_format_git_push_report_text)

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

    def test_git_local_report_helpers_reexports_index_helpers(self) -> None:
        self.assertIs(git_local_report_helpers.git_index_usage_report, git_index_report_helpers.git_index_usage_report)
        self.assertIs(git_local_report_helpers.git_index_unexpected_report, git_index_report_helpers.git_index_unexpected_report)
        self.assertIs(git_local_report_helpers.git_index_observation_report, git_index_report_helpers.git_index_observation_report)
        self.assertIs(git_local_report_helpers.format_git_index_report_text, git_index_report_helpers.format_git_index_report_text)
        self.assertIs(git_local_report_helpers.format_git_index_text, git_index_report_helpers.format_git_index_text)

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
