import tempfile
import threading
import unittest
from pathlib import Path

from vibeagent.action_parsing import parse_tool_action
from vibeagent.background_delegate_runtime import execute_background_task_action
from vibeagent.nested_delegate_runtime import MAX_SUBAGENT_DEPTH, NestedDelegateRuntime
from vibeagent.types import DelegateTaskObservation, TaskOutputAction
from vibeagent.workspace import create_run_workspace


class NestedDelegateRuntimeTests(unittest.TestCase):
    def test_parent_cancellation_propagates_to_background_child(self) -> None:
        parent_cancelled = threading.Event()
        child_started = threading.Event()

        def execute_child(
            action, task_id, depth, parent_id, _iteration, parent_tool_use_id, cancelled, _inbound
        ):
            self.assertEqual(parent_tool_use_id, "nested-tool-1")
            child_started.set()
            self.assertIsNotNone(cancelled)
            self.assertTrue(parent_cancelled.wait(1))
            self.assertTrue(cancelled())
            return DelegateTaskObservation(
                kind="delegate_task",
                ok=False,
                task=action.task,
                summary="",
                iterations=0,
                tool_calls=[],
                message="cancelled",
                task_id=task_id,
                background=True,
                cancelled=True,
                depth=depth,
                parent_id=parent_id,
            )

        with tempfile.TemporaryDirectory(prefix="vibeagent-nested-runtime-") as base:
            workspace = create_run_workspace(Path(base))
            runtime = NestedDelegateRuntime(
                workspace=workspace,
                subagent_id="agent-parent",
                depth=1,
                mode="code",
                cancel_requested=parent_cancelled.is_set,
                execute_child=execute_child,
            )
            action = parse_tool_action(
                "delegate_task",
                {"task": "Background child", "run_in_background": True},
            )
            started = runtime.execute(
                action,
                child_iteration=1,
                parent_tool_use_id="nested-tool-1",
            )
            self.assertTrue(child_started.wait(1))
            parent_cancelled.set()
            completed = execute_background_task_action(
                workspace,
                TaskOutputAction(
                    type="task_output",
                    task_id=started.task_id or "",
                    block=True,
                    timeout_ms=1_000,
                ),
            )

        self.assertEqual(MAX_SUBAGENT_DEPTH, 3)
        self.assertIsNotNone(completed)
        self.assertTrue(completed.completed)
        self.assertTrue(completed.result.cancelled)
        self.assertEqual(completed.result.depth, 2)
        self.assertEqual(completed.result.parent_id, "agent-parent")

    def test_explore_parent_cannot_delegate_code_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-nested-runtime-") as base:
            workspace = create_run_workspace(Path(base))
            runtime = NestedDelegateRuntime(
                workspace=workspace,
                subagent_id="agent-parent",
                depth=1,
                mode="explore",
                cancel_requested=None,
                execute_child=lambda *_args: self.fail("code child should not execute"),
            )
            denied = runtime.execute(
                parse_tool_action("delegate_task", {"task": "Write", "mode": "code"}),
                child_iteration=1,
            )

        self.assertEqual(denied.kind, "tool_error")
        self.assertIn("only delegate explore-mode", denied.message)


if __name__ == "__main__":
    unittest.main()
