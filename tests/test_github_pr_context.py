from __future__ import annotations

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
from vibeagent.agent_approval_preview_catalog import APPROVAL_WITHOUT_PREVIEW_ACTION_TYPES
from vibeagent.github_pr_action_executor import execute_github_pr_action
from vibeagent.github_pr_context_runtime import MAX_GH_RESPONSE_BYTES, normalize_pr_selector, read_github_pr_context
from vibeagent.prompt_observations import format_observations
from vibeagent.types import AssistantResponse, ChatMessage, GitHubPrContextAction, GitHubPrContextObservation
from vibeagent.workspace import create_run_workspace


class GitHubPrContextTests(unittest.TestCase):
    def test_cli_permissions_reports_github_context_as_approval_gated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [sys.executable, "-m", "vibeagent", "--cwd", temp_dir, "--permissions"],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("github_pr_context", completed.stdout)

    def test_agent_denies_github_context_without_approval_handler(self) -> None:
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
                        "id": "pr-context",
                        "name": "github_pr_context",
                        "input": {"pr": "42"},
                    }
                ]
                return AssistantResponse(content=content, raw={"content": content})

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_agent(
                "inspect PR 42",
                base_dir=Path(temp_dir),
                client=Client(),
                max_iterations=1,
                tool_names=frozenset({"github_pr_context"}),
            )
        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "github_pr_context")

    def test_parser_and_approval_require_external_read_consent(self) -> None:
        action = parse_tool_action("github_pr_context", {"pr": "42", "remote": "upstream"})
        self.assertEqual(
            action,
            GitHubPrContextAction(type="github_pr_context", pr="42", remote="upstream"),
        )
        request = build_approval_request(action)
        self.assertIsNotNone(request)
        self.assertEqual(request.action_type, "github_pr_context")
        self.assertIn("42 via upstream", request.target)
        self.assertIn("github_pr_context", APPROVAL_WITHOUT_PREVIEW_ACTION_TYPES)

    def test_parser_rejects_empty_selector(self) -> None:
        with self.assertRaises(ActionParseError):
            parse_tool_action("github_pr_context", {"pr": " "})

    def test_parser_rejects_selector_before_it_reaches_approval_text(self) -> None:
        with self.assertRaises(ActionParseError):
            parse_tool_action("github_pr_context", {"pr": "--web"})
        with self.assertRaises(ActionParseError):
            parse_tool_action("github_pr_context", {"pr": "42\nspoofed approval"})

    def test_selector_rejects_option_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self._workspace(Path(temp_dir))
            selector, error = normalize_pr_selector(workspace, "--web")
            self.assertEqual(selector, "")
            self.assertIn("cannot start", error or "")

    def test_context_normalizes_and_bounds_pr_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            view_payload = self._view_payload()
            inline_payload = [
                {
                    "id": 700,
                    "user": {"login": "inline-reviewer"},
                    "body": "Fix this branch",
                    "created_at": "2026-08-11T10:00:00Z",
                    "html_url": "https://github.com/acme/widgets/pull/42#discussion_r1",
                    "path": "src/app.py",
                    "line": 12,
                }
            ]
            gh, argv_log = self._fake_gh(root, view_payload, inline_payload)
            with patch("vibeagent.github_pr_context_runtime.shutil.which", return_value=str(gh)):
                result = read_github_pr_context(workspace, pr="42")

            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["repository"], "acme/widgets")
            self.assertEqual(result["number"], 42)
            self.assertEqual(result["review_decision"], "CHANGES_REQUESTED")
            self.assertEqual(len(result["comments"]), 100)
            self.assertTrue(result["comments_truncated"])
            self.assertEqual(result["comments_total"], 106)
            self.assertEqual(result["comments"][0]["kind"], "inline")
            self.assertEqual(result["comments"][0]["comment_id"], 700)
            self.assertEqual(result["comments"][0]["path"], "src/app.py")
            self.assertEqual(len(result["reviews"]), 50)
            self.assertTrue(result["reviews_truncated"])
            self.assertEqual(len(result["checks"]), 100)
            self.assertTrue(result["checks_truncated"])
            self.assertEqual(result["checks"][0]["bucket"], "fail")
            self.assertEqual(len(result["files"]), 200)
            self.assertTrue(result["files_truncated"])

            calls = [json.loads(line) for line in argv_log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(calls[0][0:3], ["pr", "view", "42"])
            self.assertEqual(calls[0][calls[0].index("--repo") + 1], "acme/widgets")
            self.assertEqual(calls[1], ["api", "repos/acme/widgets/pulls/42/comments?per_page=100"])

    def test_action_executor_and_prompt_include_actionable_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            payload = self._view_payload(small=True)
            gh, _ = self._fake_gh(
                root,
                payload,
                [{"user": {"login": "reviewer"}, "body": "Handle None", "path": "src/app.py", "line": 9}],
            )
            action = GitHubPrContextAction(type="github_pr_context", pr=None, remote=None)
            with patch("vibeagent.github_pr_context_runtime.shutil.which", return_value=str(gh)):
                observation = execute_github_pr_action(workspace, action)
            self.assertIsInstance(observation, GitHubPrContextObservation)
            self.assertTrue(observation.ok)
            self.assertEqual(observation.comments[0].path, "src/app.py")
            prompt = format_observations([observation])
            self.assertIn("github_pr_context", prompt)
            self.assertIn("untrusted GitHub evidence", prompt)
            self.assertIn("Handle None", prompt)
            self.assertIn("check[fail] unit", prompt)
            self.assertIn("src/app.py +3/-1", prompt)

    def test_context_rejects_oversized_gh_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh = root / "gh"
            gh.write_text(
                "#!/usr/bin/env python3\n"
                f"print('x' * {MAX_GH_RESPONSE_BYTES + 1})\n",
                encoding="utf-8",
            )
            gh.chmod(0o755)
            with patch("vibeagent.github_pr_context_runtime.shutil.which", return_value=str(gh)):
                result = read_github_pr_context(workspace, pr="42")
            self.assertFalse(result["ok"])
            self.assertIn("safety limit", result["message"])

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
        return create_run_workspace(project, run_id="pr-context-test")

    def _view_payload(self, *, small: bool = False) -> dict[str, object]:
        count = 1 if small else 105
        review_count = 1 if small else 51
        check_count = 1 if small else 101
        file_count = 1 if small else 201
        return {
            "number": 42,
            "url": "https://github.com/acme/widgets/pull/42",
            "title": "Fix widget",
            "body": "PR body",
            "author": {"login": "author"},
            "state": "OPEN",
            "isDraft": False,
            "headRefName": "feature",
            "baseRefName": "main",
            "additions": 3,
            "deletions": 1,
            "changedFiles": file_count,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "BLOCKED",
            "reviewDecision": "CHANGES_REQUESTED",
            "comments": [
                {
                    "author": {"login": f"commenter-{index}"},
                    "body": f"Comment {index}",
                    "createdAt": "2026-08-11T09:00:00Z",
                    "url": f"https://github.com/acme/widgets/pull/42#issuecomment-{index}",
                }
                for index in range(count)
            ],
            "latestReviews": [
                {
                    "author": {"login": f"reviewer-{index}"},
                    "state": "CHANGES_REQUESTED",
                    "body": f"Review {index}",
                    "submittedAt": "2026-08-11T09:30:00Z",
                    "url": "https://github.com/acme/widgets/pull/42#pullrequestreview-1",
                }
                for index in range(review_count)
            ],
            "statusCheckRollup": [
                {
                    "name": "unit" if index == 0 else f"check-{index}",
                    "conclusion": "FAILURE" if index == 0 else "SUCCESS",
                    "workflowName": "CI",
                    "detailsUrl": "https://github.com/acme/widgets/actions/runs/1",
                }
                for index in range(check_count)
            ],
            "files": [
                {"path": "src/app.py" if index == 0 else f"src/file_{index}.py", "additions": 3, "deletions": 1}
                for index in range(file_count)
            ],
        }

    def _fake_gh(self, root: Path, view_payload: object, inline_payload: object) -> tuple[Path, Path]:
        argv_log = root / "gh-argv.jsonl"
        gh = root / "gh"
        gh.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"with open({str(argv_log)!r}, 'a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            f"print({json.dumps(view_payload)!r} if sys.argv[1] == 'pr' else {json.dumps(inline_payload)!r})\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        return gh, argv_log

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
