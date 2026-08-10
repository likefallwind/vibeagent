from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_completion import build_completion_blocker_details, build_completion_blockers
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.agent_special_tools import execute_special_tool_action
from vibeagent.background_delegate_runtime import close_background_delegate_tasks
from vibeagent.types import (
    AssistantResponse,
    ApprovalDecision,
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
        self.messages = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        self.started.set()
        if not self.release.wait(5):
            raise RuntimeError("test client was not released")
        content = [{"type": "text", "text": self.text}]
        return AssistantResponse(content=content, raw={"content": content})


class SequenceDelegateClient:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.messages = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class SteerableDelegateClient:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.messages = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        if len(self.messages) == 1:
            self.started.set()
            if not self.release.wait(5):
                raise RuntimeError("test client was not released")
            text = "Initial answer before steering."
        else:
            text = "Corrected answer after steering."
        content = [{"type": "text", "text": text}]
        return AssistantResponse(content=content, raw={"content": content})


class BackgroundDelegateTests(unittest.TestCase):
    def test_task_alias_parses_background_and_lifecycle_actions(self) -> None:
        task = parse_tool_action("Task", {"prompt": "Inspect auth", "run_in_background": True})
        output = parse_tool_action("TaskOutput", {"task_id": "task-123456789abc", "block": False})
        stop = parse_tool_action("TaskStop", {"task_id": "task-123456789abc"})

        self.assertTrue(task.run_in_background)
        self.assertEqual(output, TaskOutputAction(type="task_output", task_id="task-123456789abc", block=False))
        self.assertEqual(stop, TaskStopAction(type="task_stop", task_id="task-123456789abc"))

    def test_background_code_delegation_is_supported(self) -> None:
        action = parse_tool_action("Task", {"prompt": "Edit auth", "mode": "code", "run_in_background": True})

        self.assertEqual(action.mode, "code")
        self.assertTrue(action.run_in_background)

    def test_background_project_agent_can_apply_code_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-profile-") as base:
            root = Path(base)
            profile = root / ".claude/agents/writer.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "---\nname: writer\ndescription: Writes code\nmode: code\ntools: [Read, Write]\n---\n\nEdit files.\n",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root)
            client = SequenceDelegateClient([[{"type": "text", "text": "Profile code task completed."}]])
            wrapped = execute_special_tool_action(
                workspace,
                DelegateTaskAction(
                    type="delegate_task",
                    task="Inspect only",
                    agent="writer",
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
        self.assertTrue(completed.result.ok)
        self.assertEqual(completed.result.mode, "code")
        self.assertEqual(completed.result.summary, "Profile code task completed.")

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

    def test_running_background_subagent_receives_parent_steering(self) -> None:
        client = SteerableDelegateClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-steer-") as base:
            workspace = create_run_workspace(Path(base))
            started = self._start_background_task(workspace, client)
            self.assertTrue(client.started.wait(1))

            sent = self._execute_special(
                workspace,
                parse_tool_action(
                    "SendMessage",
                    {"to": started.task_id, "message": "Recheck the middleware path"},
                ),
                client,
                iteration=2,
                tool_name="SendMessage",
            ).observation
            client.release.set()
            completed = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )

        self.assertTrue(sent.running)
        self.assertIn("delivered", sent.message)
        self.assertIsNotNone(completed.result)
        self.assertEqual(completed.result.summary, "Corrected answer after steering.")
        self.assertIn("Recheck the middleware path", str(client.messages[1]))

    def test_completed_subagent_send_message_resumes_same_id_in_background(self) -> None:
        first_client = SequenceDelegateClient([[{"type": "text", "text": "Initial auth finding."}]])
        resumed_client = BlockingDelegateClient("Follow-up auth finding.")
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-resume-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("delegate_task", {"task": "Inspect auth", "max_iterations": 2})
            first = execute_delegate_task_action(
                workspace,
                action,
                first_client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )

            resumed = self._execute_special(
                workspace,
                parse_tool_action(
                    "SendMessage",
                    {"to": first.task_id, "message": "Now inspect authorization"},
                ),
                resumed_client,
                iteration=2,
                tool_name="SendMessage",
            ).observation
            self.assertTrue(resumed_client.started.wait(1))
            resumed_client.release.set()
            completed = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=first.task_id or "", block=True, timeout_ms=2_000),
            )

        self.assertEqual(resumed.task_id, "delegate-1-1")
        self.assertTrue(resumed.background)
        self.assertTrue(resumed.running)
        self.assertIsNotNone(completed.result)
        self.assertEqual(completed.result.task_id, "delegate-1-1")
        self.assertEqual(completed.result.summary, "Follow-up auth finding.")
        self.assertIn("Initial auth finding.", str(resumed_client.messages[0]))
        self.assertIn("Now inspect authorization", str(resumed_client.messages[0]))

    def test_background_code_uses_parent_approval_handler(self) -> None:
        client = SequenceDelegateClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "result.py", "content": "value = 1\n"}}],
                [{"type": "text", "text": "Wrote result.py."}],
            ]
        )
        approvals = []

        def approve(request):
            approvals.append(request.action_type)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-background-code-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            started = self._execute_special(
                workspace,
                parse_tool_action(
                    "Task",
                    {"prompt": "Write result.py", "mode": "code", "run_in_background": True},
                ),
                client,
                approval_handler=approve,
            ).observation
            completed = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )
            written = root.joinpath("result.py").read_text(encoding="utf-8")

        self.assertEqual(approvals, ["write_file"])
        self.assertEqual(written, "value = 1\n")
        self.assertIsNotNone(completed.result)
        self.assertTrue(completed.result.ok)

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

    def test_task_stop_cancelled_subagent_can_resume_with_send_message(self) -> None:
        first_client = BlockingDelegateClient()
        resumed_client = BlockingDelegateClient("Resumed after TaskStop.")
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-stop-resume-") as base:
            workspace = create_run_workspace(Path(base))
            started = self._start_background_task(workspace, first_client)
            self.assertTrue(first_client.started.wait(1))
            execute_action(
                workspace,
                TaskStopAction(type="task_stop", task_id=started.task_id or ""),
            )
            first_client.release.set()
            cancelled = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )

            resumed = self._execute_special(
                workspace,
                parse_tool_action(
                    "SendMessage",
                    {"to": started.task_id, "message": "Continue with the narrower check"},
                ),
                resumed_client,
                iteration=2,
                tool_name="SendMessage",
            ).observation
            self.assertTrue(resumed_client.started.wait(1))
            resumed_client.release.set()
            completed = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )

        self.assertIsNotNone(cancelled.result)
        self.assertTrue(cancelled.result.cancelled)
        self.assertTrue(resumed.running)
        self.assertIsNotNone(completed.result)
        self.assertEqual(completed.result.summary, "Resumed after TaskStop.")
        self.assertIn("Continue with the narrower check", str(resumed_client.messages[0]))

    def test_close_discards_completed_session_tasks(self) -> None:
        client = BlockingDelegateClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-close-complete-") as base:
            workspace = create_run_workspace(Path(base))
            started = self._start_background_task(workspace, client)
            self.assertTrue(client.started.wait(1))
            client.release.set()
            completed = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=True, timeout_ms=2_000),
            )

            closed = close_background_delegate_tasks(workspace)
            missing = execute_action(
                workspace,
                TaskOutputAction(type="task_output", task_id=started.task_id or "", block=False),
            )

        self.assertTrue(completed.completed)
        self.assertEqual(closed.task_ids, (started.task_id,))
        self.assertEqual(closed.cancel_requested_task_ids, ())
        self.assertEqual(closed.discarded_task_ids, (started.task_id,))
        self.assertFalse(missing.ok)

    def test_close_cancels_running_task_and_discards_it_when_worker_returns(self) -> None:
        client = BlockingDelegateClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-close-running-") as base:
            workspace = create_run_workspace(Path(base))
            started = self._start_background_task(workspace, client)
            self.assertTrue(client.started.wait(1))

            closed = close_background_delegate_tasks(workspace, wait_ms=0)
            self.assertEqual(closed.cancel_requested_task_ids, (started.task_id,))
            self.assertEqual(closed.still_running_task_ids, (started.task_id,))
            client.release.set()

            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                missing = execute_action(
                    workspace,
                    TaskOutputAction(type="task_output", task_id=started.task_id or "", block=False),
                )
                if not missing.ok:
                    break
                time.sleep(0.01)

        self.assertFalse(missing.ok)

    def test_close_only_discards_tasks_from_the_selected_session(self) -> None:
        first_client = BlockingDelegateClient()
        second_client = BlockingDelegateClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-close-scope-") as base:
            root = Path(base)
            first_workspace = create_run_workspace(root, run_id="first")
            second_workspace = create_run_workspace(root, run_id="second")
            first = self._start_background_task(first_workspace, first_client)
            second = self._start_background_task(second_workspace, second_client)
            self.assertTrue(first_client.started.wait(1))
            self.assertTrue(second_client.started.wait(1))

            close_background_delegate_tasks(first_workspace, wait_ms=0)
            second_running = execute_action(
                second_workspace,
                TaskOutputAction(type="task_output", task_id=second.task_id or "", block=False),
            )
            first_client.release.set()
            second_client.release.set()
            close_background_delegate_tasks(second_workspace)

        self.assertTrue(second_running.ok)
        self.assertTrue(second_running.running)
        self.assertNotEqual(first.task_id, second.task_id)

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
        wrapped = self._execute_special(
            workspace,
            DelegateTaskAction(
                type="delegate_task",
                task="Inspect auth",
                max_iterations=2,
                run_in_background=True,
            ),
            client,
        )
        self.assertTrue(wrapped.observation.background)
        self.assertTrue(wrapped.observation.running)
        self.assertRegex(wrapped.observation.task_id or "", r"^task-[a-f0-9]{12}$")
        return wrapped.observation

    def _execute_special(
        self,
        workspace,
        action,
        client,
        *,
        iteration=1,
        tool_name="Task",
        approval_handler=None,
    ):
        return execute_special_tool_action(
            workspace,
            action,
            client,
            steps=[],
            observations=[],
            iteration=iteration,
            tool_name=tool_name,
            max_output_tokens=2048,
            model_retries=0,
            model_retry_delay_ms=0,
            model_timeout_ms=10_000,
            command_timeout_ms=10_000,
            logger=None,
            approval_handler=approval_handler,
            approval_policy="ask",
            user_input_handler=None,
            hooks=ProjectHooks(),
            permissions=ProjectPermissions(),
            execute_action_safely_func=_unexpected_execute_action_safely,
        )


def _unexpected_execute_action_safely(
    _workspace: object,
    _action: object,
    _command_timeout_ms: int,
    _tool_name: str,
) -> Observation:
    raise AssertionError("background explore tests should not execute generic actions")


if __name__ == "__main__":
    unittest.main()
