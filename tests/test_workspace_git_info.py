from __future__ import annotations

import unittest

from vibeagent.workspace_git_info import git_info_payload, git_not_repo_info, parse_ahead_behind_counts


class WorkspaceGitInfoTests(unittest.TestCase):
    def test_git_not_repo_info_preserves_field_shape(self) -> None:
        self.assertEqual(
            git_not_repo_info("not a git repo"),
            {
                "ok": False,
                "is_git_repo": False,
                "branch": "",
                "head": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "remotes": [],
                "status": "",
                "message": "not a git repo",
            },
        )

    def test_parse_ahead_behind_counts_accepts_git_count_output(self) -> None:
        self.assertEqual(parse_ahead_behind_counts("3\t5\n"), (3, 5))
        self.assertEqual(parse_ahead_behind_counts("3 5 extra\n"), (3, 5))
        self.assertEqual(parse_ahead_behind_counts("bad 5\n"), (0, 0))
        self.assertEqual(parse_ahead_behind_counts(""), (0, 0))

    def test_git_info_payload_builds_upstream_and_detached_messages(self) -> None:
        self.assertEqual(
            git_info_payload(
                branch="main",
                head="abc1234",
                upstream="origin/main",
                ahead=1,
                behind=2,
                remotes=[{"name": "origin", "url": "git@example.com/repo.git", "kind": "fetch"}],
                status=" M app.py\n",
            ),
            {
                "ok": True,
                "is_git_repo": True,
                "branch": "main",
                "head": "abc1234",
                "upstream": "origin/main",
                "ahead": 1,
                "behind": 2,
                "remotes": [{"name": "origin", "url": "git@example.com/repo.git", "kind": "fetch"}],
                "status": " M app.py\n",
                "message": "Git repository on main at abc1234. Upstream origin/main, ahead 1, behind 2.",
            },
        )
        self.assertEqual(
            git_info_payload(
                branch="",
                head="",
                upstream="",
                ahead=0,
                behind=0,
                remotes=[],
                status="",
            )["message"],
            "Git repository on detached HEAD at unknown. No upstream configured.",
        )


if __name__ == "__main__":
    unittest.main()
