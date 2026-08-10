from __future__ import annotations

import subprocess
from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.actions import AGENT_TOOL_DEFINITIONS, execute_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.background_delegate_runtime import start_background_delegate_task
from vibeagent.subagent_transcripts import SubagentWorktreeRecord, read_subagent_transcript
from vibeagent.subagent_worktrees import SubagentWorktreeError, prepare_subagent_worktree
from vibeagent.types import ApprovalDecision, AssistantResponse, ContentBlock
from vibeagent.workspace import create_run_workspace
from vibeagent.dynamic_agent_profiles import parse_dynamic_agent_profiles


class IsolationClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _repository(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "VibeAgent Test")
    _git(root, "config", "user.email", "vibeagent@example.test")
    root.joinpath("README.md").write_text("# Test\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-qm", "initial")


def _execute(workspace, action, client, *, subagent_id="delegate-1-1", resume=None, followup=None):
    return execute_delegate_task_action(
        workspace,
        action,
        client,
        parent_iteration=1,
        subagent_id=subagent_id,
        max_output_tokens=2048,
        model_retries=0,
        model_retry_delay_ms=0,
        model_timeout_ms=10_000,
        command_timeout_ms=10_000,
        logger=None,
        approval_handler=lambda _request: ApprovalDecision(approved=True, message="approved"),
        resume_transcript=resume,
        followup_message=followup,
    )


class SubagentWorktreeIsolationTests(unittest.TestCase):
    def test_parser_schema_and_approval_contract(self) -> None:
        action = parse_tool_action(
            "Agent",
            {"prompt": "Implement feature", "mode": "code", "isolation": "worktree"},
        )
        schema = next(tool for tool in AGENT_TOOL_DEFINITIONS if tool["name"] == "Agent")["input_schema"]
        approval = build_approval_request(action)

        self.assertEqual(action.isolation, "worktree")
        self.assertEqual(schema["properties"]["isolation"]["enum"], ["worktree"])
        self.assertEqual(approval.action_type if approval is not None else None, "delegate_task_worktree")
        with self.assertRaises(ActionParseError):
            parse_tool_action("Agent", {"prompt": "x", "isolation": "container"})

    def test_clean_isolated_subagent_removes_temporary_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            root = Path(base)
            _repository(root)
            workspace = create_run_workspace(root, run_id="clean-isolation")
            action = parse_tool_action(
                "Agent",
                {"prompt": "Inspect README", "isolation": "worktree"},
            )
            result = _execute(
                workspace,
                action,
                IsolationClient([[{"type": "text", "text": "README inspected."}]]),
            )
            transcript = read_subagent_transcript(workspace, "delegate-1-1")
            registered = _git(root, "worktree", "list", "--porcelain")
            worktree_exists = Path(result.worktree_path or "").exists()

        self.assertTrue(result.ok)
        self.assertEqual(result.isolation, "worktree")
        self.assertFalse(result.worktree_preserved)
        self.assertIsNotNone(transcript.worktree)
        self.assertFalse(worktree_exists)
        self.assertNotIn(result.worktree_branch or "missing", registered)

    def test_project_agent_profile_can_require_worktree_isolation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            root = Path(base)
            _repository(root)
            profile = root / ".claude" / "agents" / "isolated-writer.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "---\nname: isolated-writer\ndescription: Writes away from the parent\n"
                "mode: code\ntools: Write\nisolation: worktree\n---\n\nWrite the requested file.\n",
                encoding="utf-8",
            )
            _git(root, "add", ".claude/agents/isolated-writer.md")
            _git(root, "commit", "-qm", "add isolated agent")
            workspace = create_run_workspace(root, run_id="profile-isolation")
            action = parse_tool_action(
                "Agent",
                {"prompt": "Create profile-isolated.py", "subagent_type": "isolated-writer"},
            )
            result = _execute(
                workspace,
                action,
                IsolationClient(
                    [
                        [
                            {
                                "type": "tool_call",
                                "id": "write-profile",
                                "name": "Write",
                                "input": {
                                    "file_path": "profile-isolated.py",
                                    "content": "from_profile = True\n",
                                },
                            }
                        ],
                        [{"type": "text", "text": "Profile-isolated edit complete."}],
                    ]
                ),
            )
            isolated_content = Path(result.worktree_path or "").joinpath(
                "profile-isolated.py"
            ).read_text(encoding="utf-8")
            parent_has_file = root.joinpath("profile-isolated.py").exists()

        self.assertTrue(result.ok)
        self.assertEqual(result.isolation, "worktree")
        self.assertTrue(result.worktree_preserved)
        self.assertEqual(isolated_content, "from_profile = True\n")
        self.assertFalse(parent_has_file)

    def test_dynamic_agent_profile_can_require_worktree_isolation(self) -> None:
        profiles = parse_dynamic_agent_profiles(
            json.dumps(
                {
                    "isolated-writer": {
                        "description": "Writes away from the parent",
                        "prompt": "DYNAMIC_ISOLATED_WRITER_INSTRUCTION",
                        "mode": "code",
                        "tools": ["Write"],
                        "isolation": "worktree",
                    }
                }
            )
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            root = Path(base)
            _repository(root)
            workspace = replace(
                create_run_workspace(root, run_id="dynamic-profile-isolation"),
                dynamic_agent_profiles=profiles,
            )
            client = IsolationClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "write-profile",
                            "name": "Write",
                            "input": {
                                "file_path": "dynamic-isolated.py",
                                "content": "from_dynamic_profile = True\n",
                            },
                        }
                    ],
                    [{"type": "text", "text": "Dynamic isolated edit complete."}],
                ]
            )
            result = _execute(
                workspace,
                parse_tool_action(
                    "Agent",
                    {"prompt": "Create dynamic-isolated.py", "subagent_type": "isolated-writer"},
                ),
                client,
            )
            isolated_content = Path(result.worktree_path or "").joinpath(
                "dynamic-isolated.py"
            ).read_text(encoding="utf-8")
            parent_has_file = root.joinpath("dynamic-isolated.py").exists()

        self.assertTrue(result.ok)
        self.assertEqual(result.isolation, "worktree")
        self.assertTrue(result.worktree_preserved)
        self.assertEqual(isolated_content, "from_dynamic_profile = True\n")
        self.assertFalse(parent_has_file)
        self.assertIn("DYNAMIC_ISOLATED_WRITER_INSTRUCTION", str(client.messages[0][0].content))

    def test_worktree_isolation_fails_closed_outside_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            workspace = create_run_workspace(Path(base), run_id="not-git")
            action = parse_tool_action("Agent", {"prompt": "Inspect", "isolation": "worktree"})
            client = IsolationClient([[{"type": "text", "text": "must not run"}]])
            result = _execute(workspace, action, client)

        self.assertFalse(result.ok)
        self.assertIn("requires a git repository", result.message)
        self.assertEqual(client.messages, [])

    def test_setup_failure_unlocks_and_removes_clean_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            root = Path(base)
            _repository(root)
            workspace = create_run_workspace(root, run_id="setup-failure")
            action = parse_tool_action("Agent", {"prompt": "Inspect", "isolation": "worktree"})
            client = IsolationClient([[{"type": "text", "text": "must not run"}]])
            with patch(
                "vibeagent.agent_delegate.create_subagent_transcript",
                side_effect=ValueError("transcript unavailable"),
            ):
                result = _execute(workspace, action, client)
            registered = _git(root, "worktree", "list", "--porcelain")

        self.assertFalse(result.ok)
        self.assertIn("Subagent setup failed", result.message)
        self.assertFalse(result.worktree_preserved)
        self.assertNotIn("vibeagent/subagent-", registered)
        self.assertEqual(client.messages, [])

    def test_resume_rejects_tampered_managed_worktree_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            root = Path(base)
            _repository(root)
            workspace = create_run_workspace(root, run_id="tampered-worktree")
            action = parse_tool_action(
                "Agent",
                {"prompt": "Create isolated.py", "mode": "code", "isolation": "worktree"},
            )
            _execute(
                workspace,
                action,
                IsolationClient(
                    [
                        [
                            {
                                "type": "tool_call",
                                "id": "write-tampered",
                                "name": "Write",
                                "input": {"file_path": "isolated.py", "content": "value = 1\n"},
                            }
                        ],
                        [{"type": "text", "text": "Created file."}],
                    ]
                ),
            )
            record = read_subagent_transcript(workspace, "delegate-1-1").worktree
            self.assertIsNotNone(record)
            tampered = SubagentWorktreeRecord(
                project_path=record.project_path,
                worktree_path=record.worktree_path,
                branch="main",
                base_commit=record.base_commit,
            )

            with self.assertRaises(SubagentWorktreeError):
                prepare_subagent_worktree(workspace, "delegate-1-1", tampered)

    def test_isolated_changes_are_preserved_outside_parent_checkout_and_resumable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            root = Path(base)
            _repository(root)
            workspace = create_run_workspace(root, run_id="preserved-isolation")
            action = parse_tool_action(
                "Agent",
                {"prompt": "Create isolated.py", "mode": "code", "isolation": "worktree"},
            )
            first = _execute(
                workspace,
                action,
                IsolationClient(
                    [
                        [
                            {
                                "type": "tool_call",
                                "id": "write-1",
                                "name": "Write",
                                "input": {"file_path": "isolated.py", "content": "isolated = True\n"},
                            }
                        ],
                        [{"type": "text", "text": "Created isolated.py."}],
                    ]
                ),
            )
            transcript = read_subagent_transcript(workspace, "delegate-1-1")
            isolated_root = Path(first.worktree_path or "")
            listed = execute_action(workspace, parse_tool_action("ListAgents", {}))
            second_client = IsolationClient([[{"type": "text", "text": "Confirmed the isolated change."}]])
            second = _execute(
                workspace,
                transcript.action,
                second_client,
                resume=transcript,
                followup="Confirm the file",
            )
            parent_has_file = root.joinpath("isolated.py").exists()
            isolated_content = isolated_root.joinpath("isolated.py").read_text(encoding="utf-8")
            resumed_messages = str(second_client.messages[0])

        self.assertTrue(first.ok)
        self.assertTrue(first.worktree_preserved)
        self.assertFalse(parent_has_file)
        self.assertEqual(isolated_content, "isolated = True\n")
        self.assertEqual(listed.agents[0].worktree_path, str(isolated_root))
        self.assertEqual(second.worktree_path, str(isolated_root))
        self.assertTrue(second.worktree_preserved)
        self.assertIn("Created isolated.py.", resumed_messages)
        self.assertIn("Confirm the file", resumed_messages)

    def test_background_isolated_subagent_returns_preserved_worktree_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-isolated-agent-") as base:
            root = Path(base)
            _repository(root)
            workspace = create_run_workspace(root, run_id="background-isolation")
            action = parse_tool_action(
                "Agent",
                {
                    "prompt": "Create background-isolated.py",
                    "mode": "code",
                    "isolation": "worktree",
                    "run_in_background": True,
                },
            )
            client = IsolationClient(
                [
                    [
                        {
                            "type": "tool_call",
                            "id": "write-background",
                            "name": "Write",
                            "input": {
                                "file_path": "background-isolated.py",
                                "content": "background = True\n",
                            },
                        }
                    ],
                    [{"type": "text", "text": "Background isolated edit complete."}],
                ]
            )
            started = start_background_delegate_task(
                workspace,
                action,
                lambda task_id, cancel, inbox: execute_delegate_task_action(
                    workspace,
                    action,
                    client,
                    parent_iteration=1,
                    subagent_id=task_id,
                    max_output_tokens=2048,
                    model_retries=0,
                    model_retry_delay_ms=0,
                    model_timeout_ms=10_000,
                    command_timeout_ms=10_000,
                    logger=None,
                    approval_handler=lambda _request: ApprovalDecision(approved=True, message="approved"),
                    cancel_requested=cancel,
                    inbound_messages=inbox,
                ),
            )
            output = execute_action(
                workspace,
                parse_tool_action(
                    "TaskOutput",
                    {"task_id": started.task_id, "block": True, "timeout_ms": 10_000},
                ),
            )
            result = output.result
            isolated_content = Path(result.worktree_path or "").joinpath(
                "background-isolated.py"
            ).read_text(encoding="utf-8") if result is not None else ""
            parent_has_file = root.joinpath("background-isolated.py").exists()

        self.assertTrue(output.ok)
        self.assertIsNotNone(result)
        self.assertEqual(result.isolation if result is not None else None, "worktree")
        self.assertTrue(result.worktree_preserved if result is not None else False)
        self.assertEqual(isolated_content, "background = True\n")
        self.assertFalse(parent_has_file)


if __name__ == "__main__":
    unittest.main()
