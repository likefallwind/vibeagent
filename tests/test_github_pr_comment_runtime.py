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
from vibeagent.github_pr_action_executor import execute_github_pr_action
from vibeagent.github_pr_comment_runtime import create_github_pr_comment, preview_github_pr_comment
from vibeagent.prompt_observations import format_observations
from vibeagent.types import (
    AssistantResponse,
    ChatMessage,
    CheckGitHubPrCommentAction,
    CheckGitHubPrCommentObservation,
    GitHubPrCommentAction,
    GitHubPrCommentObservation,
)
from vibeagent.workspace import create_run_workspace


class GitHubPrCommentRuntimeTests(unittest.TestCase):
    def test_parser_approval_and_preview_key_preserve_comment_target(self) -> None:
        action = parse_tool_action(
            "github_pr_comment",
            {"body": "Handled the review.", "pr": "42", "remote": "upstream", "reply_to": 700},
        )
        self.assertEqual(
            action,
            GitHubPrCommentAction(
                type="github_pr_comment",
                body="Handled the review.",
                pr="42",
                remote="upstream",
                reply_to=700,
            ),
        )
        request = build_approval_request(action)
        self.assertIsNotNone(request)
        self.assertEqual(request.action_type, "github_pr_comment")
        self.assertIn("reply-to=700", request.target)
        self.assertIn("trigger notifications", request.risk)

        digest = hashlib.sha256(action.body.encode("utf-8")).hexdigest()
        observation = CheckGitHubPrCommentObservation(
            kind="check_github_pr_comment",
            ok=True,
            repository="acme/widgets",
            selector="42",
            pr="42",
            remote="upstream",
            reply_to=700,
            body_chars=len(action.body),
            body_sha256=digest,
            comment_target="42 reply-to=700: Handled the review.",
            message="Ready.",
        )
        self.assertEqual(approval_preview_key(action), approval_preview_key(observation))

    def test_parser_rejects_invalid_body_and_reply_id(self) -> None:
        for payload in (
            {"body": ""},
            {"body": "bad\x00body"},
            {"body": "ok", "reply_to": 0},
            {"body": "ok", "reply_to": True},
            {"body": "ok", "pr": "--web"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ActionParseError):
                parse_tool_action("github_pr_comment", payload)

    def test_preflight_is_local_and_exposes_stable_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, log = self._fake_gh(root)
            with patch("vibeagent.github_pr_comment_runtime.shutil.which", return_value=str(gh)):
                result = preview_github_pr_comment(
                    workspace,
                    body="Status update",
                    pr="42",
                    remote="origin",
                )

            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["repository"], "acme/widgets")
            self.assertEqual(result["selector"], "42")
            self.assertEqual(result["pr"], "42")
            self.assertEqual(result["remote"], "origin")
            self.assertEqual(result["body_chars"], 13)
            self.assertFalse(log.exists(), "preflight must not invoke gh")

    def test_posts_discussion_comment_without_shell_interpretation(self) -> None:
        body = "--not-an-option\n@literal $(touch should-not-run)"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, log = self._fake_gh(root)
            with patch("vibeagent.github_pr_comment_runtime.shutil.which", return_value=str(gh)):
                result = create_github_pr_comment(workspace, body=body, pr="42", remote="origin")

            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["url"], "https://github.com/acme/widgets/pull/42#issuecomment-99")
            calls = self._calls(log)
            self.assertEqual(calls, [["pr", "comment", "42", "--repo", "acme/widgets", "--body", body]])
            self.assertFalse((workspace.root / "should-not-run").exists())

    def test_replies_to_inline_review_comment_by_id(self) -> None:
        body = "Fixed in the latest commit."
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, log = self._fake_gh(root)
            with patch("vibeagent.github_pr_comment_runtime.shutil.which", return_value=str(gh)):
                result = create_github_pr_comment(
                    workspace,
                    body=body,
                    pr="42",
                    remote="origin",
                    reply_to=700,
                )

            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["url"], "https://github.com/acme/widgets/pull/42#discussion_r99")
            calls = self._calls(log)
            self.assertEqual(calls[0], ["pr", "view", "42", "--repo", "acme/widgets", "--json", "number"])
            self.assertEqual(
                calls[1],
                [
                    "api",
                    "--method",
                    "POST",
                    "repos/acme/widgets/pulls/42/comments/700/replies",
                    "--raw-field",
                    f"body={body}",
                ],
            )

    def test_action_executor_and_prompt_include_reply_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, _ = self._fake_gh(root)
            action = CheckGitHubPrCommentAction(
                type="check_github_pr_comment",
                body="Ready to merge.",
                pr="42",
                remote="origin",
                reply_to=700,
            )
            with patch("vibeagent.github_pr_comment_runtime.shutil.which", return_value=str(gh)):
                observation = execute_github_pr_action(workspace, action)

            self.assertIsInstance(observation, CheckGitHubPrCommentObservation)
            self.assertTrue(observation.ok)
            self.assertEqual(observation.reply_to, 700)
            prompt = format_observations([observation])
            self.assertIn("check_github_pr_comment", prompt)
            self.assertIn("replyTo: 700", prompt)
            self.assertIn("bodySha256:", prompt)

    def test_agent_denies_comment_without_approval_handler(self) -> None:
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
                        "id": "pr-comment",
                        "name": "github_pr_comment",
                        "input": {"pr": "42", "body": "Done."},
                    }
                ]
                return AssistantResponse(content=content, raw={"content": content})

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_agent(
                "post a PR update",
                base_dir=Path(temp_dir),
                client=Client(),
                max_iterations=1,
                tool_names=frozenset({"github_pr_comment"}),
            )
        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "github_pr_comment")

    def test_cli_permissions_lists_comment_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [sys.executable, "-m", "vibeagent", "--cwd", temp_dir, "--permissions"],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("github_pr_comment", completed.stdout)

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
        return create_run_workspace(project, run_id="pr-comment-test")

    def _fake_gh(self, root: Path) -> tuple[Path, Path]:
        log = root / "gh-argv.jsonl"
        gh = root / "gh"
        gh.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"with open({str(log)!r}, 'a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:3] == ['pr', 'view']:\n"
            "    print(json.dumps({'number': 42}))\n"
            "elif sys.argv[1] == 'api':\n"
            "    print(json.dumps({'html_url': 'https://github.com/acme/widgets/pull/42#discussion_r99'}))\n"
            "else:\n"
            "    print('https://github.com/acme/widgets/pull/42#issuecomment-99')\n",
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
