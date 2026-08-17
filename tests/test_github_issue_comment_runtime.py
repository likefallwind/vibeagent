from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_approval_preview_keys import approval_preview_key
from vibeagent.github_issue_action_executor import execute_github_issue_action
from vibeagent.github_issue_comment_runtime import (
    create_github_issue_comment,
    preview_github_issue_comment,
)
from vibeagent.prompt_observations import format_observations
from vibeagent.types import (
    AssistantResponse,
    ChatMessage,
    CheckGitHubIssueCommentAction,
    CheckGitHubIssueCommentObservation,
    GitHubIssueCommentAction,
)
from vibeagent.workspace import create_run_workspace


class GitHubIssueCommentRuntimeTests(unittest.TestCase):
    def test_parser_approval_and_preview_key_preserve_exact_comment(self) -> None:
        action = parse_tool_action(
            "github_issue_comment",
            {"body": "Fixed in PR #43.", "issue": "42", "remote": "upstream"},
        )
        self.assertEqual(
            action,
            GitHubIssueCommentAction(
                type="github_issue_comment",
                body="Fixed in PR #43.",
                issue="42",
                remote="upstream",
            ),
        )
        request = build_approval_request(action)
        self.assertIsNotNone(request)
        self.assertEqual(request.action_type, "github_issue_comment")
        self.assertIn("42: Fixed in PR #43.", request.target)
        self.assertIn("issue_comment", request.risk)

        digest = hashlib.sha256(action.body.encode("utf-8")).hexdigest()
        observation = CheckGitHubIssueCommentObservation(
            kind="check_github_issue_comment",
            ok=True,
            repository="acme/widgets",
            selector="42",
            issue="42",
            remote="upstream",
            body_chars=len(action.body),
            body_sha256=digest,
            comment_target="42: Fixed in PR #43.",
            message="Ready.",
        )
        self.assertEqual(approval_preview_key(action), approval_preview_key(observation))
        changed_body = GitHubIssueCommentAction(
            type="github_issue_comment",
            body="Different result.",
            issue="42",
            remote="upstream",
        )
        changed_issue = GitHubIssueCommentAction(
            type="github_issue_comment",
            body=action.body,
            issue="43",
            remote="upstream",
        )
        self.assertNotEqual(approval_preview_key(changed_body), approval_preview_key(observation))
        self.assertNotEqual(approval_preview_key(changed_issue), approval_preview_key(observation))

    def test_parser_rejects_invalid_body_issue_and_remote(self) -> None:
        for payload in (
            {"body": "", "issue": "42"},
            {"body": "bad\x00body", "issue": "42"},
            {"body": "ok", "issue": "0"},
            {"body": "ok", "issue": "--web"},
            {"body": "ok", "issue": "42", "remote": "--repo"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ActionParseError):
                parse_tool_action("github_issue_comment", payload)

    def test_parser_rejects_private_key_material_before_preview(self) -> None:
        body = "-----BEGIN PRIVATE KEY-----\nnot-a-real-key"

        with self.assertRaises(ActionParseError) as raised:
            parse_tool_action("github_issue_comment", {"body": body, "issue": "42"})

        self.assertIn("sensitive credential material", str(raised.exception))
        self.assertNotIn(body, str(raised.exception))

    def test_preflight_is_local_and_returns_stable_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, log = self._fake_gh(root)
            with patch("vibeagent.github_issue_comment_runtime.shutil.which", return_value=str(gh)):
                result = preview_github_issue_comment(
                    workspace,
                    body="Status update",
                    issue="https://github.com/acme/widgets/issues/42/",
                    remote="origin",
                )

            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["repository"], "acme/widgets")
            self.assertEqual(result["selector"], "https://github.com/acme/widgets/issues/42")
            self.assertEqual(result["issue"], "https://github.com/acme/widgets/issues/42/")
            self.assertEqual(result["remote"], "origin")
            self.assertEqual(result["body_chars"], 13)
            self.assertFalse(log.exists(), "preflight must not invoke gh")

    def test_preflight_rejects_cross_repository_url_before_gh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, log = self._fake_gh(root)
            with patch("vibeagent.github_issue_comment_runtime.shutil.which", return_value=str(gh)):
                result = preview_github_issue_comment(
                    workspace,
                    body="Status update",
                    issue="https://github.com/other/widgets/issues/42",
                )
            self.assertFalse(result["ok"])
            self.assertIn("does not match local repository", result["message"])
            self.assertFalse(log.exists())

    def test_posts_issue_comment_without_shell_interpretation(self) -> None:
        body = "--not-an-option\n@literal $(touch should-not-run)"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, log = self._fake_gh(root)
            with patch("vibeagent.github_issue_comment_runtime.shutil.which", return_value=str(gh)):
                result = create_github_issue_comment(
                    workspace,
                    body=body,
                    issue="42",
                    remote="origin",
                )

            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["url"], "https://github.com/acme/widgets/issues/42#issuecomment-99")
            self.assertEqual(
                self._calls(log),
                [["issue", "comment", "42", "--repo", "acme/widgets", "--body", body]],
            )
            self.assertFalse((workspace.root / "should-not-run").exists())

    def test_action_executor_and_prompt_include_comment_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, _ = self._fake_gh(root)
            action = CheckGitHubIssueCommentAction(
                type="check_github_issue_comment",
                body="Ready for verification.",
                issue="42",
                remote="origin",
            )
            with patch("vibeagent.github_issue_comment_runtime.shutil.which", return_value=str(gh)):
                observation = execute_github_issue_action(workspace, action)

            self.assertIsInstance(observation, CheckGitHubIssueCommentObservation)
            self.assertTrue(observation.ok)
            prompt = format_observations([observation])
            self.assertIn("check_github_issue_comment", prompt)
            self.assertIn("issue: 42", prompt)
            self.assertIn("bodySha256:", prompt)

    def test_agent_denies_issue_comment_without_approval_handler(self) -> None:
        class Client:
            def complete(
                self,
                messages: list[ChatMessage],
                tools: list[dict] | None = None,
                max_tokens: int = 4096,
                temperature: float = 0.2,
                timeout_ms: int = 120_000,
            ) -> AssistantResponse:
                content = [
                    {
                        "type": "tool_call",
                        "id": "issue-comment",
                        "name": "github_issue_comment",
                        "input": {"issue": "42", "body": "Fixed."},
                    }
                ]
                return AssistantResponse(content=content, raw={"content": content})

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_agent(
                "post an issue update",
                base_dir=Path(temp_dir),
                client=Client(),
                max_iterations=1,
                tool_names=frozenset({"github_issue_comment"}),
            )
        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "github_issue_comment")

    def test_cli_permissions_lists_issue_comment_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [sys.executable, "-m", "vibeagent", "--cwd", temp_dir, "--permissions"],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("github_issue_comment", completed.stdout)

    def _workspace(self, root: Path):
        project = root / "project"
        project.mkdir()
        self._git(project, "init", "--initial-branch=main")
        self._git(project, "config", "user.name", "Test User")
        self._git(project, "config", "user.email", "test@example.com")
        (project / "README.md").write_text("base\n", encoding="utf-8")
        self._git(project, "add", "README.md")
        self._git(project, "commit", "-m", "base")
        self._git(project, "remote", "add", "origin", "git@github.com:acme/widgets.git")
        self._git(project, "config", "branch.main.remote", "origin")
        self._git(project, "config", "branch.main.merge", "refs/heads/main")
        return create_run_workspace(project, run_id="issue-comment-test")

    def _fake_gh(self, root: Path) -> tuple[Path, Path]:
        log = root / "gh-argv.jsonl"
        gh = root / "gh"
        gh.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"with open({str(log)!r}, 'a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "print('https://github.com/acme/widgets/issues/42#issuecomment-99')\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        return gh, log

    def _calls(self, log: Path) -> list[list[str]]:
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
