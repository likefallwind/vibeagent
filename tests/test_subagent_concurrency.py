from __future__ import annotations

from pathlib import Path
from threading import Event
import os
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.background_delegate_runtime import (
    close_background_delegate_tasks,
    start_background_delegate_task,
)
from vibeagent.subagent_concurrency import resolve_max_concurrent_subagents
from vibeagent.types import DelegateTaskAction, DelegateTaskObservation
from vibeagent.workspace import create_run_workspace


def _action(task: str) -> DelegateTaskAction:
    return DelegateTaskAction(
        type="delegate_task",
        task=task,
        run_in_background=True,
    )


def _result(task_id: str, action: DelegateTaskAction) -> DelegateTaskObservation:
    return DelegateTaskObservation(
        kind="delegate_task",
        ok=True,
        task=action.task,
        summary="done",
        iterations=1,
        tool_calls=[],
        message="done",
        mode=action.mode,
        task_id=task_id,
        background=True,
    )


class SubagentConcurrencyTests(unittest.TestCase):
    def test_resolves_default_and_compatible_environment_override(self) -> None:
        self.assertEqual(resolve_max_concurrent_subagents({}), 20)
        self.assertEqual(
            resolve_max_concurrent_subagents(
                {"CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "7"}
            ),
            7,
        )
        self.assertEqual(
            resolve_max_concurrent_subagents(
                {
                    "VIBEAGENT_MAX_CONCURRENT_SUBAGENTS": "5",
                    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "7",
                }
            ),
            5,
        )

    def test_rejects_invalid_environment_override(self) -> None:
        for value in ("many", "0", "101"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "must (be an integer|be between)"):
                    resolve_max_concurrent_subagents(
                        {"VIBEAGENT_MAX_CONCURRENT_SUBAGENTS": value}
                    )

    def test_running_task_holds_slot_until_completion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-subagent-limit-") as base:
            workspace = create_run_workspace(Path(base))
            release = Event()
            first_action = _action("first")

            def wait_for_release(task_id, _cancel, _inbox):
                release.wait(2)
                return _result(task_id, first_action)

            with patch.dict(
                os.environ,
                {
                    "VIBEAGENT_MAX_CONCURRENT_SUBAGENTS": "1",
                    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "",
                },
            ):
                first = start_background_delegate_task(
                    workspace,
                    first_action,
                    wait_for_release,
                )
                try:
                    with self.assertRaisesRegex(
                        ValueError,
                        "Concurrent subagent limit reached \\(1/1\\)",
                    ):
                        start_background_delegate_task(
                            workspace,
                            _action("blocked"),
                            lambda task_id, _cancel, _inbox: _result(
                                task_id, _action("blocked")
                            ),
                        )

                    release.set()
                    close_result = close_background_delegate_tasks(
                        workspace,
                        wait_ms=2_000,
                    )
                    self.assertIn(first.task_id, close_result.discarded_task_ids)

                    after_action = _action("after")
                    after = start_background_delegate_task(
                        workspace,
                        after_action,
                        lambda task_id, _cancel, _inbox: _result(
                            task_id, after_action
                        ),
                    )
                    self.assertTrue(after.running)
                finally:
                    release.set()
                    close_background_delegate_tasks(workspace, wait_ms=2_000)


if __name__ == "__main__":
    unittest.main()
