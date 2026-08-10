from dataclasses import replace
import json
import tempfile
import time
import unittest
from pathlib import Path

from vibeagent.agent_background_notifications import inject_background_delegate_notifications
from vibeagent.agent_completion import build_completion_blockers
from vibeagent.background_delegate_runtime import start_background_delegate_task
from vibeagent.types import ChatMessage, DelegateTaskAction, DelegateTaskObservation, TaskOutputAction
from vibeagent.actions import execute_action
from vibeagent.workspace import create_run_workspace


def _result(task_id: str, action: DelegateTaskAction) -> DelegateTaskObservation:
    return DelegateTaskObservation(
        kind="delegate_task",
        ok=True,
        task=action.task,
        summary="Notification result from app.py:1.",
        iterations=1,
        tool_calls=[],
        message="Subagent completed the investigation.",
        mode=action.mode,
        task_id=task_id,
        background=True,
    )


class BackgroundDelegateNotificationTests(unittest.TestCase):
    def test_completion_notification_is_injected_once_and_clears_blocker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-notification-") as base:
            workspace = create_run_workspace(Path(base))
            action = DelegateTaskAction(type="delegate_task", task="Inspect auth", run_in_background=True)
            started = start_background_delegate_task(
                workspace,
                action,
                lambda task_id, _cancel, _inbox: _result(task_id, action),
            )
            messages = [ChatMessage(role="system", content="system")]
            observations = [started]

            delivered = 0
            for _ in range(100):
                delivered = inject_background_delegate_notifications(
                    workspace,
                    messages,
                    observations,
                    iteration=2,
                    logger=None,
                )
                if delivered:
                    break
                time.sleep(0.01)
            repeated = inject_background_delegate_notifications(
                workspace,
                messages,
                observations,
                iteration=3,
                logger=None,
            )
            event = json.loads(
                (workspace.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1]
            )

        self.assertEqual(delivered, 1)
        self.assertEqual(repeated, 0)
        self.assertEqual(observations[-1].kind, "task_output")
        self.assertIn("Notification result from app.py:1.", str(messages[-1].content))
        self.assertEqual(event["type"], "background_delegate_notification")
        self.assertNotIn("background subagent task", " ".join(build_completion_blockers(True, observations, [])))

    def test_explicit_task_output_suppresses_duplicate_notification(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-notification-") as base:
            workspace = create_run_workspace(Path(base))
            action = DelegateTaskAction(type="delegate_task", task="Inspect auth", run_in_background=True)
            started = start_background_delegate_task(
                workspace,
                action,
                lambda task_id, _cancel, _inbox: _result(task_id, action),
            )
            output = execute_action(
                workspace,
                TaskOutputAction(
                    type="task_output",
                    task_id=started.task_id or "",
                    block=True,
                    timeout_ms=2_000,
                ),
            )
            messages = [ChatMessage(role="system", content="system")]
            observations = [started, output]

            delivered = inject_background_delegate_notifications(
                workspace,
                messages,
                observations,
                iteration=2,
                logger=None,
            )

        self.assertTrue(output.completed)
        self.assertEqual(delivered, 0)
        self.assertEqual(len(messages), 1)

    def test_notification_redacts_secrets_before_parent_injection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-notification-") as base:
            workspace = create_run_workspace(Path(base))
            action = DelegateTaskAction(type="delegate_task", task="Inspect auth", run_in_background=True)

            def secret_result(task_id, _cancel, _inbox):
                result = _result(task_id, action)
                return replace(result, summary="API_KEY=super-secret-value")

            start_background_delegate_task(workspace, action, secret_result)
            messages = [ChatMessage(role="system", content="system")]
            observations = []
            for _ in range(100):
                if inject_background_delegate_notifications(
                    workspace,
                    messages,
                    observations,
                    iteration=2,
                    logger=None,
                ):
                    break
                time.sleep(0.01)

        rendered = str(messages[-1].content)
        self.assertIn("[REDACTED]", rendered)
        self.assertNotIn("super-secret-value", rendered)


if __name__ == "__main__":
    unittest.main()
