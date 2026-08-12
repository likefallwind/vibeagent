from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session_pull_requests import (
    parse_pull_request_url,
    read_session_pull_requests,
    resolve_session_from_pull_request,
)
from vibeagent.workspace_core import create_run_workspace


class SessionPullRequestTests(unittest.TestCase):
    def test_parses_supported_pull_request_urls(self) -> None:
        cases = (
            ("https://github.com/acme/widgets/pull/42", "github", "acme/widgets"),
            ("https://github.example.com/acme/widgets/pull/42/", "github", "acme/widgets"),
            ("https://gitlab.com/acme/platform/widgets/-/merge_requests/42", "gitlab", "acme/platform/widgets"),
            ("https://bitbucket.org/acme/widgets/pull-requests/42", "bitbucket", "acme/widgets"),
        )
        for url, provider, repository in cases:
            with self.subTest(url=url):
                identity = parse_pull_request_url(url)
                self.assertEqual(identity.provider, provider)
                self.assertEqual(identity.repository, repository)
                self.assertEqual(identity.number, 42)
                self.assertFalse(identity.url.endswith("/"))

    def test_rejects_unsafe_or_ambiguous_pull_request_urls(self) -> None:
        invalid = (
            "http://github.com/acme/widgets/pull/1",
            "https://user@github.com/acme/widgets/pull/1",
            "https://github.com:443/acme/widgets/pull/1",
            "https://github.com/acme/widgets/pull/1?token=x",
            "https://github.com/acme/widgets/pull/1#discussion",
            "https://github.com/acme%2Fother/widgets/pull/1",
            "https://github.com/acme/widgets/pull/0",
            "https://github.com/acme/widgets/issues/1",
            "https://github.com/acme/widgets/pull/1\nignored",
            "\nhttps://github.com/acme/widgets/pull/1",
        )
        for url in invalid:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    parse_pull_request_url(url)

    def test_resolves_newest_matching_historical_tool_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-pr-session-") as base:
            root = Path(base)
            older = create_run_workspace(root, "older-run")
            newer = create_run_workspace(root, "newer-run")
            other = create_run_workspace(root, "other-run")
            _record_created_pr(older, "tool_result", "https://github.com/acme/widgets/pull/42")
            _record_created_pr(newer, "subagent_tool_result", "https://github.com/acme/widgets/pull/42")
            _record_created_pr(other, "tool_result", "https://github.com/acme/other/pull/42")
            os.utime(older.session_dir / "events.jsonl", (1, 1))
            os.utime(newer.session_dir / "events.jsonl", (2, 2))
            os.utime(other.session_dir / "events.jsonl", (3, 3))

            selected = resolve_session_from_pull_request(
                root, "https://github.com/acme/widgets/pull/42"
            )

        self.assertEqual(selected, "newer-run")

    def test_number_resolves_against_current_local_github_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-pr-session-") as base:
            root = Path(base)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "remote", "add", "origin", "git@github.com:acme/widgets.git"],
                check=True,
            )
            workspace = create_run_workspace(root, "linked-run")
            _record_created_pr(workspace, "tool_result", "https://github.com/acme/widgets/pull/42")

            selected = resolve_session_from_pull_request(root, "42")

        self.assertEqual(selected, "linked-run")

    def test_failed_and_malformed_tool_results_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-pr-session-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "bad-run")
            append_session_event(
                workspace.session_dir,
                "tool_result",
                {"name": "github_pr_create", "result": {"kind": "github_pr_create", "ok": False, "url": "https://github.com/acme/widgets/pull/1"}},
            )
            append_session_event(
                workspace.session_dir,
                "tool_result",
                {"name": "github_pr_create", "result": {"kind": "github_pr_create", "ok": True, "url": "not-a-url"}},
            )

            self.assertEqual(read_session_pull_requests(root, workspace.run_id), ())
            with self.assertRaisesRegex(ValueError, "No local session"):
                resolve_session_from_pull_request(root, "https://github.com/acme/widgets/pull/1")


def _record_created_pr(workspace, event_type: str, url: str) -> None:
    append_session_event(
        workspace.session_dir,
        event_type,
        {
            "name": "github_pr_create",
            "result": {
                "kind": "github_pr_create",
                "ok": True,
                "repository": "acme/widgets",
                "url": url,
            },
        },
    )


if __name__ == "__main__":
    unittest.main()
