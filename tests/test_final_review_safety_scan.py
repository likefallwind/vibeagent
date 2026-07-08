import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.final_review_safety_scan import collect_final_review_safety_scan
from vibeagent.workspace_core import create_run_workspace


class FinalReviewSafetyScanTests(unittest.TestCase):
    def test_collect_final_review_safety_scan_composes_scan_helpers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-review-") as base:
            workspace = create_run_workspace(Path(base), "test-run")
            review_files = [{"path": "app.py", "status": "M"}]
            review_scan_files = [{"path": "app.py", "status": "M"}, {"path": "session.py", "status": "session"}]

            with (
                patch(
                    "vibeagent.final_review_safety_scan.read_git_conflicts",
                    return_value={"ok": True, "markers": []},
                ) as read_git_conflicts,
                patch(
                    "vibeagent.final_review_safety_scan.final_review_scan_file_items",
                    return_value=review_scan_files,
                ) as final_review_scan_file_items,
                patch(
                    "vibeagent.final_review_safety_scan.find_large_changed_files",
                    return_value=([{"path": "big.bin", "size_bytes": 123}], 2),
                ) as find_large_changed_files,
                patch(
                    "vibeagent.final_review_safety_scan.find_secret_like_changed_files",
                    return_value=([{"path": "app.py", "line": 1, "label": "token"}], 3, True),
                ) as find_secret_like_changed_files,
                patch(
                    "vibeagent.final_review_safety_scan.find_secret_like_git_diff_additions",
                    return_value=(
                        [{"path": "app.py", "line": 2, "label": "api key", "source": "worktree"}],
                        4,
                        True,
                        ["diff warning"],
                    ),
                ) as find_secret_like_git_diff_additions,
                patch(
                    "vibeagent.final_review_safety_scan.find_nested_git_repositories",
                    return_value=(["vendor"], 5),
                ) as find_nested_git_repositories,
                patch(
                    "vibeagent.final_review_safety_scan.find_changed_gitlinks",
                    return_value=(["vendor/lib"], 6, ["gitlink warning"]),
                ) as find_changed_gitlinks,
                patch(
                    "vibeagent.final_review_safety_scan.find_hidden_tracked_git_changes",
                    return_value=([{"path": ".codex/private.txt", "status": " M"}], 7, ["hidden warning"]),
                ) as find_hidden_tracked_git_changes,
                patch(
                    "vibeagent.final_review_safety_scan.find_unsafe_changed_symlinks",
                    return_value=(
                        [{"path": "leak.txt", "target": "../outside.txt", "reason": "points outside project"}],
                        8,
                        ["symlink warning"],
                        {"points outside project"},
                    ),
                ) as find_unsafe_changed_symlinks,
                patch(
                    "vibeagent.final_review_safety_scan.read_git_operation_state",
                    return_value={"ok": False, "operations": [], "message": "git dir unavailable"},
                ) as read_git_operation_state,
                patch(
                    "vibeagent.final_review_safety_scan.read_git_info",
                    return_value={"ok": True, "branch": "main", "upstream": "origin/main", "ahead": 1, "behind": 0},
                ) as read_git_info,
            ):
                scan = collect_final_review_safety_scan(
                    workspace,
                    review_files,
                    large_file_bytes=111,
                    secret_scan_bytes=222,
                )

        read_git_conflicts.assert_called_once_with(workspace, max_markers=20, max_files=5000)
        final_review_scan_file_items.assert_called_once_with(workspace, review_files)
        find_large_changed_files.assert_called_once_with(workspace, review_scan_files, max_bytes=111)
        find_secret_like_changed_files.assert_called_once_with(workspace, review_scan_files, max_bytes=222)
        find_secret_like_git_diff_additions.assert_called_once_with(workspace, max_bytes=222)
        find_nested_git_repositories.assert_called_once_with(workspace)
        find_changed_gitlinks.assert_called_once_with(workspace)
        find_hidden_tracked_git_changes.assert_called_once_with(workspace)
        find_unsafe_changed_symlinks.assert_called_once_with(workspace, review_files)
        read_git_operation_state.assert_called_once_with(workspace)
        read_git_info.assert_called_once_with(workspace)

        self.assertEqual(scan.conflict_scan, {"ok": True, "markers": []})
        self.assertEqual(scan.large_files_total, 2)
        self.assertEqual(scan.secret_findings_total, 3)
        self.assertTrue(scan.secret_scan_truncated)
        self.assertEqual(scan.secret_diff_findings_total, 4)
        self.assertTrue(scan.secret_diff_truncated)
        self.assertEqual(scan.secret_diff_warnings, ["diff warning"])
        self.assertEqual(scan.nested_git_repo_total, 5)
        self.assertEqual(scan.changed_gitlink_total, 6)
        self.assertEqual(scan.hidden_git_change_total, 7)
        self.assertEqual(scan.unsafe_symlink_total, 8)
        self.assertEqual(scan.unsafe_symlink_reasons, {"points outside project"})
        self.assertEqual(scan.git_operation["message"], "git dir unavailable")
        self.assertEqual(scan.git_info["ahead"], 1)


if __name__ == "__main__":
    unittest.main()
