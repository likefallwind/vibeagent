from __future__ import annotations

import unittest

from vibeagent.workspace_git_sync_preview import (
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
