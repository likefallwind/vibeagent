import tempfile
import unittest
import json
import subprocess
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.types import ApprovalDecision, ApprovalRequest, AssistantResponse, ChatMessage, ContentBlock


class MockClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
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
        self.index += 1
        return AssistantResponse(content=response, raw={"content": response})


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
        self.assertIn("npm run test: python3 -m unittest discover -s tests", first_user)

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
        self.assertEqual(result.observations[0].files, ["src/app.py"])
        self.assertEqual(result.observations[0].python_files[0].symbols[0].name, "App")
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


if __name__ == "__main__":
    unittest.main()
