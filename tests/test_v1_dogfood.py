from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.session_commands import get_resume_context
from vibeagent.types import ApprovalDecision, ApprovalRequest, AssistantResponse, ChatMessage, ContentBlock


class DogfoodClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []
        self.tools: list[list[dict]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.tools.append(list(tools or []))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def approve_all(_request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(approved=True, message="approved")


def init_broken_calculator_repo(root: Path) -> None:
    (root / "tests").mkdir()
    (root / "calc.py").write_text("def add(left, right):\n    return left - right\n", encoding="utf-8")
    (root / ".gitignore").write_text(".vibeagent/\n__pycache__/\n", encoding="utf-8")
    (root / "tests" / "test_calc.py").write_text(
        "import unittest\n\n"
        "from calc import add\n\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_adds_two_numbers(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    subprocess.run(
        ["git", "add", ".gitignore", "calc.py", "tests/test_calc.py"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(["git", "commit", "-m", "initial broken calculator"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def v1_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "overview-1",
                "name": "project_overview",
                "input": {"max_files": 20, "max_commands": 10, "max_checks": 10},
            }
        ],
        [
            {"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "calc.py"}},
            {"type": "tool_call", "id": "read-2", "name": "read_file", "input": {"path": "tests/test_calc.py"}},
        ],
        [
            {
                "type": "tool_call",
                "id": "test-1",
                "name": "run_command",
                "input": {"command": "python -B -m unittest discover -s tests", "timeout_ms": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "plan-1",
                "name": "update_plan",
                "input": {
                    "plan": [
                        {"step": "Inspect calculator code and tests", "status": "completed"},
                        {"step": "Reproduce the failing test", "status": "completed"},
                        {"step": "Fix add implementation", "status": "in_progress"},
                        {"step": "Rerun unit tests", "status": "pending"},
                        {"step": "Commit verified fix", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "write-1",
                "name": "write_file",
                "input": {"path": "calc.py", "content": "def add(left, right):\n    return left + right\n"},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "test-2",
                "name": "run_command",
                "input": {"command": "python -B -m unittest discover -s tests", "timeout_ms": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "plan-2",
                "name": "update_plan",
                "input": {
                    "plan": [
                        {"step": "Inspect calculator code and tests", "status": "completed"},
                        {"step": "Reproduce the failing test", "status": "completed"},
                        {"step": "Fix add implementation", "status": "completed"},
                        {"step": "Rerun unit tests", "status": "completed"},
                        {"step": "Commit verified fix", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add"}}],
        [
            {
                "type": "tool_call",
                "id": "plan-3",
                "name": "update_plan",
                "input": {
                    "plan": [
                        {"step": "Inspect calculator code and tests", "status": "completed"},
                        {"step": "Reproduce the failing test", "status": "completed"},
                        {"step": "Fix add implementation", "status": "completed"},
                        {"step": "Rerun unit tests", "status": "completed"},
                        {"step": "Commit verified fix", "status": "completed"},
                    ]
                },
            }
        ],
        [{"type": "text", "text": "Fixed calculator addition, verified tests pass, and committed the change."}],
        [
            {
                "type": "tool_call",
                "id": "verify-1",
                "name": "run_session_verification",
                "input": {"include_pending": True, "include_failed": True, "timeout_ms": 10_000},
            }
        ],
        [{"type": "text", "text": "Verified the recorded checks, committed the fix, and the workspace is clean."}],
    ]


def interrupted_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "overview-1",
                "name": "project_overview",
                "input": {"max_files": 20, "max_commands": 10, "max_checks": 10},
            }
        ],
        [
            {"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "calc.py"}},
            {"type": "tool_call", "id": "read-2", "name": "read_file", "input": {"path": "tests/test_calc.py"}},
        ],
        [
            {
                "type": "tool_call",
                "id": "test-1",
                "name": "run_command",
                "input": {"command": "python -B -m unittest discover -s tests", "timeout_ms": 10_000},
            }
        ],
    ]


def resumed_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "plan-1",
                "name": "update_plan",
                "input": {
                    "plan": [
                        {"step": "Use resumed context to confirm the previous failing test", "status": "completed"},
                        {"step": "Fix add implementation", "status": "in_progress"},
                        {"step": "Rerun unit tests", "status": "pending"},
                        {"step": "Commit verified fix", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "write-1",
                "name": "write_file",
                "input": {"path": "calc.py", "content": "def add(left, right):\n    return left + right\n"},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "test-2",
                "name": "run_command",
                "input": {"command": "python -B -m unittest discover -s tests", "timeout_ms": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "plan-2",
                "name": "update_plan",
                "input": {
                    "plan": [
                        {"step": "Use resumed context to confirm the previous failing test", "status": "completed"},
                        {"step": "Fix add implementation", "status": "completed"},
                        {"step": "Rerun unit tests", "status": "completed"},
                        {"step": "Commit verified fix", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after resume"}}],
        [
            {
                "type": "tool_call",
                "id": "plan-3",
                "name": "update_plan",
                "input": {
                    "plan": [
                        {"step": "Use resumed context to confirm the previous failing test", "status": "completed"},
                        {"step": "Fix add implementation", "status": "completed"},
                        {"step": "Rerun unit tests", "status": "completed"},
                        {"step": "Commit verified fix", "status": "completed"},
                    ]
                },
            }
        ],
        [{"type": "text", "text": "Resumed from the previous failed test, fixed the code, verified tests, and committed."}],
        [
            {
                "type": "tool_call",
                "id": "verify-1",
                "name": "run_session_verification",
                "input": {"include_pending": True, "include_failed": True, "timeout_ms": 10_000},
            }
        ],
        [{"type": "text", "text": "Session verification is clean after resume and the fix is committed."}],
    ]


def claude_compat_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "in_progress"},
                        {"content": "Reproduce the failure", "status": "pending"},
                        {"content": "Patch the implementation", "status": "pending"},
                        {"content": "Verify and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {"type": "tool_call", "id": "read-1", "name": "Read", "input": {"file_path": "calc.py"}},
            {"type": "tool_call", "id": "read-2", "name": "Read", "input": {"file_path": "tests/test_calc.py"}},
        ],
        [
            {
                "type": "tool_call",
                "id": "bash-1",
                "name": "Bash",
                "input": {
                    "command": "PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests",
                    "timeout": 10_000,
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "completed"},
                        {"content": "Reproduce the failure", "status": "completed"},
                        {"content": "Patch the implementation", "status": "in_progress"},
                        {"content": "Verify and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "edit-1",
                "name": "Edit",
                "input": {
                    "file_path": "calc.py",
                    "old_string": "return left - right",
                    "new_string": "return left + right",
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "bash-2",
                "name": "Bash",
                "input": {"command": "python -m unittest discover -s tests", "timeout": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-3",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "completed"},
                        {"content": "Reproduce the failure", "status": "completed"},
                        {"content": "Patch the implementation", "status": "completed"},
                        {"content": "Verify and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "todo-read-1", "name": "TodoRead", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add via Claude aliases"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "completed"},
                        {"content": "Reproduce the failure", "status": "completed"},
                        {"content": "Patch the implementation", "status": "completed"},
                        {"content": "Verify and commit", "status": "completed"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "verify-1",
                "name": "run_session_verification",
                "input": {"include_pending": True, "include_failed": True, "timeout_ms": 10_000},
            }
        ],
        [{"type": "text", "text": "Fixed with Claude-compatible tools, verified tests, and committed."}],
    ]


def delegated_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "delegate-1",
                "name": "Task",
                "input": {
                    "prompt": "Inspect calc.py and its test to identify the failing behavior.",
                    "description": "Read-only investigation before the parent edits.",
                    "max_iterations": 2,
                },
            }
        ],
        [
            {"type": "tool_call", "id": "read-1", "name": "Read", "input": {"file_path": "calc.py"}},
            {"type": "tool_call", "id": "read-2", "name": "Read", "input": {"file_path": "tests/test_calc.py"}},
        ],
        [{"type": "text", "text": "The test expects add(2, 3) == 5, but calc.py subtracts on line 2."}],
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Use delegated investigation", "status": "completed"},
                        {"content": "Reproduce the failing test", "status": "in_progress"},
                        {"content": "Patch add implementation", "status": "pending"},
                        {"content": "Verify and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "bash-1",
                "name": "Bash",
                "input": {
                    "command": "PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests",
                    "timeout": 10_000,
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "edit-1",
                "name": "Edit",
                "input": {
                    "file_path": "calc.py",
                    "old_string": "return left - right",
                    "new_string": "return left + right",
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Use delegated investigation", "status": "completed"},
                        {"content": "Reproduce the failing test", "status": "completed"},
                        {"content": "Patch add implementation", "status": "completed"},
                        {"content": "Verify and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "bash-2",
                "name": "Bash",
                "input": {"command": "python -m unittest discover -s tests", "timeout": 10_000},
            }
        ],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after delegation"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-3",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Use delegated investigation", "status": "completed"},
                        {"content": "Reproduce the failing test", "status": "completed"},
                        {"content": "Patch add implementation", "status": "completed"},
                        {"content": "Verify and commit", "status": "completed"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "verify-1",
                "name": "run_session_verification",
                "input": {"include_pending": True, "include_failed": True, "timeout_ms": 10_000},
            }
        ],
        [{"type": "text", "text": "Delegated the investigation, fixed the implementation, verified tests, and committed."}],
    ]


def plan_mode_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "overview-1",
                "name": "project_overview",
                "input": {"max_files": 20, "max_commands": 10, "max_checks": 10},
            }
        ],
        [
            {"type": "tool_call", "id": "read-1", "name": "read_file", "input": {"path": "calc.py"}},
            {"type": "tool_call", "id": "read-2", "name": "read_file", "input": {"path": "tests/test_calc.py"}},
        ],
        [
            {
                "type": "text",
                "text": (
                    "Plan: change calc.py so add returns left + right, then verify with "
                    "python -B -m unittest discover -s tests. Risk: keep the change scoped to calc.py."
                ),
            }
        ],
    ]


class V1DogfoodTests(unittest.TestCase):
    def test_v1_agent_can_read_repair_verify_commit_and_finish(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(v1_dogfood_responses())

            result = run_agent(
                "Fix the calculator test failure and commit the verified fix.",
                base_dir=root,
                client=client,
                max_iterations=14,
                approval_handler=approve_all,
            )
            git_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout
            head_message = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip()

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 5)

        observation_kinds = [item.kind for item in result.observations]
        self.assertIn("project_overview", observation_kinds)
        self.assertGreaterEqual(observation_kinds.count("read_file"), 2)
        run_commands = [item for item in result.observations if item.kind == "run_command"]
        self.assertEqual(len(run_commands), 2)
        self.assertNotEqual(run_commands[0].result.exit_code, 0)
        self.assertEqual(run_commands[1].result.exit_code, 0)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn("checkpoint_create", observation_kinds)
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("write_file"))
        self.assertLess(observation_kinds.index("write_file"), observation_kinds.index("git_stage"))
        self.assertLess(observation_kinds.index("git_stage"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("final_review"))

    def test_v1_agent_can_resume_after_interrupted_failure_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-resume-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            interrupted_client = DogfoodClient(interrupted_dogfood_responses())

            interrupted = run_agent(
                "Fix the calculator test failure and commit the verified fix.",
                base_dir=root,
                client=interrupted_client,
                max_iterations=3,
                approval_handler=approve_all,
            )
            selected_run_id, prior_context, resume_message = get_resume_context(
                interrupted.run_id,
                root,
                max_files=20,
                max_commands=5,
                max_checks=10,
                max_output_chars=1_000,
                max_text=4_000,
            )
            self.assertEqual(selected_run_id, interrupted.run_id)
            self.assertIsNotNone(prior_context, resume_message)
            assert prior_context is not None
            self.assertIn("python -B -m unittest discover -s tests", prior_context)

            resumed_client = DogfoodClient(resumed_dogfood_responses())
            resumed = run_agent(
                "Continue from the previous VibeAgent session and commit the verified fix.",
                base_dir=root,
                client=resumed_client,
                max_iterations=12,
                approval_handler=approve_all,
                prior_context=prior_context,
            )
            git_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout
            head_message = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip()

        initial_resumed_prompt = "\n".join(str(message.content) for message in resumed_client.messages[0])
        interrupted_observations = [item.kind for item in interrupted.observations]
        resumed_observations = [item.kind for item in resumed.observations]

        self.assertFalse(interrupted.success)
        self.assertIn("run_command", interrupted_observations)
        self.assertIn("Previous session context:", initial_resumed_prompt)
        self.assertIn("python -B -m unittest discover -s tests", initial_resumed_prompt)
        self.assertTrue(resumed.success)
        self.assertTrue(resumed.completion_ready)
        self.assertEqual(resumed.completion_blockers, [])
        self.assertEqual(resumed.pending_verification_checks, [])
        self.assertEqual(resumed.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after resume")
        self.assertIn("run_session_verification", resumed_observations)
        self.assertLess(resumed_observations.index("write_file"), resumed_observations.index("git_commit"))

    def test_v1_agent_can_complete_repair_with_claude_code_tool_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-claude-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(claude_compat_dogfood_responses())

            result = run_agent(
                "Fix the calculator test failure using Claude-style tools and commit the verified fix.",
                base_dir=root,
                client=client,
                max_iterations=14,
                approval_handler=approve_all,
            )
            git_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout
            head_message = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add via Claude aliases")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertGreaterEqual(observation_kinds.count("update_plan"), 4)
        self.assertGreaterEqual(observation_kinds.count("read_file"), 2)
        self.assertEqual(observation_kinds.count("run_command"), 2)
        self.assertIn("edit_file", observation_kinds)
        self.assertIn("session_plan", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "TodoWrite"', events_text)
        self.assertIn('"name": "Read"', events_text)
        self.assertIn('"name": "Bash"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        self.assertIn('"name": "TodoRead"', events_text)
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_can_delegate_read_only_investigation_before_repair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-delegate-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(delegated_dogfood_responses())

            result = run_agent(
                "Delegate the initial investigation, then fix the calculator test failure and commit.",
                base_dir=root,
                client=client,
                max_iterations=14,
                approval_handler=approve_all,
            )
            git_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout
            head_message = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        delegated = next(item for item in result.observations if item.kind == "delegate_task")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after delegation")
        self.assertTrue(delegated.ok)
        self.assertEqual(delegated.mode, "explore")
        self.assertEqual(delegated.tool_calls, ["Read", "Read"])
        self.assertIn("calc.py subtracts", delegated.summary)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "Task"', events_text)
        self.assertIn('"type": "subagent_tool_call"', events_text)
        self.assertIn('"name": "Read"', events_text)
        self.assertLess(observation_kinds.index("delegate_task"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_plan_mode_inspects_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-plan-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(plan_mode_dogfood_responses())

            result = run_agent(
                "Plan the calculator repair without changing files or running commands.",
                base_dir=root,
                client=client,
                max_iterations=3,
                approval_policy="plan",
            )
            git_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout
            calc_text = (root / "calc.py").read_text(encoding="utf-8")

        initial_prompt = "\n".join(str(message.content) for message in client.messages[0])
        exposed_names = {str(tool["name"]) for tools in client.tools for tool in tools}
        observation_kinds = [item.kind for item in result.observations]

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertIn("Plan mode is active", initial_prompt)
        self.assertIn("project_overview", observation_kinds)
        self.assertGreaterEqual(observation_kinds.count("read_file"), 2)
        self.assertNotIn("write_file", observation_kinds)
        self.assertNotIn("edit_file", observation_kinds)
        self.assertNotIn("run_command", observation_kinds)
        self.assertTrue({"write_file", "edit_file", "run_command", "git_commit"}.isdisjoint(exposed_names))
        self.assertIn("return left - right", calc_text)
        self.assertEqual(git_status, "")
        self.assertIn("Plan:", result.message)


if __name__ == "__main__":
    unittest.main()
