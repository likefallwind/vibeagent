from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_completion import build_completion_blocker_details, build_completion_blockers
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.agent_special_tools import execute_special_tool_action
from vibeagent.types import (
    AssistantResponse,
    DelegateTaskAction,
    Observation,
    TaskOutputAction,
    TaskStopAction,
)
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


class BlockingDelegateClient:
    def __init__(self, text: str = "Found the answer in app.py:1") -> None:
        self.text = text
        self.started = threading.Event()
        self.release = threading.Event()

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.started.set()
        if not self.release.wait(5):
            raise RuntimeError("test client was not released")
        content = [{"type": "text", "text": self.text}]
        return AssistantResponse(content=content, raw={"content": content})


class UnexpectedDelegateClient:
    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        raise AssertionError("background code profile must be rejected before a model call")


class BackgroundDelegateTests(unittest.TestCase):
    def test_task_alias_parses_background_and_lifecycle_actions(self) -> None:
        task = parse_tool_action("Task", {"prompt": "Inspect auth", "run_in_background": True})
        output = parse_tool_action("TaskOutput", {"task_id": "task-123456789abc", "block": False})
        stop = parse_tool_action("TaskStop", {"task_id": "task-123456789abc"})

        self.assertTrue(task.run_in_background)
        self.assertEqual(output, TaskOutputAction(type="task_output", task_id="task-123456789abc", block=False))
        self.assertEqual(stop, TaskStopAction(type="task_stop", task_id="task-123456789abc"))

    def test_background_code_delegation_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "only supports explore mode"):
            parse_tool_action("Task", {"prompt": "Edit auth", "mode": "code", "run_in_background": True})

    def test_background_project_agent_cannot_override_explore_with_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-profile-") as base:
            root = Path(base)
            profile = root / ".claude/agents/writer.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "---\nname: writer\ndescription: Writes code\nmode: code\ntools: [Read, Write]\n---\n\nEdit files.\n",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root)
            wrapped = execute_special_tool_action(
                workspace,
                DelegateTaskAction(
                    type="delegate_task",
                    task="Inspect only",
                    agent="writer",
                    run_in_background=True,
                ),
                UnexpectedDelegateClient(),
                steps=[],
                observations=[],
                iteration=1,
                tool_name="Task",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                user_input_handler=None,
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                execute_action_safely_func=_unexpected_execute_action_safely,
            )
            completed = execute_action(
                workspace,
                TaskOutputAction(
                    type="task_output",
                    task_id=wrapped.observation.task_id or "",
                    block=True,
                    timeout_ms=2_000,
                ),
            )

        self.assertTrue(completed.completed)
        self.assertIsNotNone(completed.result)
        self.assertFalse(completed.result.ok)
        self.assertIn("only supports explore mode", completed.result.message)

    def test_background_task_can_be_polled_and_collected(self) -> None:
        client = BlockingDelegateClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-") as base:
            workspace = create_run_workspace(Path(base))
            started = self._start_background_task(workspace, client)
            self.assertTrue(client.started.wait(1))

            running = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=False),
            )
            self.assertTrue(running.running)
            self.assertFalse(running.completed)

            client.release.set()
            completed = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )

        self.assertTrue(completed.ok)
        self.assertTrue(completed.completed)
        self.assertFalse(completed.running)
        self.assertIsNotNone(completed.result)
        self.assertEqual(completed.result.summary, "Found the answer in app.py:1")

    def test_background_task_stop_is_cooperative_and_collectable(self) -> None:
        client = BlockingDelegateClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-stop-") as base:
            workspace = create_run_workspace(Path(base))
            started = self._start_background_task(workspace, client)
            self.assertTrue(client.started.wait(1))

            stopping = execute_action(
                workspace,
                TaskStopAction(type="task_stop", task_id=started.task_id or ""),
            )
            self.assertTrue(stopping.ok)
            self.assertTrue(stopping.running)

            client.release.set()
            completed = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )

        self.assertTrue(completed.completed)
        self.assertIsNotNone(completed.result)
        self.assertTrue(completed.result.cancelled)
        self.assertFalse(completed.result.ok)

    def test_completion_is_blocked_until_background_result_is_collected(self) -> None:
        client = BlockingDelegateClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-blocker-") as base:
            workspace = create_run_workspace(Path(base))
            started = self._start_background_task(workspace, client)
            blockers = build_completion_blockers(True, [started], [])
            details = build_completion_blocker_details(True, [started], blockers=blockers)
            client.release.set()
            collected = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )

        self.assertIn("1 background subagent task(s) are still running or unread.", blockers)
        self.assertIn("activeBackgroundTasks", details)
        self.assertNotIn(
            "1 background subagent task(s) are still running or unread.",
            build_completion_blockers(True, [started, collected], []),
        )

    def test_session_event_appends_remain_valid_under_threads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-events-") as base:
            session_dir = Path(base)
            threads = [
                threading.Thread(
                    target=lambda worker=worker: [
                        append_session_event(session_dir, "test", {"worker": worker, "index": index})
                        for index in range(50)
                    ]
                )
                for worker in range(8)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            events = [json.loads(line) for line in (session_dir / "events.jsonl").read_text().splitlines()]

        self.assertEqual(len(events), 400)
        self.assertEqual({event["worker"] for event in events}, set(range(8)))

    def _start_background_task(self, workspace, client: BlockingDelegateClient):
        wrapped = execute_special_tool_action(
            workspace,
            DelegateTaskAction(
                type="delegate_task",
                task="Inspect auth",
                max_iterations=2,
                run_in_background=True,
            ),
            client,
            steps=[],
            observations=[],
            iteration=1,
            tool_name="Task",
            max_output_tokens=2048,
            model_retries=0,
            model_retry_delay_ms=0,
            model_timeout_ms=10_000,
            command_timeout_ms=10_000,
            logger=None,
            approval_handler=None,
            approval_policy="ask",
            user_input_handler=None,
            hooks=ProjectHooks(),
            permissions=ProjectPermissions(),
            execute_action_safely_func=_unexpected_execute_action_safely,
        )
        self.assertTrue(wrapped.observation.background)
        self.assertTrue(wrapped.observation.running)
        self.assertRegex(wrapped.observation.task_id or "", r"^task-[a-f0-9]{12}$")
        return wrapped.observation


def _unexpected_execute_action_safely(
    _workspace: object,
    _action: object,
    _command_timeout_ms: int,
    _tool_name: str,
) -> Observation:
    raise AssertionError("background explore tests should not execute generic actions")


if __name__ == "__main__":
    unittest.main()
