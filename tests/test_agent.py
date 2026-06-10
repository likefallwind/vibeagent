import tempfile
import unittest
import json
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent import run_agent
from vibeagent.types import ApprovalDecision, ApprovalRequest, AssistantResponse, ChatMessage, ContentBlock, ModelUsage


class MockClient:
    def __init__(self, responses: list[list[ContentBlock]], usages: list[ModelUsage | None] | None = None) -> None:
        self.responses = responses
        self.usages = usages or []
        self.index = 0
        self.messages: list[list[ChatMessage]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AssistantResponse:
        self.messages.append(list(messages))
        response = self.responses[self.index]
        usage = self.usages[self.index] if self.index < len(self.usages) else None
        self.index += 1
        return AssistantResponse(content=response, raw={"content": response}, usage=usage)


def approve_all(_request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def deny_all(_request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(approved=False, message="denied")


class AgentTests(unittest.TestCase):
    def test_run_agent_allows_plain_text_response_without_tool_call(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient([[{"type": "text", "text": "这个问题不需要访问工作区。"}]])

            result = run_agent("解释一下递归", base_dir=Path(base), client=client, max_iterations=1)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "这个问题不需要访问工作区。")
        self.assertEqual(result.observations, [])

    def test_run_agent_includes_prior_context_and_records_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient([[{"type": "text", "text": "继续处理。"}]])

            result = run_agent(
                "继续上次任务",
                base_dir=Path(base),
                client=client,
                max_iterations=1,
                prior_context="session: old-run\nfinal: Added tests.",
            )
            events_path = Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        first_user = client.messages[0][1].content
        self.assertIsInstance(first_user, str)
        self.assertIn("Previous session context:", first_user)
        self.assertIn("final: Added tests.", first_user)
        self.assertEqual(rows[0]["type"], "task")
        self.assertEqual(rows[0]["task"], "继续上次任务")
        self.assertIn("old-run", rows[0]["prior_context"])

    def test_run_agent_records_model_token_usage_without_raw_response_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [[{"type": "text", "text": "完成。"}]],
                usages=[ModelUsage(input_tokens=12, output_tokens=4, total_tokens=16, cache_read_tokens=2)],
            )

            result = run_agent("记录 usage", base_dir=Path(base), client=client, max_iterations=1)
            events_path = Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        model_rows = [row for row in rows if row["type"] == "model"]
        self.assertEqual(model_rows[0]["usage"]["input_tokens"], 12)
        self.assertEqual(model_rows[0]["usage"]["output_tokens"], 4)
        self.assertEqual(model_rows[0]["usage"]["total_tokens"], 16)
        self.assertEqual(model_rows[0]["usage"]["cache_read_tokens"], 2)
        self.assertNotIn("raw", model_rows[0])

    def test_run_agent_includes_agents_md_in_initial_prompt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "AGENTS.md").write_text("Prefer unittest for tests.\n", encoding="utf-8")
            client = MockClient([[{"type": "text", "text": "知道了。"}]])

            result = run_agent("检查项目约定", base_dir=Path(base), client=client, max_iterations=1)

        first_user = client.messages[0][1].content
        self.assertTrue(result.success)
        self.assertIsInstance(first_user, str)
        self.assertIn("Project instructions from AGENTS.md files:", first_user)
        self.assertIn("Scope: .", first_user)
        self.assertIn("Prefer unittest for tests.", first_user)

    def test_run_agent_includes_project_command_hints_in_initial_prompt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text(
                '{"scripts":{"test":"python3 -m unittest discover -s tests"}}',
                encoding="utf-8",
            )
            client = MockClient([[{"type": "text", "text": "知道了。"}]])

            result = run_agent("运行测试", base_dir=Path(base), client=client, max_iterations=1)

        first_user = client.messages[0][1].content
        self.assertTrue(result.success)
        self.assertIsInstance(first_user, str)
        self.assertIn("Project command hints:", first_user)
        self.assertIn("pass the listed Cwd as the command cwd", first_user)
        self.assertIn("Cwd: .", first_user)
        self.assertIn("- npm run test [available=", first_user)
        self.assertIn(": python3 -m unittest discover -s tests", first_user)

    def test_run_agent_repairs_a_failing_script_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "sum.py", "content": "print(total)"}}],
                    [{"type": "tool_call", "id": "2", "name": "run_command", "input": {"command": "python3 sum.py"}}],
                    [
                        {
                            "type": "tool_call",
                            "id": "3",
                            "name": "write_file",
                            "input": {"path": "sum.py", "content": "total = sum(range(1, 101))\nprint(total)\n"},
                        }
                    ],
                    [{"type": "tool_call", "id": "4", "name": "run_command", "input": {"command": "python3 sum.py"}}],
                    [
                        {
                            "type": "tool_call",
                            "id": "5",
                            "name": "finish",
                            "input": {"message": "Generated and ran sum.py successfully."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "sum 1 to 100",
                base_dir=Path(base),
                client=client,
                max_iterations=5,
                approval_handler=approve_all,
            )
            event_log_exists = (Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl").is_file()

        self.assertTrue(result.success)
        self.assertEqual(result.run_dir, Path(base).resolve())
        self.assertTrue(event_log_exists)
        command_observations = [item for item in result.observations if item.kind == "run_command"]
        self.assertEqual(len(command_observations), 2)
        self.assertNotEqual(command_observations[0].result.exit_code, 0)
        self.assertEqual(command_observations[1].result.exit_code, 0)
        self.assertEqual(command_observations[1].result.stdout.strip(), "5050")
        self.assertEqual(client.messages[1][-1].role, "user")
        self.assertEqual(client.messages[1][-1].content[0]["type"], "tool_result")
        self.assertEqual([step.status for step in result.steps], ["completed", "failed", "completed", "completed", "completed"])

    def test_run_agent_executes_multiple_tool_calls_in_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "write_file",
                            "input": {"path": "hello.txt", "content": "hello\n"},
                        },
                        {
                            "type": "tool_call",
                            "id": "2",
                            "name": "run_command",
                            "input": {"command": "cat hello.txt", "timeout_ms": 1000, "max_output_chars": 1000},
                        },
                    ],
                    [
                        {
                            "type": "tool_call",
                            "id": "3",
                            "name": "finish",
                            "input": {"message": "Wrote and checked hello.txt."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "write hello",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )

        self.assertTrue(result.success)
        self.assertEqual([item.kind for item in result.observations], ["write_file", "run_command", "finish"])
        self.assertEqual(result.observations[1].result.stdout, "hello\n")
        self.assertEqual(result.observations[1].result.timeout_ms, 1000)
        self.assertEqual(result.observations[1].result.cwd, ".")
        self.assertFalse(result.observations[1].result.stdout_truncated)
        command_payload = json.loads(client.messages[1][-1].content[1]["content"])
        self.assertEqual(command_payload["result"]["timeout_ms"], 1000)
        self.assertEqual(command_payload["result"]["cwd"], ".")
        self.assertEqual(command_payload["result"]["max_output_chars"], 1000)
        self.assertFalse(command_payload["result"]["stdout_truncated"])
        self.assertEqual([step.status for step in result.steps], ["completed", "completed", "completed"])

    def test_run_agent_runs_command_in_project_relative_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            pkg = Path(base, "pkg")
            pkg.mkdir()
            Path(pkg, "hello.txt").write_text("hello\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "run_command",
                            "input": {"command": "cat hello.txt", "cwd": "pkg"},
                        }
                    ],
                    [{"type": "text", "text": "Checked package file."}],
                ]
            )

            result = run_agent(
                "check package file",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "run_command")
        self.assertEqual(result.observations[0].result.stdout, "hello\n")
        self.assertEqual(result.observations[0].result.cwd, "pkg")
        self.assertEqual(payload["result"]["cwd"], "pkg")
        self.assertEqual(result.steps[0].target, "cat hello.txt (cwd: pkg)")

    def test_run_agent_tracks_latest_model_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "update_plan",
                            "input": {
                                "plan": [
                                    {"step": "Inspect files", "status": "in_progress"},
                                    {"step": "Run tests", "status": "pending"},
                                ]
                            },
                        }
                    ],
                    [
                        {
                            "type": "tool_call",
                            "id": "2",
                            "name": "update_plan",
                            "input": {
                                "plan": [
                                    {"step": "Inspect files", "status": "completed"},
                                    {"step": "Run tests", "status": "in_progress"},
                                ]
                            },
                        }
                    ],
                    [{"type": "text", "text": "Plan is current."}],
                ]
            )

            result = run_agent("make a plan", base_dir=Path(base), client=client, max_iterations=3)
            events_path = Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Plan is current.")
        self.assertEqual([item.status for item in result.plan], ["completed", "in_progress"])
        self.assertEqual([item.step for item in result.plan], ["Inspect files", "Run tests"])
        self.assertEqual([item.kind for item in result.observations], ["update_plan", "update_plan"])
        self.assertEqual([step.action_type for step in result.steps], ["update_plan", "update_plan"])
        self.assertIn("update_plan", [event.get("name") for event in events if event["type"] == "tool_call"])

    def test_run_agent_returns_blocked_command_as_tool_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "run_command",
                            "input": {"command": "sudo reboot"},
                        }
                    ],
                    [
                        {
                            "type": "tool_call",
                            "id": "2",
                            "name": "finish",
                            "input": {"message": "Blocked the dangerous command."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "try dangerous command",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )

        self.assertTrue(result.success)
        self.assertIsNone(result.observations[0].result.exit_code)
        self.assertIn("Command blocked", result.observations[0].result.stderr)
        self.assertIn("Command blocked", client.messages[1][-1].content[0]["content"])
        self.assertEqual(result.steps[0].status, "failed")

    def test_run_agent_allows_git_status_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_status", "input": {}}],
                    [{"type": "tool_call", "id": "2", "name": "finish", "input": {"message": "Checked git status."}}],
                ]
            )

            result = run_agent("check git", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_status")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_git_info_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_info", "input": {}}],
                    [{"type": "tool_call", "id": "2", "name": "finish", "input": {"message": "Checked git info."}}],
                ]
            )

            result = run_agent("check git info", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_info")
        self.assertTrue(result.observations[0].ok)
        self.assertTrue(result.observations[0].head)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_git_branches_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "branch", "feature/demo"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_branches", "input": {"max_branches": 10}}],
                    [{"type": "text", "text": "Listed branches."}],
                ]
            )

            result = run_agent("list branches", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_branches")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].current, "main")
        self.assertIn("feature/demo", [branch.name for branch in result.observations[0].branches])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_switch_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_switch", "input": {"branch": "feature/new", "create": True}}],
                    [{"type": "text", "text": "Previewed switch."}],
                ]
            )

            result = run_agent("check branch switch", base_dir=Path(base), client=client, max_iterations=2)
            current = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()

        self.assertTrue(result.success)
        self.assertEqual(current, "main")
        self.assertEqual(result.observations[0].kind, "check_git_switch")
        self.assertTrue(result.observations[0].ok)
        self.assertFalse(result.observations[0].branch_exists)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_fetch_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            remote = Path(base, "remote.git")
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_fetch", "input": {}}],
                    [{"type": "text", "text": "Checked fetch."}],
                ]
            )

            result = run_agent("check fetch", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_git_fetch")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].remote, "origin")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_pull_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base, "repo")
            root.mkdir()
            remote = Path(base, "remote.git")
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(root, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_pull", "input": {}}],
                    [{"type": "text", "text": "Checked pull."}],
                ]
            )

            result = run_agent("check pull", base_dir=root, client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_git_pull")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].upstream, "origin/main")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_push_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base, "repo")
            root.mkdir()
            remote = Path(base, "remote.git")
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(root, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(root, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "local update"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_push", "input": {}}],
                    [{"type": "text", "text": "Checked push."}],
                ]
            )

            result = run_agent("check push", base_dir=root, client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_git_push")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].upstream, "origin/main")
        self.assertEqual(result.observations[0].ahead, 1)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_restore_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_restore", "input": {"paths": ["app.py"]}}],
                    [{"type": "text", "text": "Checked restore."}],
                ]
            )

            result = run_agent("check restore", base_dir=Path(base), client=client, max_iterations=2)
            content_after = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content_after, "print('new')\n")
        self.assertEqual(result.observations[0].kind, "check_git_restore")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+print('new')", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_stash_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_stash", "input": {"message": "save work"}}],
                    [{"type": "text", "text": "Checked stash."}],
                ]
            )

            result = run_agent("check stash", base_dir=Path(base), client=client, max_iterations=2)
            content_after = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content_after, "print('new')\n")
        self.assertEqual(result.observations[0].kind, "check_git_stash")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+print('new')", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_stash_apply_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save work", "--", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_stash_apply", "input": {"stash_ref": "stash@{0}"}}],
                    [{"type": "text", "text": "Checked stash apply."}],
                ]
            )

            result = run_agent("check stash apply", base_dir=Path(base), client=client, max_iterations=2)
            content_after = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content_after, "print('old')\n")
        self.assertEqual(result.observations[0].kind, "check_git_stash_apply")
        self.assertTrue(result.observations[0].ok)
        self.assertTrue(result.observations[0].worktree_clean)
        self.assertIn("+print('new')", result.observations[0].patch)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_stash_drop_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save work", "--", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_stash_drop", "input": {"stash_ref": "stash@{0}"}}],
                    [{"type": "text", "text": "Checked stash drop."}],
                ]
            )

            result = run_agent("check stash drop", base_dir=Path(base), client=client, max_iterations=2)
            stash_list = subprocess.run(["git", "stash", "list"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout

        self.assertTrue(result.success)
        self.assertIn("save work", stash_list)
        self.assertEqual(result.observations[0].kind, "check_git_stash_drop")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+print('new')", result.observations[0].patch)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_git_blame_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "git_blame",
                            "input": {"path": "app.py", "start_line": 1, "line_count": 1},
                        }
                    ],
                    [{"type": "text", "text": "Checked git blame."}],
                ]
            )

            result = run_agent("check blame", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_blame")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("print('ok')", result.observations[0].blame)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_git_changes_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_changes", "input": {}}],
                    [{"type": "text", "text": "Read changed files."}],
                ]
            )

            result = run_agent("summarize changes", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_changes")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].files[0].path, "app.py")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_review_changes_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "review_changes", "input": {}}],
                    [{"type": "text", "text": "Reviewed changed files."}],
                ]
            )

            result = run_agent("review changes", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "review_changes")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].files[0].path, "app.py")
        self.assertEqual(result.observations[0].diff_hunks_total, 1)
        self.assertEqual(result.observations[0].diff_hunks[0].file, "app.py")
        self.assertEqual(result.observations[0].untracked_previews_total, 0)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_suggest_checks_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts":{"test":"node test.js"}}', encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "suggest_checks", "input": {}}],
                    [{"type": "text", "text": "Suggested checks."}],
                ]
            )

            result = run_agent("suggest checks", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "suggest_checks")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].checks[0].command, "npm run test")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_project_commands_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts":{"test":"node test.js"}}', encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "project_commands", "input": {}}],
                    [{"type": "text", "text": "Listed commands."}],
                ]
            )

            result = run_agent("list project commands", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "project_commands")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].commands[0].command, "npm run test")
        self.assertEqual(payload["kind"], "project_commands")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_project_manifests_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"name":"web","dependencies":{"react":"^19.0.0"}}', encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "project_manifests", "input": {}}],
                    [{"type": "text", "text": "Read manifests."}],
                ]
            )

            result = run_agent("read manifests", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "project_manifests")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].manifests[0].items[0].name, "react")
        self.assertEqual(payload["kind"], "project_manifests")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_environment_info_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "environment_info", "input": {}}],
                    [{"type": "text", "text": "Read environment info."}],
                ]
            )

            result = run_agent("inspect environment", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "environment_info")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("python", [tool.name for tool in result.observations[0].tools])
        self.assertEqual(payload["kind"], "environment_info")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_command_check_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "command_check",
                            "input": {"command": "sudo reboot"},
                        }
                    ],
                    [{"type": "text", "text": "Preflighted command."}],
                ]
            )

            result = run_agent("preflight command", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "command_check")
        self.assertFalse(result.observations[0].ok)
        self.assertTrue(result.observations[0].blocked)
        self.assertEqual(payload["kind"], "command_check")
        self.assertEqual(result.steps[0].status, "failed")

    def test_run_agent_allows_check_run_commands_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_run_commands",
                            "input": {
                                "commands": [
                                    {"command": "python3 --version"},
                                    {"command": "sudo reboot"},
                                ]
                            },
                        }
                    ],
                    [{"type": "text", "text": "Preflighted commands."}],
                ]
            )

            result = run_agent("preflight commands", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_run_commands")
        self.assertFalse(result.observations[0].ok)
        self.assertEqual(len(result.observations[0].checks), 2)
        self.assertEqual(payload["kind"], "check_run_commands")
        self.assertEqual(result.steps[0].status, "failed")

    def test_run_agent_denies_run_commands_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            marker = Path(base, "marker.txt")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "run_commands",
                            "input": {
                                "commands": [
                                    {"command": "python3 -c \"from pathlib import Path; Path('marker.txt').write_text('ran')\""}
                                ]
                            },
                        }
                    ]
                ]
            )

            result = run_agent("run commands", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertFalse(marker.exists())
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "run_commands")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_start_command_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_start_command",
                            "input": {"command": "python3 -m http.server", "cwd": "."},
                        }
                    ],
                    [{"type": "text", "text": "Preflighted start command."}],
                ]
            )

            result = run_agent("preflight dev server", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_start_command")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(payload["kind"], "check_start_command")
        self.assertEqual(payload["command"], "python3 -m http.server")
        self.assertEqual(result.steps[0].status, "completed")
        self.assertEqual(result.steps[0].target, "python3 -m http.server (cwd: .)")

    def test_run_agent_allows_port_check_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "port_check",
                            "input": {"host": "127.0.0.1", "port": 9, "timeout_ms": 100},
                        }
                    ],
                    [{"type": "text", "text": "Checked port."}],
                ]
            )

            with patch("vibeagent.actions.socket.create_connection", side_effect=ConnectionRefusedError("refused")):
                result = run_agent("check port", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "port_check")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(payload["kind"], "port_check")
        self.assertEqual(payload["host"], "127.0.0.1")
        self.assertEqual(payload["port"], 9)
        self.assertEqual(result.steps[0].status, "completed")
        self.assertEqual(result.steps[0].target, "127.0.0.1:9")

    def test_run_agent_allows_http_check_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "http_check",
                            "input": {"url": "http://127.0.0.1:8000/health", "timeout_ms": 100},
                        }
                    ],
                    [{"type": "text", "text": "Checked HTTP."}],
                ]
            )

            with patch("vibeagent.actions.urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
                result = run_agent("check http", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "http_check")
        self.assertTrue(result.observations[0].ok)
        self.assertFalse(result.observations[0].reachable)
        self.assertEqual(payload["kind"], "http_check")
        self.assertEqual(payload["url"], "http://127.0.0.1:8000/health")
        self.assertEqual(result.steps[0].status, "completed")
        self.assertEqual(result.steps[0].target, "http://127.0.0.1:8000/health")

    def test_run_agent_allows_check_stop_process_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_stop_process",
                            "input": {"process_id": "missing"},
                        }
                    ],
                    [{"type": "text", "text": "Checked process id."}],
                ]
            )

            result = run_agent("check process id", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_stop_process")
        self.assertFalse(result.observations[0].ok)
        self.assertEqual(payload["kind"], "check_stop_process")
        self.assertEqual(payload["process_id"], "missing")
        self.assertEqual(result.steps[0].status, "failed")
        self.assertEqual(result.steps[0].target, "missing")

    def test_run_agent_allows_check_stop_all_processes_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_stop_all_processes", "input": {}}],
                    [{"type": "text", "text": "Checked all process ids."}],
                ]
            )

            result = run_agent("check all process ids", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_stop_all_processes")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(payload["kind"], "check_stop_all_processes")
        self.assertEqual(result.steps[0].status, "completed")
        self.assertEqual(result.steps[0].target, "background processes")

    def test_run_agent_allows_wait_process_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "wait_process",
                            "input": {
                                "process_id": "missing",
                                "timeout_ms": 100,
                                "stdout_contains": "READY",
                                "max_output_chars": 1000,
                            },
                        }
                    ],
                    [{"type": "text", "text": "Checked process completion."}],
                ]
            )

            result = run_agent("wait process id", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "wait_process")
        self.assertFalse(result.observations[0].ok)
        self.assertEqual(result.observations[0].timeout_ms, 100)
        self.assertEqual(result.observations[0].max_output_chars, 1000)
        self.assertFalse(result.observations[0].matched)
        self.assertEqual(payload["kind"], "wait_process")
        self.assertEqual(payload["process_id"], "missing")
        self.assertEqual(payload["max_output_chars"], 1000)
        self.assertFalse(payload["matched"])
        self.assertEqual(result.steps[0].status, "failed")
        self.assertEqual(result.steps[0].target, "missing")

    def test_run_agent_allows_check_write_process_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_write_process",
                            "input": {"process_id": "missing", "content": "hello\n"},
                        }
                    ],
                    [{"type": "text", "text": "Checked process input."}],
                ]
            )

            result = run_agent("check process input", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "check_write_process")
        self.assertFalse(result.observations[0].ok)
        self.assertEqual(result.observations[0].content_chars, 6)
        self.assertEqual(payload["kind"], "check_write_process")
        self.assertEqual(payload["process_id"], "missing")
        self.assertEqual(result.steps[0].status, "failed")
        self.assertEqual(result.steps[0].target, "missing (6 chars)")

    def test_run_agent_denies_write_process_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "write_process",
                            "input": {"process_id": "abc123", "content": "hello\n"},
                        }
                    ]
                ]
            )

            result = run_agent("write process input", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "write_process")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_git_log_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_log", "input": {"max_count": 1}}],
                    [{"type": "text", "text": "Read recent history."}],
                ]
            )

            result = run_agent("read history", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_log")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("initial", result.observations[0].log)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_git_diff_hunks_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\nprint('extra')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_diff_hunks", "input": {"path": "app.py"}}],
                    [{"type": "text", "text": "Read diff hunks."}],
                ]
            )

            result = run_agent("read diff hunks", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_diff_hunks")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].hunks[0].file, "app.py")
        self.assertEqual(payload["kind"], "git_diff_hunks")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_git_show_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_show", "input": {"rev": "HEAD", "path": "app.py"}}],
                    [{"type": "text", "text": "Read commit details."}],
                ]
            )

            result = run_agent("read commit details", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "git_show")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("initial", result.observations[0].output)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_session_summary_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "session_summary", "input": {}}],
                    [{"type": "text", "text": "Read session summary."}],
                ]
            )

            result = run_agent("read session summary", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "session_summary")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("Session:", result.observations[0].summary)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_glob_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "glob", "input": {"pattern": "*.py"}}],
                    [{"type": "text", "text": "Found Python files."}],
                ]
            )

            result = run_agent("find python files", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "glob")
        self.assertEqual(result.observations[0].matches, ["app.py"])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_list_tree_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "src").mkdir()
            Path(base, "src", "app.py").write_text("print('ok')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "list_tree", "input": {"path": ".", "max_depth": 2}}],
                    [{"type": "text", "text": "Mapped project tree."}],
                ]
            )

            result = run_agent("map project tree", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "list_tree")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].entries, ["src/", "src/app.py"])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_repo_map_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "src").mkdir()
            Path(base, "src", "app.py").write_text("class App:\n    pass\n", encoding="utf-8")
            Path(base, "src", "app.ts").write_text("export function render() {}\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "repo_map", "input": {"path": ".", "max_depth": 2}}],
                    [{"type": "text", "text": "Mapped repository."}],
                ]
            )

            result = run_agent("map repository", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "repo_map")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].files, ["src/app.py", "src/app.ts"])
        self.assertEqual(result.observations[0].python_files[0].symbols[0].name, "App")
        self.assertEqual(result.observations[0].code_files[1].language, "typescript")
        self.assertEqual(result.observations[0].code_files[1].symbols[0].name, "render")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_read_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            Path(base, "config.py").write_text("debug = False\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "read_files", "input": {"paths": ["app.py", "config.py"]}}],
                    [{"type": "text", "text": "Read both files."}],
                ]
            )

            result = run_agent("read files", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "read_files")
        self.assertEqual([item.path for item in result.observations[0].files], ["app.py", "config.py"])
        self.assertTrue(all(item.ok for item in result.observations[0].files))
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_read_file_ranges_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "read_file_ranges",
                            "input": {"ranges": [{"path": "app.py", "start_line": 2, "line_count": 1}]},
                        }
                    ],
                    [{"type": "text", "text": "Read focused range."}],
                ]
            )

            result = run_agent("read focused ranges", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "read_file_ranges")
        self.assertEqual(result.observations[0].ranges[0].content, "2: two")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_file_info_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "file_info", "input": {"paths": ["app.py"]}}],
                    [{"type": "text", "text": "Inspected file metadata."}],
                ]
            )

            result = run_agent("inspect file metadata", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "file_info")
        self.assertEqual(result.observations[0].files[0].path, "app.py")
        self.assertTrue(result.observations[0].files[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_json_set_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts":{"test":"npm test"}}\n', encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_json_set",
                            "input": {
                                "path": "package.json",
                                "pointer": "/scripts/dev",
                                "value": "vite",
                                "create_missing": True,
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed JSON change."}],
                ]
            )

            result = run_agent("preview json", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "package.json").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, '{"scripts":{"test":"npm test"}}\n')
        self.assertEqual(result.observations[0].kind, "check_json_set")
        self.assertTrue(result.observations[0].ok)
        self.assertIn('"dev": "vite"', result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_json_set_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"private":false}\n', encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "json_set",
                            "input": {"path": "package.json", "pointer": "/private", "value": True},
                        }
                    ]
                ]
            )

            result = run_agent("set json", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "package.json").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, '{"private":false}\n')
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "json_set")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_json_remove_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts":{"test":"npm test","dev":"vite"}}\n', encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_json_remove",
                            "input": {"path": "package.json", "pointer": "/scripts/dev"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed JSON removal."}],
                ]
            )

            result = run_agent("preview json remove", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "package.json").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, '{"scripts":{"test":"npm test","dev":"vite"}}\n')
        self.assertEqual(result.observations[0].kind, "check_json_remove")
        self.assertTrue(result.observations[0].ok)
        self.assertIn('"dev":"vite"', result.observations[0].diff)
        self.assertIn('"test": "npm test"', result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_json_remove_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts":{"dev":"vite"}}\n', encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "json_remove",
                            "input": {"path": "package.json", "pointer": "/scripts/dev"},
                        }
                    ]
                ]
            )

            result = run_agent("remove json", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "package.json").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, '{"scripts":{"dev":"vite"}}\n')
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "json_remove")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_json_patch_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts":{"test":"npm test"},"private":false}\n', encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_json_patch",
                            "input": {
                                "path": "package.json",
                                "operations": [
                                    {"op": "add", "path": "/scripts/dev", "value": "vite"},
                                    {"op": "replace", "path": "/private", "value": True},
                                ],
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed JSON patch."}],
                ]
            )

            result = run_agent("preview json patch", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "package.json").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, '{"scripts":{"test":"npm test"},"private":false}\n')
        self.assertEqual(result.observations[0].kind, "check_json_patch")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].operation_count, 2)
        self.assertIn('"dev": "vite"', result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_json_patch_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts":{"test":"npm test"}}\n', encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "json_patch",
                            "input": {
                                "path": "package.json",
                                "operations": [{"op": "add", "path": "/scripts/dev", "value": "vite"}],
                            },
                        }
                    ]
                ]
            )

            result = run_agent("patch json", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "package.json").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, '{"scripts":{"test":"npm test"}}\n')
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "json_patch")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_python_symbols_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("class App:\n    def run(self):\n        return 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "python_symbols", "input": {"paths": ["app.py"]}}],
                    [{"type": "text", "text": "Inspected Python symbols."}],
                ]
            )

            result = run_agent("inspect python symbols", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_symbols")
        self.assertEqual([item.name for item in result.observations[0].files[0].symbols], ["App", "run"])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_code_outline_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.ts").write_text("export function render() {}\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "code_outline", "input": {"paths": ["app.ts"]}}],
                    [{"type": "text", "text": "Read code outline."}],
                ]
            )

            result = run_agent("outline code", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "code_outline")
        self.assertEqual(result.observations[0].files[0].language, "typescript")
        self.assertEqual(result.observations[0].files[0].symbols[0].name, "render")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_python_check_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "python_check", "input": {}}],
                    [{"type": "text", "text": "Checked Python syntax."}],
                ]
            )

            result = run_agent("check python", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_check")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].files[0].path, "app.py")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_config_check_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "package.json").write_text('{"scripts": {"test": "python3 -m unittest"}}\n', encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "config_check", "input": {}}],
                    [{"type": "text", "text": "Checked config syntax."}],
                ]
            )

            result = run_agent("check config", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "config_check")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].files[0].path, "package.json")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_python_dependencies_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "pkg").mkdir()
            Path(base, "pkg", "__init__.py").write_text("", encoding="utf-8")
            Path(base, "pkg", "util.py").write_text("VALUE = 1\n", encoding="utf-8")
            Path(base, "pkg", "app.py").write_text("from .util import VALUE\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "python_dependencies", "input": {"path": "pkg"}}],
                    [{"type": "text", "text": "Inspected Python dependencies."}],
                ]
            )

            result = run_agent("inspect python dependencies", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_dependencies")
        self.assertTrue(result.observations[0].ok)
        app = next(file for file in result.observations[0].files if file.path == "pkg/app.py")
        self.assertEqual(app.local_modules, ["pkg.util"])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_code_dependencies_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.ts").write_text("import React from 'react';\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "code_dependencies", "input": {"path": "."}}],
                    [{"type": "text", "text": "Read code dependencies."}],
                ]
            )

            result = run_agent("inspect code dependencies", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "code_dependencies")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].files[0].dependencies, ["react"])
        self.assertEqual(payload["kind"], "code_dependencies")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_code_references_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.ts").write_text("const runAgent = 1;\nrunAgent();\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "code_references", "input": {"symbol": "runAgent"}}],
                    [{"type": "text", "text": "Read code references."}],
                ]
            )

            result = run_agent("inspect code references", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "code_references")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].references[0].symbol, "runAgent")
        self.assertEqual(payload["kind"], "code_references")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_code_definitions_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.ts").write_text("export function runAgent() {\n  return 1;\n}\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "code_definitions", "input": {"symbol": "runAgent"}}],
                    [{"type": "text", "text": "Read code definitions."}],
                ]
            )

            result = run_agent("inspect code definitions", base_dir=Path(base), client=client, max_iterations=2)
            payload = json.loads(client.messages[1][-1].content[0]["content"])

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "code_definitions")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].definitions[0].name, "runAgent")
        self.assertEqual(payload["kind"], "code_definitions")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_python_definitions_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("def run_agent(task):\n    return task\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "python_definitions", "input": {"symbol": "run_agent"}}],
                    [{"type": "text", "text": "Inspected Python definitions."}],
                ]
            )

            result = run_agent("inspect python definitions", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_definitions")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].definitions[0].qualified_name, "run_agent")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_python_calls_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text(
                "def run_agent(task):\n    return task\n\nvalue = run_agent('x')\n",
                encoding="utf-8",
            )
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "python_calls",
                            "input": {"symbol": "run_agent"},
                        }
                    ],
                    [{"type": "text", "text": "Inspected Python calls."}],
                ]
            )

            result = run_agent("inspect python calls", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_calls")
        self.assertEqual([(item.path, item.line, item.callee) for item in result.observations[0].calls], [("app.py", 4, "run_agent")])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_python_call_graph_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text(
                "def run_agent(task):\n    return task\n\nvalue = run_agent('x')\n",
                encoding="utf-8",
            )
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "python_call_graph",
                            "input": {"path": "."},
                        }
                    ],
                    [{"type": "text", "text": "Inspected Python call graph."}],
                ]
            )

            result = run_agent("inspect python call graph", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_call_graph")
        self.assertEqual([(item.path, item.line, item.callee) for item in result.observations[0].edges], [("app.py", 4, "run_agent")])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_python_references_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text(
                "def run_agent(task):\n    return task\n\nvalue = run_agent('x')\n",
                encoding="utf-8",
            )
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "python_references",
                            "input": {"symbol": "run_agent"},
                        }
                    ],
                    [{"type": "text", "text": "Inspected Python references."}],
                ]
            )

            result = run_agent("inspect python references", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_references")
        self.assertEqual([(item.path, item.line, item.kind) for item in result.observations[0].references], [("app.py", 1, "definition"), ("app.py", 4, "reference")])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_python_rename_preview_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text(
                "def run_agent(task):\n    return run_agent(task)\n",
                encoding="utf-8",
            )
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "python_rename_preview",
                            "input": {"symbol": "run_agent", "new_name": "execute_agent"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed Python rename."}],
                ]
            )

            result = run_agent("preview rename", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "python_rename_preview")
        self.assertEqual(result.observations[0].total_replacements, 2)
        self.assertIn("+def execute_agent(task):", result.observations[0].files[0].diff)
        self.assertEqual(content, "def run_agent(task):\n    return run_agent(task)\n")
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_reports_binary_read_as_tool_failure_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "asset.bin").write_bytes(b"\x00\x01")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "read_file", "input": {"path": "asset.bin"}}],
                    [{"type": "text", "text": "Binary read failed normally."}],
                ]
            )

            result = run_agent("read binary", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "read_file")
        self.assertIn("binary or non-UTF-8", result.observations[0].message)
        self.assertEqual(result.steps[0].status, "failed")

    def test_run_agent_allows_list_processes_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "list_processes", "input": {}}],
                    [{"type": "text", "text": "No background processes."}],
                ]
            )

            result = run_agent("list processes", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "list_processes")
        self.assertEqual(result.observations[0].processes, [])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_stop_all_processes_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "stop_all_processes", "input": {}}],
                    [{"type": "text", "text": "Stopped background processes."}],
                ]
            )

            result = run_agent("stop all processes", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "stop_all_processes")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")
        self.assertEqual(result.steps[0].target, "background processes")

    def test_run_agent_guards_repeated_list_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "list_files", "input": {"path": "."}}],
                    [{"type": "tool_call", "id": "2", "name": "list_files", "input": {"path": "."}}],
                    [{"type": "tool_call", "id": "3", "name": "finish", "input": {"message": "Done."}}],
                ]
            )

            result = run_agent("list twice", base_dir=Path(base), client=client, max_iterations=3)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[1].kind, "list_files")
        self.assertIn("Already listed", result.observations[1].message)

    def test_run_agent_reports_malformed_tool_input_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "read_file", "input": {}}],
                    [{"type": "tool_call", "id": "2", "name": "finish", "input": {"message": "Handled error."}}],
                ]
            )

            result = run_agent("read a file", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertEqual(result.observations[0].kind, "tool_error")
        self.assertIn("read_file action requires a string path", result.observations[0].message)
        self.assertIn("tool_error", client.messages[1][-1].content[0]["content"])

    def test_run_agent_allows_plain_text_final_answer_after_tool_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "note.txt", "content": "ok\n"}}],
                    [{"type": "text", "text": "Created note.txt."}],
                ]
            )

            result = run_agent(
                "create note",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Created note.txt.")
        self.assertEqual([item.kind for item in result.observations], ["write_file"])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_writes_multiple_files_with_approval(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "write_files",
                            "input": {
                                "files": [
                                    {"path": "src/a.py", "content": "A = 1\n"},
                                    {"path": "src/b.py", "content": "B = 2\n"},
                                ]
                            },
                        }
                    ],
                    [{"type": "text", "text": "Created files."}],
                ]
            )

            result = run_agent(
                "create files",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=approve_all,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.observations[0].kind, "write_files")
            self.assertTrue(result.observations[0].ok)
            self.assertEqual(Path(base, "src", "a.py").read_text(encoding="utf-8"), "A = 1\n")
            self.assertEqual(Path(base, "src", "b.py").read_text(encoding="utf-8"), "B = 2\n")
            self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_write_file_before_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "note.txt", "content": "ok\n"}}],
                    [
                        {
                            "type": "tool_call",
                            "id": "2",
                            "name": "finish",
                            "input": {"message": "Write was denied."},
                        }
                    ],
                ]
            )

            result = run_agent(
                "create note",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                approval_handler=deny_all,
            )
            events_path = Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(result.success)
        self.assertFalse(Path(base, "note.txt").exists())
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertIn("approval_denied", client.messages[1][-1].content[0]["content"])
        self.assertEqual(result.steps[0].status, "denied")
        self.assertIn("approval_requested", [event["type"] for event in events])
        self.assertIn("approval_decision", [event["type"] for event in events])
        self.assertIn("step_started", [event["type"] for event in events])
        self.assertIn("step_completed", [event["type"] for event in events])

    def test_run_agent_denies_write_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [[{"type": "tool_call", "id": "1", "name": "write_file", "input": {"path": "note.txt", "content": "ok\n"}}]]
            )

            result = run_agent("create note", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertFalse(Path(base, "note.txt").exists())
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.steps[0].status, "denied")
        self.assertIn("No approval handler", result.observations[0].message)

    def test_run_agent_allows_check_write_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_write_file", "input": {"path": "note.txt", "content": "ok\n"}}],
                    [{"type": "text", "text": "Previewed note.txt."}],
                ]
            )

            result = run_agent("check create note", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertFalse(Path(base, "note.txt").exists())
        self.assertEqual(result.observations[0].kind, "check_write_file")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+ok", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_write_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "write_files",
                            "input": {"files": [{"path": "note.txt", "content": "ok\n"}]},
                        }
                    ]
                ]
            )

            result = run_agent("create note", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertFalse(Path(base, "note.txt").exists())
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.steps[0].status, "denied")
        self.assertIn("No approval handler", result.observations[0].message)

    def test_run_agent_allows_check_write_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_write_files",
                            "input": {"files": [{"path": "note.txt", "content": "ok\n"}]},
                        }
                    ],
                    [{"type": "text", "text": "Previewed files."}],
                ]
            )

            result = run_agent("check create note", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertFalse(Path(base, "note.txt").exists())
        self.assertEqual(result.observations[0].kind, "check_write_files")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+ok", result.observations[0].files[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_start_command_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "start_command",
                            "input": {"command": "python3 -m http.server 8000"},
                        }
                    ]
                ]
            )

            result = run_agent("start server", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "start_command")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_patch_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "patch_file",
                            "input": {
                                "path": "app.py",
                                "patch": "@@ -1 +1 @@\n-value = 'old'\n+value = 'new'\n",
                            },
                        }
                    ]
                ]
            )

            result = run_agent("patch app", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "value = 'old'\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "patch_file")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_patch_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_patch",
                            "input": {
                                "path": "app.py",
                                "patch": "@@ -1 +1 @@\n-value = 'old'\n+value = 'new'\n",
                            },
                        }
                    ],
                    [{"type": "text", "text": "Patch can apply."}],
                ]
            )

            result = run_agent("check patch", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "value = 'old'\n")
        self.assertEqual(result.observations[0].kind, "check_patch")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_patches_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            Path(base, "config.py").write_text("debug = False\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_patches",
                            "input": {
                                "patch": (
                                    "--- a/app.py\n"
                                    "+++ b/app.py\n"
                                    "@@ -1 +1 @@\n"
                                    "-value = 'old'\n"
                                    "+value = 'new'\n"
                                    "--- a/config.py\n"
                                    "+++ b/config.py\n"
                                    "@@ -1 +1 @@\n"
                                    "-debug = False\n"
                                    "+debug = True\n"
                                )
                            },
                        }
                    ],
                    [{"type": "text", "text": "Patches can apply."}],
                ]
            )

            result = run_agent("check patches", base_dir=Path(base), client=client, max_iterations=2)
            app = Path(base, "app.py").read_text(encoding="utf-8")
            config = Path(base, "config.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(app, "value = 'old'\n")
        self.assertEqual(config, "debug = False\n")
        self.assertEqual(result.observations[0].kind, "check_patches")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].files, ["app.py", "config.py"])
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_edit_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "edit_file",
                            "input": {"path": "app.py", "old": "old", "new": "new"},
                        }
                    ]
                ]
            )

            result = run_agent("edit app", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "value = 'old'\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "edit_file")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_edit_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_edit_file",
                            "input": {"path": "app.py", "old": "old", "new": "new"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed edit."}],
                ]
            )

            result = run_agent("check edit app", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "value = 'old'\n")
        self.assertEqual(result.observations[0].kind, "check_edit_file")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+value = 'new'", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_multi_edit_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\nprint(value)\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "multi_edit_file",
                            "input": {
                                "path": "app.py",
                                "edits": [
                                    {"old": "old", "new": "new"},
                                    {"old": "print(value)", "new": "print(value.upper())"},
                                ],
                            },
                        }
                    ]
                ]
            )

            result = run_agent("multi edit app", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "value = 'old'\nprint(value)\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "multi_edit_file")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_multi_edit_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\nprint(value)\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_multi_edit_file",
                            "input": {
                                "path": "app.py",
                                "edits": [
                                    {"old": "old", "new": "new"},
                                    {"old": "print(value)", "new": "print(value.upper())"},
                                ],
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed multi-edit."}],
                ]
            )

            result = run_agent("check multi edit app", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "value = 'old'\nprint(value)\n")
        self.assertEqual(result.observations[0].kind, "check_multi_edit_file")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+print(value.upper())", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_replace_python_definition_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("def run_agent(task):\n    return task\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "replace_python_definition",
                            "input": {
                                "symbol": "run_agent",
                                "path": "app.py",
                                "content": "def run_agent(task):\n    return task.upper()\n",
                            },
                        }
                    ]
                ]
            )

            result = run_agent("replace definition", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "def run_agent(task):\n    return task\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "replace_python_definition")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_replace_python_definition_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("def run_agent(task):\n    return task\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_replace_python_definition",
                            "input": {
                                "symbol": "run_agent",
                                "path": "app.py",
                                "content": "def run_agent(task):\n    return task.upper()\n",
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed Python definition replacement."}],
                ]
            )

            result = run_agent("check replace definition", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "def run_agent(task):\n    return task\n")
        self.assertEqual(result.observations[0].kind, "check_replace_python_definition")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+    return task.upper()", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_python_rename_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("def run_agent(task):\n    return run_agent(task)\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "python_rename",
                            "input": {"symbol": "run_agent", "new_name": "execute_agent"},
                        }
                    ]
                ]
            )

            result = run_agent("rename python", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "def run_agent(task):\n    return run_agent(task)\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "python_rename")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_replace_lines_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "replace_lines",
                            "input": {"path": "app.py", "start_line": 2, "end_line": 2, "content": "TWO\n"},
                        }
                    ]
                ]
            )

            result = run_agent("replace line", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "one\ntwo\nthree\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "replace_lines")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_replace_lines_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_replace_lines",
                            "input": {"path": "app.py", "start_line": 2, "end_line": 2, "content": "TWO\n"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed line replacement."}],
                ]
            )

            result = run_agent("check replace line", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "one\ntwo\nthree\n")
        self.assertEqual(result.observations[0].kind, "check_replace_lines")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+TWO", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_insert_lines_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("one\nthree\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "insert_lines",
                            "input": {"path": "app.py", "line": 2, "content": "two\n"},
                        }
                    ]
                ]
            )

            result = run_agent("insert line", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "one\nthree\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "insert_lines")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_insert_lines_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("one\nthree\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_insert_lines",
                            "input": {"path": "app.py", "line": 2, "content": "two\n"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed line insertion."}],
                ]
            )

            result = run_agent("check insert line", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "one\nthree\n")
        self.assertEqual(result.observations[0].kind, "check_insert_lines")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+two", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_append_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "notes.md").write_text("one\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "append_file",
                            "input": {"path": "notes.md", "content": "two\n"},
                        }
                    ]
                ]
            )

            result = run_agent("append note", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "notes.md").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "one\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "append_file")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_append_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "notes.md").write_text("one\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_append_file",
                            "input": {"path": "notes.md", "content": "two\n"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed append."}],
                ]
            )

            result = run_agent("check append note", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "notes.md").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "one\n")
        self.assertEqual(result.observations[0].kind, "check_append_file")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("+two", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_regex_replace_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "regex_replace",
                            "input": {"path": "app.py", "pattern": "old", "replacement": "new"},
                        }
                    ]
                ]
            )

            result = run_agent("regex replace", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "value = 'old'\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "regex_replace")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_regex_replace_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_regex_replace",
                            "input": {"path": "app.py", "pattern": "old", "replacement": "new"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed regex replacement."}],
                ]
            )

            result = run_agent("preview regex replace", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "value = 'old'\n")
        self.assertEqual(result.observations[0].kind, "check_regex_replace")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].replacements, 1)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_patch_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "app.py").write_text("value = 'old'\n", encoding="utf-8")
            Path(base, "config.py").write_text("debug = False\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "patch_files",
                            "input": {
                                "patch": (
                                    "--- a/app.py\n"
                                    "+++ b/app.py\n"
                                    "@@ -1 +1 @@\n"
                                    "-value = 'old'\n"
                                    "+value = 'new'\n"
                                    "--- a/config.py\n"
                                    "+++ b/config.py\n"
                                    "@@ -1 +1 @@\n"
                                    "-debug = False\n"
                                    "+debug = True\n"
                                )
                            },
                        }
                    ]
                ]
            )

            result = run_agent("patch files", base_dir=Path(base), client=client, max_iterations=1)
            app = Path(base, "app.py").read_text(encoding="utf-8")
            config = Path(base, "config.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(app, "value = 'old'\n")
        self.assertEqual(config, "debug = False\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "patch_files")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_delete_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "obsolete.py").write_text("print('keep')\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "delete_file",
                            "input": {"path": "obsolete.py"},
                        }
                    ]
                ]
            )

            result = run_agent("delete file", base_dir=Path(base), client=client, max_iterations=1)
            content = Path(base, "obsolete.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content, "print('keep')\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "delete_file")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_delete_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "obsolete.py").write_text("print('keep')\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_delete_file",
                            "input": {"path": "obsolete.py"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed deletion."}],
                ]
            )

            result = run_agent("check delete file", base_dir=Path(base), client=client, max_iterations=2)
            content = Path(base, "obsolete.py").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(content, "print('keep')\n")
        self.assertEqual(result.observations[0].kind, "check_delete_file")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("-print('keep')", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_delete_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "one.txt").write_text("one\n", encoding="utf-8")
            Path(base, "two.txt").write_text("two\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "delete_files",
                            "input": {"paths": ["one.txt", "two.txt"]},
                        }
                    ]
                ]
            )

            result = run_agent("delete files", base_dir=Path(base), client=client, max_iterations=1)
            one = Path(base, "one.txt").read_text(encoding="utf-8")
            two = Path(base, "two.txt").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(one, "one\n")
        self.assertEqual(two, "two\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "delete_files")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_delete_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "one.txt").write_text("one\n", encoding="utf-8")
            Path(base, "two.txt").write_text("two\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_delete_files",
                            "input": {"paths": ["one.txt", "two.txt"]},
                        }
                    ],
                    [{"type": "text", "text": "Previewed deletions."}],
                ]
            )

            result = run_agent("check delete files", base_dir=Path(base), client=client, max_iterations=2)
            one = Path(base, "one.txt").read_text(encoding="utf-8")
            two = Path(base, "two.txt").read_text(encoding="utf-8")

        self.assertTrue(result.success)
        self.assertEqual(one, "one\n")
        self.assertEqual(two, "two\n")
        self.assertEqual(result.observations[0].kind, "check_delete_files")
        self.assertTrue(result.observations[0].ok)
        self.assertIn("-one", result.observations[0].diff)
        self.assertIn("-two", result.observations[0].diff)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_move_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "old.py").write_text("print('keep')\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "move_file",
                            "input": {"source": "old.py", "destination": "new.py"},
                        }
                    ]
                ]
            )

            result = run_agent("move file", base_dir=Path(base), client=client, max_iterations=1)
            old_exists = Path(base, "old.py").exists()
            new_exists = Path(base, "new.py").exists()

        self.assertFalse(result.success)
        self.assertTrue(old_exists)
        self.assertFalse(new_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "move_file")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_move_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "old.py").write_text("print('keep')\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_move_file",
                            "input": {"source": "old.py", "destination": "new.py"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed move."}],
                ]
            )

            result = run_agent("check move file", base_dir=Path(base), client=client, max_iterations=2)
            old_exists = Path(base, "old.py").exists()
            new_exists = Path(base, "new.py").exists()

        self.assertTrue(result.success)
        self.assertTrue(old_exists)
        self.assertFalse(new_exists)
        self.assertEqual(result.observations[0].kind, "check_move_file")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_move_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "one.py").write_text("one\n", encoding="utf-8")
            Path(base, "two.py").write_text("two\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "move_files",
                            "input": {
                                "transfers": [
                                    {"source": "one.py", "destination": "moved/one.py"},
                                    {"source": "two.py", "destination": "moved/two.py"},
                                ]
                            },
                        }
                    ]
                ]
            )

            result = run_agent("move files", base_dir=Path(base), client=client, max_iterations=1)
            one_exists = Path(base, "one.py").exists()
            two_exists = Path(base, "two.py").exists()
            moved_one_exists = Path(base, "moved", "one.py").exists()

        self.assertFalse(result.success)
        self.assertTrue(one_exists)
        self.assertTrue(two_exists)
        self.assertFalse(moved_one_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "move_files")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_move_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "one.py").write_text("one\n", encoding="utf-8")
            Path(base, "two.py").write_text("two\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_move_files",
                            "input": {
                                "transfers": [
                                    {"source": "one.py", "destination": "moved/one.py"},
                                    {"source": "two.py", "destination": "moved/two.py"},
                                ]
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed moves."}],
                ]
            )

            result = run_agent("check move files", base_dir=Path(base), client=client, max_iterations=2)
            one_exists = Path(base, "one.py").exists()
            two_exists = Path(base, "two.py").exists()
            moved_one_exists = Path(base, "moved", "one.py").exists()

        self.assertTrue(result.success)
        self.assertTrue(one_exists)
        self.assertTrue(two_exists)
        self.assertFalse(moved_one_exists)
        self.assertEqual(result.observations[0].kind, "check_move_files")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_copy_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "template.py").write_text("print('keep')\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "copy_file",
                            "input": {"source": "template.py", "destination": "copied.py"},
                        }
                    ]
                ]
            )

            result = run_agent("copy file", base_dir=Path(base), client=client, max_iterations=1)
            source_exists = Path(base, "template.py").exists()
            copied_exists = Path(base, "copied.py").exists()

        self.assertFalse(result.success)
        self.assertTrue(source_exists)
        self.assertFalse(copied_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "copy_file")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_copy_file_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "template.py").write_text("print('keep')\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_copy_file",
                            "input": {"source": "template.py", "destination": "copied.py"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed copy."}],
                ]
            )

            result = run_agent("check copy file", base_dir=Path(base), client=client, max_iterations=2)
            source_exists = Path(base, "template.py").exists()
            copied_exists = Path(base, "copied.py").exists()

        self.assertTrue(result.success)
        self.assertTrue(source_exists)
        self.assertFalse(copied_exists)
        self.assertEqual(result.observations[0].kind, "check_copy_file")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_copy_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "one.py").write_text("one\n", encoding="utf-8")
            Path(base, "two.py").write_text("two\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "copy_files",
                            "input": {
                                "transfers": [
                                    {"source": "one.py", "destination": "copies/one.py"},
                                    {"source": "two.py", "destination": "copies/two.py"},
                                ]
                            },
                        }
                    ]
                ]
            )

            result = run_agent("copy files", base_dir=Path(base), client=client, max_iterations=1)
            one_exists = Path(base, "one.py").exists()
            two_exists = Path(base, "two.py").exists()
            copied_one_exists = Path(base, "copies", "one.py").exists()

        self.assertFalse(result.success)
        self.assertTrue(one_exists)
        self.assertTrue(two_exists)
        self.assertFalse(copied_one_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "copy_files")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_copy_files_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            Path(base, "one.py").write_text("one\n", encoding="utf-8")
            Path(base, "two.py").write_text("two\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_copy_files",
                            "input": {
                                "transfers": [
                                    {"source": "one.py", "destination": "copies/one.py"},
                                    {"source": "two.py", "destination": "copies/two.py"},
                                ]
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed copies."}],
                ]
            )

            result = run_agent("check copy files", base_dir=Path(base), client=client, max_iterations=2)
            one_exists = Path(base, "one.py").exists()
            two_exists = Path(base, "two.py").exists()
            copied_one_exists = Path(base, "copies", "one.py").exists()

        self.assertTrue(result.success)
        self.assertTrue(one_exists)
        self.assertTrue(two_exists)
        self.assertFalse(copied_one_exists)
        self.assertEqual(result.observations[0].kind, "check_copy_files")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_create_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "create_dir",
                            "input": {"path": "pkg/generated"},
                        }
                    ]
                ]
            )

            result = run_agent("create directory", base_dir=Path(base), client=client, max_iterations=1)
            created_exists = Path(base, "pkg", "generated").exists()

        self.assertFalse(result.success)
        self.assertFalse(created_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "create_dir")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_create_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_create_dir",
                            "input": {"path": "pkg/generated"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed directory creation."}],
                ]
            )

            result = run_agent("check create directory", base_dir=Path(base), client=client, max_iterations=2)
            created_exists = Path(base, "pkg", "generated").exists()

        self.assertTrue(result.success)
        self.assertFalse(created_exists)
        self.assertEqual(result.observations[0].kind, "check_create_dir")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_create_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "create_dirs",
                            "input": {"paths": ["pkg/generated", "assets/icons"]},
                        }
                    ]
                ]
            )

            result = run_agent("create directories", base_dir=Path(base), client=client, max_iterations=1)
            created_exists = [Path(base, "pkg", "generated").exists(), Path(base, "assets", "icons").exists()]

        self.assertFalse(result.success)
        self.assertEqual(created_exists, [False, False])
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "create_dirs")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_create_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_create_dirs",
                            "input": {"paths": ["pkg/generated", "assets/icons"]},
                        }
                    ],
                    [{"type": "text", "text": "Previewed directory creation."}],
                ]
            )

            result = run_agent("check create directories", base_dir=Path(base), client=client, max_iterations=2)
            created_exists = [Path(base, "pkg", "generated").exists(), Path(base, "assets", "icons").exists()]

        self.assertTrue(result.success)
        self.assertEqual(created_exists, [False, False])
        self.assertEqual(result.observations[0].kind, "check_create_dirs")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_move_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source = Path(base, "old_pkg")
            source.mkdir()
            (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "move_dir",
                            "input": {"source": "old_pkg", "destination": "new_pkg"},
                        }
                    ]
                ]
            )

            result = run_agent("move directory", base_dir=Path(base), client=client, max_iterations=1)
            source_exists = source.exists()
            destination_exists = Path(base, "new_pkg").exists()

        self.assertFalse(result.success)
        self.assertTrue(source_exists)
        self.assertFalse(destination_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "move_dir")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_move_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source = Path(base, "old_pkg")
            source.mkdir()
            (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_move_dir",
                            "input": {"source": "old_pkg", "destination": "new_pkg"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed directory move."}],
                ]
            )

            result = run_agent("check move directory", base_dir=Path(base), client=client, max_iterations=2)
            source_exists = source.exists()
            destination_exists = Path(base, "new_pkg").exists()

        self.assertTrue(result.success)
        self.assertTrue(source_exists)
        self.assertFalse(destination_exists)
        self.assertEqual(result.observations[0].kind, "check_move_dir")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_move_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source_a = Path(base, "old_a")
            source_b = Path(base, "old_b")
            source_a.mkdir()
            source_b.mkdir()
            (source_a / "module.py").write_text("A = 1\n", encoding="utf-8")
            (source_b / "module.py").write_text("B = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "move_dirs",
                            "input": {
                                "transfers": [
                                    {"source": "old_a", "destination": "new_a"},
                                    {"source": "old_b", "destination": "new_b"},
                                ]
                            },
                        }
                    ]
                ]
            )

            result = run_agent("move directories", base_dir=Path(base), client=client, max_iterations=1)
            sources_exist = [source_a.exists(), source_b.exists()]
            destinations_exist = [Path(base, "new_a").exists(), Path(base, "new_b").exists()]

        self.assertFalse(result.success)
        self.assertEqual(sources_exist, [True, True])
        self.assertEqual(destinations_exist, [False, False])
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "move_dirs")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_move_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source_a = Path(base, "old_a")
            source_b = Path(base, "old_b")
            source_a.mkdir()
            source_b.mkdir()
            (source_a / "module.py").write_text("A = 1\n", encoding="utf-8")
            (source_b / "module.py").write_text("B = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_move_dirs",
                            "input": {
                                "transfers": [
                                    {"source": "old_a", "destination": "new_a"},
                                    {"source": "old_b", "destination": "new_b"},
                                ]
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed directory moves."}],
                ]
            )

            result = run_agent("check move directories", base_dir=Path(base), client=client, max_iterations=2)
            sources_exist = [source_a.exists(), source_b.exists()]
            destinations_exist = [Path(base, "new_a").exists(), Path(base, "new_b").exists()]

        self.assertTrue(result.success)
        self.assertEqual(sources_exist, [True, True])
        self.assertEqual(destinations_exist, [False, False])
        self.assertEqual(result.observations[0].kind, "check_move_dirs")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_copy_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source = Path(base, "template_pkg")
            source.mkdir()
            (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "copy_dir",
                            "input": {"source": "template_pkg", "destination": "new_pkg"},
                        }
                    ]
                ]
            )

            result = run_agent("copy directory", base_dir=Path(base), client=client, max_iterations=1)
            source_exists = source.exists()
            destination_exists = Path(base, "new_pkg").exists()

        self.assertFalse(result.success)
        self.assertTrue(source_exists)
        self.assertFalse(destination_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "copy_dir")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_copy_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source = Path(base, "template_pkg")
            source.mkdir()
            (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_copy_dir",
                            "input": {"source": "template_pkg", "destination": "new_pkg"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed directory copy."}],
                ]
            )

            result = run_agent("check copy directory", base_dir=Path(base), client=client, max_iterations=2)
            source_exists = source.exists()
            destination_exists = Path(base, "new_pkg").exists()

        self.assertTrue(result.success)
        self.assertTrue(source_exists)
        self.assertFalse(destination_exists)
        self.assertEqual(result.observations[0].kind, "check_copy_dir")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_copy_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source_a = Path(base, "template_a")
            source_b = Path(base, "template_b")
            source_a.mkdir()
            source_b.mkdir()
            (source_a / "module.py").write_text("A = 1\n", encoding="utf-8")
            (source_b / "module.py").write_text("B = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "copy_dirs",
                            "input": {
                                "transfers": [
                                    {"source": "template_a", "destination": "copy_a"},
                                    {"source": "template_b", "destination": "copy_b"},
                                ]
                            },
                        }
                    ]
                ]
            )

            result = run_agent("copy directories", base_dir=Path(base), client=client, max_iterations=1)
            sources_exist = [source_a.exists(), source_b.exists()]
            destinations_exist = [Path(base, "copy_a").exists(), Path(base, "copy_b").exists()]

        self.assertFalse(result.success)
        self.assertEqual(sources_exist, [True, True])
        self.assertEqual(destinations_exist, [False, False])
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "copy_dirs")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_copy_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            source_a = Path(base, "template_a")
            source_b = Path(base, "template_b")
            source_a.mkdir()
            source_b.mkdir()
            (source_a / "module.py").write_text("A = 1\n", encoding="utf-8")
            (source_b / "module.py").write_text("B = 1\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_copy_dirs",
                            "input": {
                                "transfers": [
                                    {"source": "template_a", "destination": "copy_a"},
                                    {"source": "template_b", "destination": "copy_b"},
                                ]
                            },
                        }
                    ],
                    [{"type": "text", "text": "Previewed directory copies."}],
                ]
            )

            result = run_agent("check copy directories", base_dir=Path(base), client=client, max_iterations=2)
            sources_exist = [source_a.exists(), source_b.exists()]
            destinations_exist = [Path(base, "copy_a").exists(), Path(base, "copy_b").exists()]

        self.assertTrue(result.success)
        self.assertEqual(sources_exist, [True, True])
        self.assertEqual(destinations_exist, [False, False])
        self.assertEqual(result.observations[0].kind, "check_copy_dirs")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_delete_empty_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            empty_dir = Path(base, "empty")
            empty_dir.mkdir()
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "delete_empty_dir",
                            "input": {"path": "empty"},
                        }
                    ]
                ]
            )

            result = run_agent("delete empty directory", base_dir=Path(base), client=client, max_iterations=1)
            empty_exists = empty_dir.exists()

        self.assertFalse(result.success)
        self.assertTrue(empty_exists)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "delete_empty_dir")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_delete_empty_dir_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            empty_dir = Path(base, "empty")
            empty_dir.mkdir()
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_delete_empty_dir",
                            "input": {"path": "empty"},
                        }
                    ],
                    [{"type": "text", "text": "Previewed empty directory deletion."}],
                ]
            )

            result = run_agent("check delete empty directory", base_dir=Path(base), client=client, max_iterations=2)
            empty_exists = empty_dir.exists()

        self.assertTrue(result.success)
        self.assertTrue(empty_exists)
        self.assertEqual(result.observations[0].kind, "check_delete_empty_dir")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_delete_empty_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            empty_a = Path(base, "empty-a")
            empty_b = Path(base, "empty-b")
            empty_a.mkdir()
            empty_b.mkdir()
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "delete_empty_dirs",
                            "input": {"paths": ["empty-a", "empty-b"]},
                        }
                    ]
                ]
            )

            result = run_agent("delete empty directories", base_dir=Path(base), client=client, max_iterations=1)
            empty_exists = [empty_a.exists(), empty_b.exists()]

        self.assertFalse(result.success)
        self.assertEqual(empty_exists, [True, True])
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "delete_empty_dirs")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_delete_empty_dirs_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            empty_a = Path(base, "empty-a")
            empty_b = Path(base, "empty-b")
            empty_a.mkdir()
            empty_b.mkdir()
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_delete_empty_dirs",
                            "input": {"paths": ["empty-a", "empty-b"]},
                        }
                    ],
                    [{"type": "text", "text": "Previewed empty directory deletion."}],
                ]
            )

            result = run_agent("check delete empty directories", base_dir=Path(base), client=client, max_iterations=2)
            empty_exists = [empty_a.exists(), empty_b.exists()]

        self.assertTrue(result.success)
        self.assertEqual(empty_exists, [True, True])
        self.assertEqual(result.observations[0].kind, "check_delete_empty_dirs")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_set_executable_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            script = Path(base, "tool.sh")
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o644)
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "set_executable",
                            "input": {"path": "tool.sh", "executable": True},
                        }
                    ]
                ]
            )

            result = run_agent("make executable", base_dir=Path(base), client=client, max_iterations=1)
            mode = script.stat().st_mode & 0o777

        self.assertFalse(result.success)
        self.assertEqual(mode, 0o644)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "set_executable")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_set_executable_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            script = Path(base, "tool.sh")
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o644)
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "check_set_executable",
                            "input": {"path": "tool.sh", "executable": True},
                        }
                    ],
                    [{"type": "text", "text": "Previewed executable bit."}],
                ]
            )

            result = run_agent("check executable", base_dir=Path(base), client=client, max_iterations=2)
            mode = script.stat().st_mode & 0o777

        self.assertTrue(result.success)
        self.assertEqual(mode, 0o644)
        self.assertEqual(result.observations[0].kind, "check_set_executable")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual((result.observations[0].mode_before, result.observations[0].mode_after), ("0644", "0755"))
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_git_stage_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "git_stage",
                            "input": {"paths": ["app.py"]},
                        }
                    ]
                ]
            )

            result = run_agent("stage file", base_dir=Path(base), client=client, max_iterations=1)
            status = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout

        self.assertFalse(result.success)
        self.assertIn(" M app.py", status)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_stage")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_switch_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "git_switch",
                            "input": {"branch": "feature/new", "create": True},
                        }
                    ]
                ]
            )

            result = run_agent("switch branch", base_dir=Path(base), client=client, max_iterations=1)
            current = subprocess.run(["git", "branch", "--show-current"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()

        self.assertFalse(result.success)
        self.assertEqual(current, "main")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_switch")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_fetch_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            remote = Path(base, "remote.git")
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_fetch", "input": {"remote": "origin"}}],
                ]
            )

            result = run_agent("fetch remote", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_fetch")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_pull_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            remote = Path(base, "remote.git")
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_pull", "input": {}}],
                ]
            )

            result = run_agent("pull upstream", base_dir=Path(base), client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_pull")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_push_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base, "repo")
            root.mkdir()
            remote = Path(base, "remote.git")
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(root, "app.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(["git", "branch", "-M", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "init", "--bare", remote.as_posix()], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", remote.as_posix()], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(root, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "local update"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_push", "input": {}}],
                ]
            )

            result = run_agent("push upstream", base_dir=root, client=client, max_iterations=1)

        self.assertFalse(result.success)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_push")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_restore_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_restore", "input": {"paths": ["app.py"]}}],
                ]
            )

            result = run_agent("restore app", base_dir=Path(base), client=client, max_iterations=1)
            content_after = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content_after, "print('new')\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_restore")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_stash_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_stash", "input": {"message": "save work"}}],
                ]
            )

            result = run_agent("stash work", base_dir=Path(base), client=client, max_iterations=1)
            content_after = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content_after, "print('new')\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_stash")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_stash_apply_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save work", "--", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_stash_apply", "input": {"stash_ref": "stash@{0}"}}],
                ]
            )

            result = run_agent("apply stash", base_dir=Path(base), client=client, max_iterations=1)
            content_after = Path(base, "app.py").read_text(encoding="utf-8")

        self.assertFalse(result.success)
        self.assertEqual(content_after, "print('old')\n")
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_stash_apply")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_denies_git_stash_drop_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "stash", "push", "-m", "save work", "--", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "git_stash_drop", "input": {"stash_ref": "stash@{0}"}}],
                ]
            )

            result = run_agent("drop stash", base_dir=Path(base), client=client, max_iterations=1)
            stash_list = subprocess.run(["git", "stash", "list"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout

        self.assertFalse(result.success)
        self.assertIn("save work", stash_list)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_stash_drop")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_git_stage_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_stage", "input": {"paths": ["app.py"]}}],
                    [{"type": "text", "text": "Previewed staging."}],
                ]
            )

            result = run_agent("check stage file", base_dir=Path(base), client=client, max_iterations=2)
            status = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout

        self.assertTrue(result.success)
        self.assertIn(" M app.py", status)
        self.assertEqual(result.observations[0].kind, "check_git_stage")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_allows_check_git_unstage_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('old')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_unstage", "input": {"paths": ["app.py"]}}],
                    [{"type": "text", "text": "Previewed unstaging."}],
                ]
            )

            result = run_agent("check unstage file", base_dir=Path(base), client=client, max_iterations=2)
            status = subprocess.run(["git", "status", "--short"], cwd=root, check=True, stdout=subprocess.PIPE, text=True).stdout

        self.assertTrue(result.success)
        self.assertIn("M  app.py", status)
        self.assertEqual(result.observations[0].kind, "check_git_unstage")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.steps[0].status, "completed")

    def test_run_agent_denies_git_commit_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "1",
                            "name": "git_commit",
                            "input": {"message": "initial"},
                        }
                    ]
                ]
            )

            result = run_agent("commit staged changes", base_dir=Path(base), client=client, max_iterations=1)
            log = subprocess.run(["git", "log", "--oneline"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        self.assertFalse(result.success)
        self.assertNotEqual(log.returncode, 0)
        self.assertEqual(result.observations[0].kind, "approval_denied")
        self.assertEqual(result.observations[0].action_type, "git_commit")
        self.assertEqual(result.steps[0].status, "denied")

    def test_run_agent_allows_check_git_commit_without_approval_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(base, "app.py").write_text("print('new')\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = MockClient(
                [
                    [{"type": "tool_call", "id": "1", "name": "check_git_commit", "input": {"message": "initial"}}],
                    [{"type": "text", "text": "Previewed commit."}],
                ]
            )

            result = run_agent("check commit staged changes", base_dir=Path(base), client=client, max_iterations=2)
            log = subprocess.run(["git", "log", "--oneline"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        self.assertTrue(result.success)
        self.assertNotEqual(log.returncode, 0)
        self.assertEqual(result.observations[0].kind, "check_git_commit")
        self.assertTrue(result.observations[0].ok)
        self.assertEqual(result.observations[0].head_before, result.observations[0].head_after)
        self.assertEqual(result.steps[0].status, "completed")


if __name__ == "__main__":
    unittest.main()
