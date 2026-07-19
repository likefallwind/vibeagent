from __future__ import annotations

import unittest

from vibeagent.workspace_git_remote_selection import select_fetch_remote_from_remotes


class WorkspaceGitRemoteSelectionTests(unittest.TestCase):
    def test_select_fetch_remote_uses_single_remote_by_default(self) -> None:
        self.assertEqual(
            select_fetch_remote_from_remotes(
                [{"name": "origin", "url": "git@example.com/repo.git", "kind": "fetch"}],
                None,
            ),
            {
                "ok": True,
                "remote": "origin",
                "remote_url": "git@example.com/repo.git",
                "message": "Git remote selected.",
            },
        )

    def test_select_fetch_remote_requires_explicit_name_when_multiple_remotes_exist(self) -> None:
        self.assertEqual(
            select_fetch_remote_from_remotes(
                [
                    {"name": "backup", "url": "git@example.com/backup.git"},
                    {"name": "origin", "url": "git@example.com/repo.git"},
                ],
                None,
            ),
            {
                "ok": False,
                "remote": "",
                "remote_url": "",
                "message": "Multiple git remotes are configured; specify one remote.",
            },
        )

    def test_select_fetch_remote_accepts_requested_remote_and_reports_errors(self) -> None:
        fetch_remotes = [{"name": "origin", "url": "git@example.com/repo.git"}]

        self.assertEqual(
            select_fetch_remote_from_remotes(fetch_remotes, " origin "),
            {
                "ok": True,
                "remote": "origin",
                "remote_url": "git@example.com/repo.git",
                "message": "Git remote selected.",
            },
        )
        self.assertEqual(
            select_fetch_remote_from_remotes(fetch_remotes, "upstream"),
            {
                "ok": False,
                "remote": "upstream",
                "remote_url": "",
                "message": "Git remote not found: upstream.",
            },
        )
        self.assertEqual(
            select_fetch_remote_from_remotes(fetch_remotes, " "),
            {
                "ok": False,
                "remote": "",
                "remote_url": "",
                "message": "git_fetch remote must be non-empty when provided.",
            },
        )

    def test_select_fetch_remote_reports_missing_remotes(self) -> None:
        self.assertEqual(
            select_fetch_remote_from_remotes([], None),
            {
                "ok": False,
                "remote": "",
                "remote_url": "",
                "message": "No git remotes are configured.",
            },
        )


if __name__ == "__main__":
    unittest.main()
