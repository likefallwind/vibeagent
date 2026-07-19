from __future__ import annotations

import unittest

from vibeagent.workspace_git_sync_preview import (
    git_fetch_result_payload,
    git_pull_result_payload,
    git_push_result_payload,
    git_sync_detached_head_payload,
    git_sync_dirty_worktree_payload,
    git_sync_missing_upstream_payload,
    git_sync_preview_payload,
    pull_readiness,
    push_readiness,
)


class WorkspaceGitSyncPreviewTests(unittest.TestCase):
    def test_git_sync_preview_payload_preserves_field_shape(self) -> None:
        self.assertEqual(
            git_sync_preview_payload(
                ok=True,
                remote="origin",
                branch="main",
                current="main",
                upstream="origin/main",
                ahead=1,
                behind=2,
                worktree_clean=True,
                status="",
                message="ready",
            ),
            {
                "ok": True,
                "remote": "origin",
                "branch": "main",
                "current": "main",
                "upstream": "origin/main",
                "ahead": 1,
                "behind": 2,
                "worktree_clean": True,
                "status": "",
                "message": "ready",
            },
        )

    def test_git_fetch_result_payload_preserves_field_shape(self) -> None:
        self.assertEqual(
            git_fetch_result_payload(
                ok=True,
                remote="origin",
                remote_url="git@example.com/repo.git",
                branch="main",
                upstream="origin/main",
                ahead_before=1,
                behind_before=2,
                ahead_after=0,
                behind_after=0,
                message="fetched",
            ),
            {
                "ok": True,
                "remote": "origin",
                "remote_url": "git@example.com/repo.git",
                "branch": "main",
                "upstream": "origin/main",
                "ahead_before": 1,
                "behind_before": 2,
                "ahead_after": 0,
                "behind_after": 0,
                "message": "fetched",
            },
        )

    def test_git_sync_preflight_payloads_preserve_failure_shapes(self) -> None:
        self.assertEqual(
            git_sync_detached_head_payload(operation="pull", ahead=1, behind=2, status=""),
            {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "",
                "upstream": "",
                "ahead": 1,
                "behind": 2,
                "worktree_clean": False,
                "status": "",
                "message": "Cannot pull while HEAD is detached.",
            },
        )
        self.assertEqual(
            git_sync_missing_upstream_payload(
                remote="",
                branch="",
                current="main",
                upstream="",
                ahead=0,
                behind=0,
                worktree_clean=True,
                status="",
            ),
            {
                "ok": False,
                "remote": "",
                "branch": "",
                "current": "main",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "worktree_clean": True,
                "status": "",
                "message": "Current branch has no upstream configured.",
            },
        )
        self.assertEqual(
            git_sync_dirty_worktree_payload(
                operation="pushing",
                remote="origin",
                branch="main",
                current="main",
                upstream="origin/main",
                ahead=1,
                behind=0,
                status=" M app.py",
            ),
            {
                "ok": False,
                "remote": "origin",
                "branch": "main",
                "current": "main",
                "upstream": "origin/main",
                "ahead": 1,
                "behind": 0,
                "worktree_clean": False,
                "status": " M app.py",
                "message": "Working tree has uncommitted changes; commit or clean changes before pushing.",
            },
        )

    def test_git_pull_and_push_result_payloads_preserve_field_shapes(self) -> None:
        self.assertEqual(
            git_pull_result_payload(
                ok=False,
                remote="origin",
                branch="main",
                current_before="main",
                current_after="main",
                upstream="origin/main",
                ahead_before=0,
                behind_before=1,
                ahead_after=0,
                behind_after=0,
                status=" M app.py",
                message="blocked",
            ),
            {
                "ok": False,
                "remote": "origin",
                "branch": "main",
                "current_before": "main",
                "current_after": "main",
                "upstream": "origin/main",
                "ahead_before": 0,
                "behind_before": 1,
                "ahead_after": 0,
                "behind_after": 0,
                "status": " M app.py",
                "message": "blocked",
            },
        )
        self.assertEqual(
            git_push_result_payload(
                ok=True,
                remote="origin",
                branch="main",
                current="main",
                upstream="origin/main",
                ahead_before=2,
                behind_before=0,
                status="",
                message="pushed",
            ),
            {
                "ok": True,
                "remote": "origin",
                "branch": "main",
                "current": "main",
                "upstream": "origin/main",
                "ahead_before": 2,
                "behind_before": 0,
                "status": "",
                "message": "pushed",
            },
        )

    def test_pull_readiness_keeps_existing_ahead_behind_decisions(self) -> None:
        self.assertEqual(
            pull_readiness(1, 1, upstream="origin/main", current="main"),
            (False, "Current branch has diverged from upstream; fast-forward pull is not safe."),
        )
        self.assertEqual(
            pull_readiness(1, 0, upstream="origin/main", current="main"),
            (False, "Current branch is ahead of upstream; nothing to fast-forward pull."),
        )
        self.assertEqual(
            pull_readiness(0, 2, upstream="origin/main", current="main"),
            (True, "Can fast-forward pull origin/main into main."),
        )

    def test_push_readiness_keeps_existing_ahead_behind_decisions(self) -> None:
        self.assertEqual(
            push_readiness(0, 1, upstream="origin/main", current="main"),
            (False, "Current branch is behind upstream; fetch and fast-forward pull before pushing."),
        )
        self.assertEqual(
            push_readiness(0, 0, upstream="origin/main", current="main"),
            (False, "Current branch has no commits to push."),
        )
        self.assertEqual(
            push_readiness(2, 0, upstream="origin/main", current="main"),
            (True, "Can push 2 commit(s) from main to origin/main."),
        )


if __name__ == "__main__":
    unittest.main()
