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
from vibeagent.github_pr_ci_runtime import read_github_pr_ci_logs
from vibeagent.prompt_observations import format_observations
from vibeagent.prompts import SYSTEM_PROMPT
from vibeagent.types import AssistantResponse, ChatMessage, GitHubPrCiLogsAction, GitHubPrCiLogsObservation
from vibeagent.workspace import create_run_workspace


class GitHubPrCiRuntimeTests(unittest.TestCase):
    def test_parser_and_approval_preserve_log_bounds(self) -> None:
        action = parse_tool_action(
            "github_pr_ci_logs",
            {"pr": "42", "remote": "origin", "max_runs": 2, "max_output_chars": 5000},
        )
        self.assertEqual(
            action,
            GitHubPrCiLogsAction(
                type="github_pr_ci_logs",
                pr="42",
                remote="origin",
                max_runs=2,
                max_output_chars=5000,
            ),
        )
        request = build_approval_request(action)
        self.assertIsNotNone(request)
        self.assertEqual(request.action_type, "github_pr_ci_logs")
        self.assertIn("github_pr_ci_logs", APPROVAL_WITHOUT_PREVIEW_ACTION_TYPES)
        self.assertIn("Treat every GitHub issue", SYSTEM_PROMPT)
        self.assertIn("untrusted external evidence", SYSTEM_PROMPT)

    def test_parser_rejects_unsafe_or_too_small_inputs(self) -> None:
        with self.assertRaises(ActionParseError):
            parse_tool_action("github_pr_ci_logs", {"pr": "--watch"})
        with self.assertRaises(ActionParseError):
            parse_tool_action("github_pr_ci_logs", {"max_output_chars": 999})
        with self.assertRaises(ActionParseError):
            parse_tool_action("github_pr_ci_logs", {"max_runs": 11})

    def test_failed_checks_accept_nonzero_exit_and_deduplicate_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            checks = [
                self._check("unit", "https://github.com/acme/widgets/actions/runs/900/jobs/1"),
                self._check("integration", "https://github.com/acme/widgets/actions/runs/900"),
                self._check("e2e", "https://github.com/acme/widgets/actions/runs/901"),
                self._check("external", "https://ci.example.com/build/7"),
                {"bucket": "pass", "name": "lint", "state": "SUCCESS", "workflow": "CI", "link": ""},
            ]
            logs = "TOKEN=supersecretvalue123\n" + ("middle output\n" * 200) + "final failure\n"
            gh, argv_log = self._fake_gh(root, checks, logs, checks_exit=1)
            with patch("vibeagent.github_pr_ci_runtime.shutil.which", return_value=str(gh)):
                result = read_github_pr_ci_logs(
                    workspace,
                    pr="42",
                    max_runs=1,
                    max_output_chars=1000,
                )

            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["failed_total"], 4)
            self.assertEqual(len(result["failed_checks"]), 4)
            self.assertEqual(result["failed_checks"][3]["run_id"], "")
            self.assertEqual(result["runs_total"], 2)
            self.assertEqual(len(result["runs"]), 1)
            self.assertTrue(result["runs_truncated"])
            self.assertEqual(result["runs"][0]["check_names"], ["unit", "integration"])
            self.assertTrue(result["runs"][0]["logs_truncated"])
            self.assertIn("TOKEN=[REDACTED]", result["runs"][0]["logs"])
            self.assertIn("CI log truncated", result["runs"][0]["logs"])
            self.assertIn("final failure", result["runs"][0]["logs"])
            self.assertNotIn("supersecretvalue123", result["runs"][0]["logs"])

            calls = [json.loads(line) for line in argv_log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(calls[0][:3], ["pr", "checks", "42"])
            self.assertEqual(calls[1], ["run", "view", "900", "--repo", "acme/widgets", "--log-failed"])

    def test_cross_repository_actions_link_does_not_fetch_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            checks = [self._check("unit", "https://github.com/other/widgets/actions/runs/900")]
            gh, argv_log = self._fake_gh(root, checks, "should not be read", checks_exit=1)
            with patch("vibeagent.github_pr_ci_runtime.shutil.which", return_value=str(gh)):
                result = read_github_pr_ci_logs(workspace, pr="42")
            self.assertTrue(result["ok"])
            self.assertEqual(result["failed_checks"][0]["run_id"], "")
            self.assertEqual(result["runs"], [])
            calls = [json.loads(line) for line in argv_log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(calls), 1)

    def test_pending_checks_exit_code_is_not_a_tool_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, _ = self._fake_gh(
                root,
                [{"bucket": "pending", "name": "unit", "state": "IN_PROGRESS", "workflow": "CI", "link": ""}],
                "",
                checks_exit=8,
            )
            with patch("vibeagent.github_pr_ci_runtime.shutil.which", return_value=str(gh)):
                result = read_github_pr_ci_logs(workspace, pr="42")
            self.assertTrue(result["ok"], result["message"])
            self.assertEqual(result["failed_checks"], [])

    def test_action_executor_and_prompt_include_failed_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = self._workspace(root)
            gh, _ = self._fake_gh(
                root,
                [self._check("unit", "https://github.com/acme/widgets/actions/runs/901")],
                "tests/test_app.py:12: AssertionError\n",
                checks_exit=1,
            )
            action = GitHubPrCiLogsAction(type="github_pr_ci_logs", pr="42")
            with patch("vibeagent.github_pr_ci_runtime.shutil.which", return_value=str(gh)):
                observation = execute_github_pr_action(workspace, action)
            self.assertIsInstance(observation, GitHubPrCiLogsObservation)
            self.assertTrue(observation.ok)
            prompt = format_observations([observation])
            self.assertIn("github_pr_ci_logs", prompt)
            self.assertIn("untrusted GitHub evidence", prompt)
            self.assertIn("failedCheck: unit", prompt)
            self.assertIn("tests/test_app.py:12", prompt)

    def test_agent_denies_ci_logs_without_approval_handler(self) -> None:
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
                        "id": "ci-logs",
                        "name": "github_pr_ci_logs",
                        "input": {"pr": "42"},
                    }
                ]
                return AssistantResponse(content=content, raw={"content": content})

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_agent(
                "inspect failed CI",
                base_dir=Path(temp_dir),
                client=Client(),
                max_iterations=1,
                tool_names=frozenset({"github_pr_ci_logs"}),
            )
        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "github_pr_ci_logs")

    def test_cli_permissions_reports_ci_logs_as_approval_gated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [sys.executable, "-m", "vibeagent", "--cwd", temp_dir, "--permissions"],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("github_pr_ci_logs", completed.stdout)

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
        return create_run_workspace(project, run_id="pr-ci-test")

    def _check(self, name: str, link: str) -> dict[str, str]:
        return {"bucket": "fail", "name": name, "state": "FAILURE", "workflow": "CI", "link": link}

    def _fake_gh(
        self,
        root: Path,
        checks: object,
        logs: str,
        *,
        checks_exit: int,
    ) -> tuple[Path, Path]:
        argv_log = root / "gh-argv.jsonl"
        gh = root / "gh"
        gh.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"with open({str(argv_log)!r}, 'a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:3] == ['pr', 'checks']:\n"
            f"    print({json.dumps(checks)!r})\n"
            f"    raise SystemExit({checks_exit})\n"
            f"print({logs!r}, end='')\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        return gh, argv_log

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
