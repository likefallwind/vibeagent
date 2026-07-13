from __future__ import annotations

import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent import run_agent
from vibeagent.session_commands import get_resume_context, get_session_handoff_report
from vibeagent.session_handoff_details import extract_session_handoff_details
from vibeagent.types import ApprovalDecision, ApprovalRequest, AssistantResponse, ChatMessage, ContentBlock, WebFetchObservation


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


def git_worktree_status(root: Path) -> str:
    return subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout


def git_head_subject(root: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


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
                "id": "suggested-1",
                "name": "run_suggested_checks",
                "input": {"timeout_ms": 10_000, "max_checks": 5},
            },
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
            {"type": "tool_call", "id": "ls-1", "name": "LS", "input": {"path": ".", "max_depth": 2}},
            {"type": "tool_call", "id": "glob-1", "name": "Glob", "input": {"pattern": "*.py"}},
            {
                "type": "tool_call",
                "id": "grep-1",
                "name": "Grep",
                "input": {"pattern": "assertEqual", "glob": "*.py"},
            },
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


def claude_write_new_file_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect failing calculator code", "status": "in_progress"},
                        {"content": "Create helper module and wire implementation", "status": "pending"},
                        {"content": "Verify tests and review changes", "status": "pending"},
                        {"content": "Commit new helper-based fix", "status": "pending"},
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
                "input": {"command": "python -m unittest discover -s tests", "timeout": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect failing calculator code", "status": "completed"},
                        {"content": "Create helper module and wire implementation", "status": "in_progress"},
                        {"content": "Verify tests and review changes", "status": "pending"},
                        {"content": "Commit new helper-based fix", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "write-1",
                "name": "Write",
                "input": {"file_path": "math_helpers.py", "content": "def safe_add(left, right):\n    return left + right\n"},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "edit-1",
                "name": "Edit",
                "input": {
                    "file_path": "calc.py",
                    "old_string": "def add(left, right):\n    return left - right\n",
                    "new_string": "from math_helpers import safe_add\n\n\ndef add(left, right):\n    return safe_add(left, right)\n",
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-3",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect failing calculator code", "status": "completed"},
                        {"content": "Create helper module and wire implementation", "status": "completed"},
                        {"content": "Verify tests and review changes", "status": "in_progress"},
                        {"content": "Commit new helper-based fix", "status": "pending"},
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
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect failing calculator code", "status": "completed"},
                        {"content": "Create helper module and wire implementation", "status": "completed"},
                        {"content": "Verify tests and review changes", "status": "completed"},
                        {"content": "Commit new helper-based fix", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py", "math_helpers.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add with helper"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-5",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect failing calculator code", "status": "completed"},
                        {"content": "Create helper module and wire implementation", "status": "completed"},
                        {"content": "Verify tests and review changes", "status": "completed"},
                        {"content": "Commit new helper-based fix", "status": "completed"},
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
        [{"type": "text", "text": "Created a helper module with Write, wired the fix, verified tests, reviewed, and committed."}],
    ]


def background_process_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Start and inspect a background probe", "status": "in_progress"},
                        {"content": "Inspect calculator files", "status": "pending"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Stop probe, review, and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "bg-1",
                "name": "Bash",
                "input": {
                    "command": "python -u -c \"import time; print('ready', flush=True); time.sleep(30)\"",
                    "run_in_background": True,
                    "timeout": 10_000,
                    "max_output_chars": 1_000,
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "sleep-1",
                "name": "Bash",
                "input": {"command": "python -c \"import time; time.sleep(0.2)\"", "timeout": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "out-1",
                "name": "BashOutput",
                "input": {"bash_id": "111111111111", "filter": "ready", "max_output_chars": 2_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Start and inspect a background probe", "status": "completed"},
                        {"content": "Inspect calculator files", "status": "in_progress"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Stop probe, review, and commit", "status": "pending"},
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
                "id": "bash-1",
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
                        {"content": "Start and inspect a background probe", "status": "completed"},
                        {"content": "Inspect calculator files", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Stop probe, review, and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "stop-1", "name": "KillBash", "input": {"bash_id": "111111111111"}}],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after background probe"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Start and inspect a background probe", "status": "completed"},
                        {"content": "Inspect calculator files", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Stop probe, review, and commit", "status": "completed"},
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
        [{"type": "text", "text": "Started and inspected the background probe, stopped it, fixed the calculator, verified, reviewed, and committed."}],
    ]


def web_fetch_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Fetch the external calculator contract", "status": "in_progress"},
                        {"content": "Inspect local implementation and tests", "status": "pending"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Review and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "fetch-1",
                "name": "WebFetch",
                "input": {
                    "url": "https://docs.example.com/calculator-contract",
                    "prompt": "Extract the expected behavior for calc.add.",
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
                        {"content": "Fetch the external calculator contract", "status": "completed"},
                        {"content": "Inspect local implementation and tests", "status": "in_progress"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Review and commit", "status": "pending"},
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
                "id": "bash-1",
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
                        {"content": "Fetch the external calculator contract", "status": "completed"},
                        {"content": "Inspect local implementation and tests", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add using fetched contract"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Fetch the external calculator contract", "status": "completed"},
                        {"content": "Inspect local implementation and tests", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review and commit", "status": "completed"},
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
        [{"type": "text", "text": "Fetched the calculator contract, fixed add, verified, reviewed, and committed."}],
    ]


def diff_review_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "in_progress"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Review git diff before commit", "status": "pending"},
                        {"content": "Commit verified change", "status": "pending"},
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
                "id": "bash-1",
                "name": "Bash",
                "input": {"command": "python -m unittest discover -s tests", "timeout": 10_000},
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
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review git diff before commit", "status": "in_progress"},
                        {"content": "Commit verified change", "status": "pending"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "status-1", "name": "git_status", "input": {}}],
        [{"type": "tool_call", "id": "diff-1", "name": "git_diff", "input": {"path": "calc.py", "max_output_chars": 4_000}}],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [
            {
                "type": "tool_call",
                "id": "todo-3",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review git diff before commit", "status": "completed"},
                        {"content": "Commit verified change", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after diff review"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review git diff before commit", "status": "completed"},
                        {"content": "Commit verified change", "status": "completed"},
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
        [{"type": "text", "text": "Fixed the calculator, verified tests, reviewed git status and diff, final-reviewed, and committed."}],
    ]


def project_context_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Load project instructions and map", "status": "in_progress"},
                        {"content": "Inspect calculator implementation", "status": "pending"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Review and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "instructions-1",
                "name": "project_instructions",
                "input": {"max_files": 5, "max_bytes": 2_000},
            },
            {
                "type": "tool_call",
                "id": "map-1",
                "name": "repo_map",
                "input": {"max_depth": 2, "max_files": 20, "max_symbols": 20},
            },
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Load project instructions and map", "status": "completed"},
                        {"content": "Inspect calculator implementation", "status": "in_progress"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Review and commit", "status": "pending"},
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
                "id": "bash-1",
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
                        {"content": "Load project instructions and map", "status": "completed"},
                        {"content": "Inspect calculator implementation", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after project context"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Load project instructions and map", "status": "completed"},
                        {"content": "Inspect calculator implementation", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review and commit", "status": "completed"},
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
        [{"type": "text", "text": "Loaded project instructions and repo map, fixed the calculator, verified, reviewed, and committed."}],
    ]


def focused_tests_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator implementation", "status": "in_progress"},
                        {"content": "Patch calculator behavior", "status": "pending"},
                        {"content": "Find and run focused tests", "status": "pending"},
                        {"content": "Review and commit", "status": "pending"},
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
                        {"content": "Inspect calculator implementation", "status": "completed"},
                        {"content": "Patch calculator behavior", "status": "completed"},
                        {"content": "Find and run focused tests", "status": "in_progress"},
                        {"content": "Review and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "related-1", "name": "related_tests", "input": {"paths": ["calc.py"]}}],
        [
            {
                "type": "tool_call",
                "id": "focused-1",
                "name": "focused_test_commands",
                "input": {"paths": ["calc.py"], "max_commands": 5},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "run-focused-1",
                "name": "run_focused_test_commands",
                "input": {"paths": ["calc.py"], "max_commands": 5, "timeout_ms": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-3",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator implementation", "status": "completed"},
                        {"content": "Patch calculator behavior", "status": "completed"},
                        {"content": "Find and run focused tests", "status": "completed"},
                        {"content": "Review and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after focused tests"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator implementation", "status": "completed"},
                        {"content": "Patch calculator behavior", "status": "completed"},
                        {"content": "Find and run focused tests", "status": "completed"},
                        {"content": "Review and commit", "status": "completed"},
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
        [{"type": "text", "text": "Fixed the calculator, found and ran focused tests, reviewed, and committed."}],
    ]


def checkpoint_safety_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Create a rollback checkpoint", "status": "in_progress"},
                        {"content": "Patch calculator behavior", "status": "pending"},
                        {"content": "Inspect checkpoint safety and verify", "status": "pending"},
                        {"content": "Review and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "checkpoint-1", "name": "checkpoint_create", "input": {"label": "before calculator edit"}}],
        [{"type": "tool_call", "id": "checkpoint-list-1", "name": "checkpoint_list", "input": {"max_entries": 5}}],
        [
            {"type": "tool_call", "id": "read-1", "name": "Read", "input": {"file_path": "calc.py"}},
            {"type": "tool_call", "id": "read-2", "name": "Read", "input": {"file_path": "tests/test_calc.py"}},
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
                        {"content": "Create a rollback checkpoint", "status": "completed"},
                        {"content": "Patch calculator behavior", "status": "completed"},
                        {"content": "Inspect checkpoint safety and verify", "status": "in_progress"},
                        {"content": "Review and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "checkpoint-status-1", "name": "checkpoint_status", "input": {"checkpoint_id": "latest"}}],
        [{"type": "tool_call", "id": "checkpoint-restore-check-1", "name": "check_checkpoint_restore", "input": {"checkpoint_id": "latest"}}],
        [
            {
                "type": "tool_call",
                "id": "bash-1",
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
                        {"content": "Create a rollback checkpoint", "status": "completed"},
                        {"content": "Patch calculator behavior", "status": "completed"},
                        {"content": "Inspect checkpoint safety and verify", "status": "completed"},
                        {"content": "Review and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add with checkpoint safety"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Create a rollback checkpoint", "status": "completed"},
                        {"content": "Patch calculator behavior", "status": "completed"},
                        {"content": "Inspect checkpoint safety and verify", "status": "completed"},
                        {"content": "Review and commit", "status": "completed"},
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
        [{"type": "text", "text": "Created a rollback checkpoint, patched and verified the calculator, checked checkpoint safety, reviewed, and committed."}],
    ]


def session_handoff_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "in_progress"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Review and commit", "status": "pending"},
                        {"content": "Generate session handoff", "status": "pending"},
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
                "id": "bash-1",
                "name": "Bash",
                "input": {"command": "python -m unittest discover -s tests", "timeout": 10_000},
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
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review and commit", "status": "in_progress"},
                        {"content": "Generate session handoff", "status": "pending"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add before handoff"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-3",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review and commit", "status": "completed"},
                        {"content": "Generate session handoff", "status": "in_progress"},
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
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator code and test", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Review and commit", "status": "completed"},
                        {"content": "Generate session handoff", "status": "completed"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "handoff-1",
                "name": "session_handoff",
                "input": {"max_files": 10, "max_commands": 10, "max_checks": 20, "max_text": 800},
            }
        ],
        [{"type": "text", "text": "Fixed, verified, reviewed, committed, and generated a session handoff."}],
    ]


def clarification_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Clarify expected calculator behavior", "status": "in_progress"},
                        {"content": "Patch calculator implementation", "status": "pending"},
                        {"content": "Verify and commit", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "ask-1",
                "name": "AskUserQuestion",
                "input": {
                    "prompt": "Should calc.add add numbers or preserve the current subtraction behavior?",
                    "options": ["addition", "subtraction"],
                    "allow_free_text": False,
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
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Clarify expected calculator behavior", "status": "completed"},
                        {"content": "Patch calculator implementation", "status": "in_progress"},
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
                "id": "bash-1",
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
                        {"content": "Clarify expected calculator behavior", "status": "completed"},
                        {"content": "Patch calculator implementation", "status": "completed"},
                        {"content": "Verify and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after clarification"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Clarify expected calculator behavior", "status": "completed"},
                        {"content": "Patch calculator implementation", "status": "completed"},
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
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "text", "text": "Clarified addition behavior, fixed calc.add, verified tests, final-reviewed, and committed."}],
    ]


def skill_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "skills-1",
                "name": "project_skills",
                "input": {"max_skills": 10},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "skill-1",
                "name": "skill",
                "input": {"name": "calculator-repair", "max_bytes": 20_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Load calculator repair skill", "status": "completed"},
                        {"content": "Inspect calculator failure", "status": "in_progress"},
                        {"content": "Patch and verify implementation", "status": "pending"},
                        {"content": "Final review and commit", "status": "pending"},
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
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Load calculator repair skill", "status": "completed"},
                        {"content": "Inspect calculator failure", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "in_progress"},
                        {"content": "Final review and commit", "status": "pending"},
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
                "id": "bash-1",
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
                        {"content": "Load calculator repair skill", "status": "completed"},
                        {"content": "Inspect calculator failure", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Final review and commit", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add with project skill"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-4",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Load calculator repair skill", "status": "completed"},
                        {"content": "Inspect calculator failure", "status": "completed"},
                        {"content": "Patch and verify implementation", "status": "completed"},
                        {"content": "Final review and commit", "status": "completed"},
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
        [{"type": "text", "text": "Loaded the project skill, followed its calculator repair guidance, verified, reviewed, and committed."}],
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


def profiled_delegated_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "delegate-1",
                "name": "Task",
                "input": {
                    "prompt": "Inspect calc.py and its test to identify the failing behavior.",
                    "description": "Use the project calc-reviewer profile for a bounded read-only investigation.",
                    "subagent_type": "calc-reviewer",
                    "max_iterations": 2,
                },
            }
        ],
        [
            {"type": "tool_call", "id": "read-1", "name": "Read", "input": {"file_path": "calc.py"}},
            {"type": "tool_call", "id": "read-2", "name": "Read", "input": {"file_path": "tests/test_calc.py"}},
        ],
        [{"type": "text", "text": "Profiled review: test expects add(2, 3) == 5, but calc.py subtracts on line 2."}],
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Use profiled delegated investigation", "status": "completed"},
                        {"content": "Patch add implementation", "status": "in_progress"},
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
                "id": "bash-1",
                "name": "Bash",
                "input": {
                    "command": "PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests",
                    "timeout": 10_000,
                },
            }
        ],
        [{"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}}],
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add after profiled delegation"}}],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Use profiled delegated investigation", "status": "completed"},
                        {"content": "Patch add implementation", "status": "completed"},
                        {"content": "Verify and commit", "status": "completed"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "suggested-1",
                "name": "run_suggested_checks",
                "input": {"timeout_ms": 10_000, "max_checks": 5},
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
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "text", "text": "Used calc-reviewer profile, fixed the implementation, final-reviewed, verified tests, and committed."}],
    ]


def code_delegated_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Delegate the calculator repair to a code subagent", "status": "in_progress"},
                        {"content": "Audit the delegated result", "status": "pending"},
                    ]
                },
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "delegate-1",
                "name": "Task",
                "input": {
                    "prompt": "Fix the calculator add implementation, verify tests, and commit the result.",
                    "description": "Use code-mode delegation for the full repair workflow.",
                    "mode": "code",
                    "max_iterations": 8,
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
                "input": {
                    "command": "PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests",
                    "timeout": 10_000,
                },
            }
        ],
        [
            {"type": "tool_call", "id": "stage-1", "name": "git_stage", "input": {"paths": ["calc.py"]}},
            {
                "type": "tool_call",
                "id": "commit-1",
                "name": "git_commit",
                "input": {"message": "Fix calculator add from code subagent"},
            },
        ],
        [
            {
                "type": "tool_call",
                "id": "suggested-1",
                "name": "run_suggested_checks",
                "input": {"timeout_ms": 10_000, "max_checks": 5},
            },
            {
                "type": "tool_call",
                "id": "verify-1",
                "name": "run_session_verification",
                "input": {"include_pending": True, "include_failed": True, "timeout_ms": 10_000},
            }
        ],
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "text", "text": "Code subagent fixed calc.py, verified tests, committed, and final-reviewed."}],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Delegate the calculator repair to a code subagent", "status": "completed"},
                        {"content": "Audit the delegated result", "status": "in_progress"},
                    ]
                },
            }
        ],
        [{"type": "tool_call", "id": "review-parent-1", "name": "final_review", "input": {}}],
        [
            {
                "type": "tool_call",
                "id": "todo-3",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Delegate the calculator repair to a code subagent", "status": "completed"},
                        {"content": "Audit the delegated result", "status": "completed"},
                    ]
                },
            }
        ],
        [{"type": "text", "text": "Delegated code subagent fixed, verified, final-reviewed, and committed the calculator."}],
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
                "type": "tool_call",
                "id": "exit-plan-1",
                "name": "ExitPlanMode",
                "input": {
                    "plan": (
                        "Change calc.py so add returns left + right, then verify with "
                        "python -B -m unittest discover -s tests. Keep the change scoped to calc.py."
                    )
                },
            }
        ],
        [{"type": "text", "text": "Plan recorded with ExitPlanMode; no files, commands, or commits were changed."}],
    ]


def multi_edit_dogfood_responses() -> list[list[ContentBlock]]:
    return [
        [
            {
                "type": "tool_call",
                "id": "todo-1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator implementation and test", "status": "in_progress"},
                        {"content": "Reproduce the failure", "status": "pending"},
                        {"content": "Patch with Claude MultiEdit", "status": "pending"},
                        {"content": "Verify, review, and commit", "status": "pending"},
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
                "input": {"command": "python -m unittest discover -s tests", "timeout": 10_000},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "multi-edit-1",
                "name": "MultiEdit",
                "input": {
                    "file_path": "calc.py",
                    "edits": [
                        {
                            "old_string": "def add(left, right):\n",
                            "new_string": "def add(left, right):\n    \"\"\"Return the arithmetic sum.\"\"\"\n",
                        },
                        {"old_string": "return left - right", "new_string": "return left + right", "replace_all": True},
                    ],
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
        [{"type": "tool_call", "id": "commit-1", "name": "git_commit", "input": {"message": "Fix calculator add with MultiEdit"}}],
        [
            {
                "type": "tool_call",
                "id": "suggested-1",
                "name": "run_suggested_checks",
                "input": {"timeout_ms": 10_000, "max_checks": 5},
            }
        ],
        [
            {
                "type": "tool_call",
                "id": "todo-2",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {"content": "Inspect calculator implementation and test", "status": "completed"},
                        {"content": "Reproduce the failure", "status": "completed"},
                        {"content": "Patch with Claude MultiEdit", "status": "completed"},
                        {"content": "Verify, review, and commit", "status": "completed"},
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
        [{"type": "tool_call", "id": "review-1", "name": "final_review", "input": {}}],
        [{"type": "text", "text": "Fixed the calculator with MultiEdit, verified tests, final-reviewed, and committed."}],
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
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)

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
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)

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
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
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
        self.assertIn("list_tree", observation_kinds)
        self.assertIn("glob", observation_kinds)
        self.assertIn("search", observation_kinds)
        self.assertGreaterEqual(observation_kinds.count("read_file"), 2)
        self.assertEqual(observation_kinds.count("run_command"), 2)
        self.assertIn("edit_file", observation_kinds)
        self.assertIn("session_plan", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "TodoWrite"', events_text)
        self.assertIn('"name": "LS"', events_text)
        self.assertIn('"name": "Glob"', events_text)
        self.assertIn('"name": "Grep"', events_text)
        self.assertIn('"name": "Read"', events_text)
        self.assertIn('"name": "Bash"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        self.assertIn('"name": "TodoRead"', events_text)
        self.assertLess(observation_kinds.index("list_tree"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("glob"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("search"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_can_create_new_file_with_claude_write_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-write-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(claude_write_new_file_dogfood_responses())

            result = run_agent(
                "Fix the calculator by creating a helper module with Claude Write, verify it, and commit.",
                base_dir=root,
                client=client,
                max_iterations=16,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            helper_text = (root / "math_helpers.py").read_text(encoding="utf-8")
            calc_text = (root / "calc.py").read_text(encoding="utf-8")
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        run_commands = [item for item in result.observations if item.kind == "run_command"]

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add with helper")
        self.assertEqual(helper_text, "def safe_add(left, right):\n    return left + right\n")
        self.assertIn("from math_helpers import safe_add", calc_text)
        self.assertIn("return safe_add(left, right)", calc_text)
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertEqual(len(run_commands), 2)
        self.assertNotEqual(run_commands[0].result.exit_code, 0)
        self.assertEqual(run_commands[1].result.exit_code, 0)
        self.assertIn("write_file", observation_kinds)
        self.assertIn("edit_file", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn("git_stage", observation_kinds)
        self.assertIn("git_commit", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "Write"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        self.assertIn('"paths": ["calc.py", "math_helpers.py"]', events_text)
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("write_file"))
        self.assertLess(observation_kinds.index("write_file"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_stage"))
        self.assertLess(observation_kinds.index("git_stage"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_can_manage_claude_background_process_before_repair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-background-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(background_process_dogfood_responses())
            fixed_process_uuid = uuid.UUID("11111111-1111-2222-2222-222222222222")

            with patch("vibeagent.process_runtime.uuid.uuid4", return_value=fixed_process_uuid):
                result = run_agent(
                    "Start a background readiness probe, inspect it, then fix the calculator test failure and commit.",
                    base_dir=root,
                    client=client,
                    max_iterations=17,
                    approval_handler=approve_all,
                )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        run_command_positions = [index for index, kind in enumerate(observation_kinds) if kind == "run_command"]
        read_process = next(item for item in result.observations if item.kind == "read_process")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after background probe")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertIn("start_command", observation_kinds)
        self.assertIn("read_process", observation_kinds)
        self.assertIn("stop_process", observation_kinds)
        self.assertIn("edit_file", observation_kinds)
        self.assertIn("run_command", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertEqual(read_process.process_id, "111111111111")
        self.assertIn("ready", read_process.stdout)
        self.assertIn('"name": "Bash"', events_text)
        self.assertIn('"name": "BashOutput"', events_text)
        self.assertIn('"name": "KillBash"', events_text)
        self.assertLess(observation_kinds.index("start_command"), observation_kinds.index("read_process"))
        self.assertLess(observation_kinds.index("read_process"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("read_file"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), run_command_positions[-1])
        self.assertLess(run_command_positions[-1], observation_kinds.index("stop_process"))
        self.assertLess(observation_kinds.index("stop_process"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_can_use_web_fetch_before_repair(self) -> None:
        fetched_contract = WebFetchObservation(
            kind="web_fetch",
            ok=True,
            url="https://docs.example.com/calculator-contract",
            final_url="https://docs.example.com/calculator-contract",
            status=200,
            content_type="text/html",
            title="Calculator Contract",
            text="The calc.add(left, right) function must return the arithmetic sum of both arguments.",
            text_truncated=False,
            max_text_chars=20_000,
            error=None,
            message="Fetched public document.",
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-webfetch-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(web_fetch_dogfood_responses())

            with patch("vibeagent.runtime_action_executor.fetch_public_document", return_value=fetched_contract) as fetch_public_document:
                result = run_agent(
                    "Fetch the external calculator contract, then fix and commit the verified implementation.",
                    base_dir=root,
                    client=client,
                    max_iterations=15,
                    approval_handler=approve_all,
                )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        web_fetch = next(item for item in result.observations if item.kind == "web_fetch")
        next_turn_payload = str(client.messages[2][-1].content)

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add using fetched contract")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        fetch_public_document.assert_called_once_with(
            "https://docs.example.com/calculator-contract",
            timeout_ms=10_000,
            max_text_chars=20_000,
        )
        self.assertEqual(web_fetch.prompt, "Extract the expected behavior for calc.add.")
        self.assertIn("arithmetic sum", web_fetch.text)
        self.assertIn("arithmetic sum", next_turn_payload)
        self.assertIn("Extract the expected behavior for calc.add.", next_turn_payload)
        self.assertIn("read_file", observation_kinds)
        self.assertIn("edit_file", observation_kinds)
        self.assertIn("run_command", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "WebFetch"', events_text)
        self.assertLess(observation_kinds.index("web_fetch"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("read_file"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("run_command"))
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_reviews_git_diff_before_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-diff-review-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(diff_review_dogfood_responses())

            result = run_agent(
                "Fix the calculator test failure, review the git diff, then commit the verified fix.",
                base_dir=root,
                client=client,
                max_iterations=15,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        status_observation = next(item for item in result.observations if item.kind == "git_status")
        diff_observation = next(item for item in result.observations if item.kind == "git_diff")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after diff review")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertIn("calc.py", status_observation.status)
        self.assertEqual(diff_observation.path, "calc.py")
        self.assertIn("-    return left - right", diff_observation.diff)
        self.assertIn("+    return left + right", diff_observation.diff)
        self.assertIn("run_command", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "git_status"', events_text)
        self.assertIn('"name": "git_diff"', events_text)
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("run_command"))
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("git_status"))
        self.assertLess(observation_kinds.index("git_status"), observation_kinds.index("git_diff"))
        self.assertLess(observation_kinds.index("git_diff"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_stage"))
        self.assertLess(observation_kinds.index("git_stage"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_loads_project_instructions_and_repo_map_before_repair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-project-context-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            (root / "AGENTS.md").write_text(
                "Use unittest for verification and keep calculator fixes scoped to calc.py.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "AGENTS.md"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "add project instructions"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = DogfoodClient(project_context_dogfood_responses())

            result = run_agent(
                "Load project instructions and repo map, then fix the calculator test failure and commit.",
                base_dir=root,
                client=client,
                max_iterations=15,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        instructions = next(item for item in result.observations if item.kind == "project_instructions")
        repo_map = next(item for item in result.observations if item.kind == "repo_map")
        after_context_prompt = "\n".join(str(message.content) for message in client.messages[2])

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after project context")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertTrue(instructions.ok)
        self.assertIn("AGENTS.md", [source.path for source in instructions.files])
        self.assertIn("keep calculator fixes scoped to calc.py", instructions.text)
        self.assertIn("keep calculator fixes scoped to calc.py", after_context_prompt)
        self.assertTrue(repo_map.ok)
        self.assertIn("calc.py", repo_map.files)
        self.assertIn("tests/test_calc.py", repo_map.files)
        self.assertIn("project_instructions", observation_kinds)
        self.assertIn("repo_map", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn('"name": "project_instructions"', events_text)
        self.assertIn('"name": "repo_map"', events_text)
        self.assertLess(observation_kinds.index("project_instructions"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("repo_map"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("read_file"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("run_command"))
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_finds_and_runs_focused_tests_before_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-focused-tests-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(focused_tests_dogfood_responses())

            result = run_agent(
                "Fix the calculator test failure, find focused tests, run them, and commit.",
                base_dir=root,
                client=client,
                max_iterations=16,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        related = next(item for item in result.observations if item.kind == "related_tests")
        focused = next(item for item in result.observations if item.kind == "focused_test_commands")
        run_focused = next(item for item in result.observations if item.kind == "run_focused_test_commands")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after focused tests")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertTrue(related.ok)
        self.assertIn("tests/test_calc.py", [candidate.test_path for candidate in related.candidates])
        self.assertTrue(focused.ok)
        self.assertIn("tests/test_calc.py", [command.test_path for command in focused.commands])
        self.assertTrue(run_focused.ok)
        self.assertIn("tests/test_calc.py", [command.test_path for command in run_focused.focused_commands])
        self.assertGreaterEqual(len(run_focused.results), 1)
        self.assertTrue(all(result_item.exit_code == 0 for result_item in run_focused.results))
        self.assertIn("final_review", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "related_tests"', events_text)
        self.assertIn('"name": "focused_test_commands"', events_text)
        self.assertIn('"name": "run_focused_test_commands"', events_text)
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("related_tests"))
        self.assertLess(observation_kinds.index("related_tests"), observation_kinds.index("focused_test_commands"))
        self.assertLess(observation_kinds.index("focused_test_commands"), observation_kinds.index("run_focused_test_commands"))
        self.assertLess(observation_kinds.index("run_focused_test_commands"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_creates_and_checks_checkpoint_before_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-checkpoint-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(checkpoint_safety_dogfood_responses())

            result = run_agent(
                "Create a rollback checkpoint, fix the calculator test failure, verify checkpoint safety, and commit.",
                base_dir=root,
                client=client,
                max_iterations=17,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        created_checkpoints = [item for item in result.observations if item.kind == "checkpoint_create" and item.checkpoint]
        listed = next(item for item in result.observations if item.kind == "checkpoint_list")
        status = next(item for item in result.observations if item.kind == "checkpoint_status")
        restore_check = next(item for item in result.observations if item.kind == "check_checkpoint_restore")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add with checkpoint safety")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertGreaterEqual(len(created_checkpoints), 1)
        self.assertIn("before calculator edit", [item.checkpoint.label for item in created_checkpoints if item.checkpoint])
        self.assertTrue(listed.ok)
        self.assertGreaterEqual(listed.total, 1)
        self.assertFalse(status.matches)
        self.assertGreaterEqual(status.current_changed_files, 1)
        self.assertTrue(restore_check.can_restore)
        self.assertTrue(restore_check.ok)
        self.assertIn("run_command", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn('"name": "checkpoint_create"', events_text)
        self.assertIn('"name": "checkpoint_list"', events_text)
        self.assertIn('"name": "checkpoint_status"', events_text)
        self.assertIn('"name": "check_checkpoint_restore"', events_text)
        self.assertLess(observation_kinds.index("checkpoint_create"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("checkpoint_status"))
        self.assertLess(observation_kinds.index("checkpoint_status"), observation_kinds.index("check_checkpoint_restore"))
        self.assertLess(observation_kinds.index("check_checkpoint_restore"), observation_kinds.index("run_command"))
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))

    def test_v1_agent_generates_session_handoff_after_verified_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-handoff-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(session_handoff_dogfood_responses())

            result = run_agent(
                "Fix the calculator test failure, commit it, and generate a session handoff.",
                base_dir=root,
                client=client,
                max_iterations=17,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")
            completed_handoff_report = get_session_handoff_report(
                root,
                result.run_id,
                max_files=10,
                max_commands=10,
                max_checks=20,
                max_text=800,
            )
            completed_handoff = extract_session_handoff_details(completed_handoff_report)

        observation_kinds = [item.kind for item in result.observations]
        handoff = next(item for item in result.observations if item.kind == "session_handoff")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add before handoff")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertTrue(handoff.ok)
        self.assertEqual(handoff.run_id, result.run_id)
        self.assertFalse(handoff.ready)
        self.assertEqual(handoff.blockers, ["session status is incomplete"])
        self.assertEqual(handoff.pending_count, 0)
        self.assertEqual(handoff.failed_count, 0)
        self.assertGreaterEqual(handoff.verified_count, 1)
        self.assertTrue(completed_handoff.ready)
        self.assertEqual(completed_handoff.status, "ready")
        self.assertEqual(completed_handoff.blockers, [])
        self.assertEqual(completed_handoff.pending_count, 0)
        self.assertEqual(completed_handoff.failed_count, 0)
        self.assertGreaterEqual(completed_handoff.verified_count, 1)
        self.assertIn("Session handoff:", handoff.handoff)
        self.assertIn("python -m unittest discover -s tests", handoff.handoff)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn('"name": "session_handoff"', events_text)
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("run_command"))
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))
        self.assertLess(observation_kinds.index("run_session_verification"), observation_kinds.index("session_handoff"))

    def test_v1_agent_can_clarify_then_repair_verify_and_commit(self) -> None:
        user_questions = []
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-clarification-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(clarification_dogfood_responses())

            result = run_agent(
                "Clarify the expected calculator behavior if needed, then fix and commit.",
                base_dir=root,
                client=client,
                max_iterations=14,
                approval_handler=approve_all,
                user_input_handler=lambda request: user_questions.append(request) or "addition",
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]
        ask_observation = next(item for item in result.observations if item.kind == "ask_user")
        second_turn_payload = str(client.messages[2][-1].content)

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after clarification")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 3)
        self.assertEqual(len(user_questions), 1)
        self.assertIn("calc.add add numbers", user_questions[0].question)
        self.assertEqual(user_questions[0].options, ["addition", "subtraction"])
        self.assertFalse(user_questions[0].allow_free_text)
        self.assertEqual(ask_observation.answer, "addition")
        self.assertIn('"answer": "addition"', second_turn_payload)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn('"name": "AskUserQuestion"', events_text)
        self.assertIn('"type": "user_input_requested"', events_text)
        self.assertIn('"type": "user_input_answered"', events_text)
        self.assertLess(observation_kinds.index("ask_user"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("read_file"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_session_verification"))
        self.assertLess(observation_kinds.index("run_session_verification"), observation_kinds.index("final_review"))

    def test_v1_agent_can_load_project_skill_then_repair_verify_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-skill-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            skill_dir = root / ".claude" / "skills" / "calculator-repair"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(
                "---\n"
                "name: calculator-repair\n"
                "description: Repair calculator behavior safely\n"
                "---\n\n"
                "SKILL_CALCULATOR_REPAIR_INSTRUCTION: inspect calc.py and tests, make the smallest fix, run unittest, final-review before commit.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".claude/skills/calculator-repair/SKILL.md"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "add calculator repair skill"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = DogfoodClient(skill_dogfood_responses())

            result = run_agent(
                "Use a relevant project skill to fix the calculator test failure and commit.",
                base_dir=root,
                client=client,
                max_iterations=16,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        initial_prompt = "\n".join(str(message.content) for message in client.messages[0])
        after_skill_prompt = "\n".join(str(message.content) for message in client.messages[2])
        observation_kinds = [item.kind for item in result.observations]
        skill_observation = next(item for item in result.observations if item.kind == "skill")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add with project skill")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertIn("project_skills", observation_kinds)
        self.assertIn("skill", observation_kinds)
        self.assertEqual(skill_observation.name, "calculator-repair")
        self.assertIn("Repair calculator behavior safely", skill_observation.description)
        self.assertNotIn("SKILL_CALCULATOR_REPAIR_INSTRUCTION", initial_prompt)
        self.assertIn("SKILL_CALCULATOR_REPAIR_INSTRUCTION", after_skill_prompt)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn('"name": "project_skills"', events_text)
        self.assertIn('"name": "skill"', events_text)
        self.assertLess(observation_kinds.index("project_skills"), observation_kinds.index("skill"))
        self.assertLess(observation_kinds.index("skill"), observation_kinds.index("read_file"))
        self.assertLess(observation_kinds.index("read_file"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("final_review"))
        self.assertLess(observation_kinds.index("final_review"), observation_kinds.index("git_commit"))
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
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
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

    def test_v1_agent_can_delegate_with_project_agent_profile_before_repair(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-profiled-delegate-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            agent_dir = root / ".claude" / "agents"
            agent_dir.mkdir(parents=True)
            agent_path = agent_dir / "calc-reviewer.md"
            agent_path.write_text(
                "---\n"
                "name: calc-reviewer\n"
                "description: Reviews calculator failures\n"
                "mode: explore\n"
                "tools: Read\n"
                "---\n\n"
                "PROFILED_CALC_REVIEWER_INSTRUCTION: inspect calculator code and test evidence only.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".claude/agents/calc-reviewer.md"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "add calc reviewer profile"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            client = DogfoodClient(profiled_delegated_dogfood_responses())

            result = run_agent(
                "Delegate the initial investigation to the calc-reviewer profile, then fix and commit.",
                base_dir=root,
                client=client,
                max_iterations=14,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        first_subagent_prompt = str(client.messages[1][0].content)
        observation_kinds = [item.kind for item in result.observations]
        delegated = next(item for item in result.observations if item.kind == "delegate_task")

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add after profiled delegation")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 3)
        self.assertTrue(delegated.ok)
        self.assertEqual(delegated.mode, "explore")
        self.assertEqual(delegated.agent, "calc-reviewer")
        self.assertEqual(delegated.tool_calls, ["Read", "Read"])
        self.assertIn("Profiled review", delegated.summary)
        self.assertIn("PROFILED_CALC_REVIEWER_INSTRUCTION", first_subagent_prompt)
        self.assertIn("run_suggested_checks", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn('"agent": "calc-reviewer"', events_text)
        self.assertIn('"name": "Task"', events_text)
        self.assertIn('"type": "subagent_tool_call"', events_text)
        self.assertLess(observation_kinds.index("delegate_task"), observation_kinds.index("edit_file"))
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_suggested_checks"))
        self.assertLess(observation_kinds.index("run_suggested_checks"), observation_kinds.index("run_session_verification"))
        self.assertLess(observation_kinds.index("run_session_verification"), observation_kinds.index("final_review"))

    def test_v1_agent_can_delegate_code_subagent_repair_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-code-delegate-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(code_delegated_dogfood_responses())

            result = run_agent(
                "Delegate a code subagent to fix the calculator test failure and commit.",
                base_dir=root,
                client=client,
                max_iterations=8,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            calc_text = (root / "calc.py").read_text(encoding="utf-8")
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
        self.assertEqual(head_message, "Fix calculator add from code subagent")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 2)
        self.assertIn("return left + right", calc_text)
        self.assertTrue(delegated.ok)
        self.assertEqual(delegated.mode, "code")
        self.assertEqual(
            delegated.tool_calls,
            [
                "Read",
                "Read",
                "Bash",
                "Edit",
                "Bash",
                "git_stage",
                "git_commit",
                "run_suggested_checks",
                "run_session_verification",
                "final_review",
            ],
        )
        self.assertGreaterEqual(observation_kinds.count("read_file"), 2)
        self.assertEqual(observation_kinds.count("run_command"), 2)
        self.assertGreaterEqual(observation_kinds.count("update_plan"), 3)
        self.assertIn("edit_file", observation_kinds)
        self.assertIn("git_commit", observation_kinds)
        self.assertIn("run_suggested_checks", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertGreaterEqual(observation_kinds.count("final_review"), 2)
        self.assertIn('"name": "Task"', events_text)
        self.assertIn('"mode": "code"', events_text)
        self.assertIn('"type": "subagent_tool_call"', events_text)
        self.assertIn('"name": "Edit"', events_text)
        self.assertLess(observation_kinds.index("edit_file"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_suggested_checks"))
        self.assertLess(observation_kinds.index("run_suggested_checks"), observation_kinds.index("run_session_verification"))
        self.assertLess(observation_kinds.index("run_session_verification"), observation_kinds.index("delegate_task"))

    def test_v1_agent_plan_mode_inspects_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-plan-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(plan_mode_dogfood_responses())

            result = run_agent(
                "Plan the calculator repair without changing files or running commands.",
                base_dir=root,
                client=client,
                max_iterations=4,
                approval_policy="plan",
            )
            git_status = git_worktree_status(root)
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
        self.assertIn("ExitPlanMode", exposed_names)
        self.assertIn("update_plan", observation_kinds)
        self.assertEqual([item.status for item in result.plan], ["completed"])
        self.assertIn("return left - right", calc_text)
        self.assertEqual(git_status, "")
        self.assertIn("ExitPlanMode", result.message)

    def test_v1_agent_can_apply_claude_multi_edit_and_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-v1-multiedit-dogfood-") as base:
            root = Path(base)
            init_broken_calculator_repo(root)
            client = DogfoodClient(multi_edit_dogfood_responses())

            result = run_agent(
                "Fix the calculator test failure using Claude MultiEdit and commit the verified fix.",
                base_dir=root,
                client=client,
                max_iterations=13,
                approval_handler=approve_all,
            )
            git_status = git_worktree_status(root)
            head_message = git_head_subject(root)
            calc_text = (root / "calc.py").read_text(encoding="utf-8")
            events_path = root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl"
            events_text = events_path.read_text(encoding="utf-8")

        observation_kinds = [item.kind for item in result.observations]

        self.assertTrue(result.success)
        self.assertTrue(result.completion_ready)
        self.assertEqual(result.completion_blockers, [])
        self.assertEqual(result.pending_verification_checks, [])
        self.assertEqual(result.failed_verification_checks, [])
        self.assertEqual(git_status, "")
        self.assertEqual(head_message, "Fix calculator add with MultiEdit")
        self.assertEqual([item.status for item in result.plan], ["completed"] * 4)
        self.assertIn('"""Return the arithmetic sum."""', calc_text)
        self.assertIn("return left + right", calc_text)
        self.assertGreaterEqual(observation_kinds.count("read_file"), 2)
        self.assertGreaterEqual(observation_kinds.count("update_plan"), 2)
        self.assertEqual(observation_kinds.count("run_command"), 2)
        self.assertIn("multi_edit_file", observation_kinds)
        self.assertIn("run_suggested_checks", observation_kinds)
        self.assertIn("run_session_verification", observation_kinds)
        self.assertIn("final_review", observation_kinds)
        self.assertIn('"name": "MultiEdit"', events_text)
        self.assertLess(observation_kinds.index("run_command"), observation_kinds.index("multi_edit_file"))
        self.assertLess(observation_kinds.index("multi_edit_file"), observation_kinds.index("git_commit"))
        self.assertLess(observation_kinds.index("git_commit"), observation_kinds.index("run_suggested_checks"))
        self.assertLess(observation_kinds.index("run_suggested_checks"), observation_kinds.index("run_session_verification"))
        self.assertLess(observation_kinds.index("run_session_verification"), observation_kinds.index("final_review"))


if __name__ == "__main__":
    unittest.main()
