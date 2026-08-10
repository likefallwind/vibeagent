from __future__ import annotations

from dataclasses import replace
from io import StringIO
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from vibeagent.actions import parse_tool_action
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.scheduled_task_store import create_scheduled_task, write_schedule_store
from vibeagent.scheduled_task_types import ScheduledTaskStore
from vibeagent.workspace import create_run_workspace


class CliScheduledTaskTests(unittest.TestCase):
    def test_idle_interactive_session_runs_due_prompt_as_resumed_agent_turn(self) -> None:
        now = time.time()
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-cron-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "source-run")
            scheduled, _ = create_scheduled_task(
                workspace,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "* * * * *", "prompt": "Check deployment", "recurring": False},
                ),
                now=now,
            )
            write_schedule_store(
                workspace,
                ScheduledTaskStore((replace(scheduled, next_run_at=now - 1),)),
            )
            result = SimpleNamespace(run_id="scheduled-run")
            run_agent = Mock(return_value=result)

            def trigger_idle(prompt, callback, *, input_func, interval_seconds=1.0):
                callback()
                return "/exit"

            with (
                patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=trigger_idle),
                patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                patch("vibeagent.cli_interactive.print_agent_result"),
                patch("sys.stdout", new_callable=StringIO) as stdout,
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=Mock(return_value=object()),
                    run_agent_func=run_agent,
                    get_resume_context_func=Mock(
                        return_value=("scheduled-run", "next context", "loaded")
                    ),
                    initial_resume_run_id="source-run",
                    initial_resume_context="source context",
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "Check deployment")
        self.assertEqual(run_agent.call_args.kwargs["task_source_run_id"], "source-run")
        self.assertEqual(run_agent.call_args.kwargs["prior_context"], "source context")
        self.assertEqual(
            run_agent.call_args.kwargs["task_metadata"]["scheduledTaskId"],
            scheduled.id,
        )
        self.assertIn(f"Scheduled task {scheduled.id}", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
