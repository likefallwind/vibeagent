from __future__ import annotations

from pathlib import Path
from io import StringIO
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from vibeagent.action_dispatcher import execute_action
from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.agent_monitor_notifications import inject_monitor_notifications
from vibeagent.background_delegate_runtime import stop_background_delegate_task
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.monitor_runtime import collect_monitor_notifications
from vibeagent.process_registry import read_persistent_process_record
from vibeagent.types import ChatMessage, MonitorAction, TaskStopAction
from vibeagent.workspace_core import create_run_workspace


class MonitorTests(unittest.TestCase):
    def test_parser_supports_claude_alias_defaults_and_persistent_mode(self) -> None:
        action = parse_tool_action(
            "Monitor",
            {"command": "python3 watcher.py", "description": "Watch build output"},
        )
        persistent = parse_tool_action(
            "Monitor",
            {
                "command": "python3 watcher.py",
                "description": "Watch continuously",
                "persistent": True,
                "timeout_ms": 3_600_000,
            },
        )

        self.assertEqual(
            action,
            MonitorAction(
                type="monitor",
                command="python3 watcher.py",
                description="Watch build output",
            ),
        )
        self.assertTrue(persistent.persistent)
        self.assertEqual(persistent.timeout_ms, 0)
        with self.assertRaisesRegex(ActionParseError, "requires a description"):
            parse_tool_action("Monitor", {"command": "python3 watcher.py"})
        with self.assertRaisesRegex(ActionParseError, "at most 3600000"):
            parse_tool_action(
                "Monitor",
                {
                    "command": "python3 watcher.py",
                    "description": "Watch",
                    "timeout_ms": 3_600_001,
                },
            )

    def test_monitor_requires_command_approval(self) -> None:
        request = build_approval_request(
            MonitorAction(
                type="monitor",
                command="python3 watcher.py",
                description="Watch build output",
            )
        )

        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.action_type, "monitor")
        self.assertIn("python3 watcher.py", request.target)
        self.assertIn("Watch build output", request.risk)

    def test_stdout_lines_and_exit_are_delivered_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-lines")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"print('alpha'); print('beta')\"",
                    description="Capture two lines",
                    timeout_ms=5_000,
                ),
            )
            self.assertTrue(observation.ok)

            notifications = self._collect_until_exit(workspace)
            self.assertEqual(
                [item.message for item in notifications if item.status == "output"],
                ["alpha", "beta"],
            )
            self.assertEqual(len([item for item in notifications if item.status == "exited"]), 1)
            self.assertEqual(collect_monitor_notifications(workspace), [])

    def test_timeout_terminates_monitor_and_reports_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-timeout")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"import time; time.sleep(30)\"",
                    description="Timeout sleeper",
                    timeout_ms=100,
                ),
            )
            self.assertTrue(observation.ok)
            record = read_persistent_process_record(workspace.root, observation.task_id)
            self.assertIsNotNone(record)
            assert record is not None and record.monitor_started_at is not None

            notifications = collect_monitor_notifications(
                workspace,
                now=record.monitor_started_at + 1,
            )
            self.assertEqual([item.status for item in notifications], ["timed_out"])
            self.assertEqual(collect_monitor_notifications(workspace), [])

    def test_task_stop_stops_persistent_monitor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-stop")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"import time; print('ready'); time.sleep(30)\"",
                    description="Persistent sleeper",
                    persistent=True,
                    timeout_ms=0,
                ),
            )
            self.assertTrue(observation.ok)

            stopped = stop_background_delegate_task(
                workspace,
                TaskStopAction(type="task_stop", task_id=observation.task_id),
            )
            self.assertTrue(stopped.ok)
            self.assertTrue(stopped.stopped)
            self.assertIn("Stopped monitor", stopped.message)

    def test_agent_notification_is_untrusted_and_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = create_run_workspace(Path(tmp), run_id="monitor-inject")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"print('event line')\"",
                    description="Inject output",
                    timeout_ms=5_000,
                ),
            )
            self.assertTrue(observation.ok)
            self._collect_until_output_available(workspace)
            messages: list[ChatMessage] = []

            delivered = inject_monitor_notifications(
                workspace,
                messages,
                iteration=2,
                logger=None,
            )

            self.assertGreater(delivered, 0)
            self.assertEqual(messages[-1].role, "user")
            self.assertIn("Untrusted background Monitor", messages[-1].content)
            self.assertIn("event line", messages[-1].content)

    def test_idle_interactive_session_wakes_for_monitor_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-monitor-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="source-run")
            observation = execute_action(
                workspace,
                MonitorAction(
                    type="monitor",
                    command="python3 -u -c \"import time; print('idle event'); time.sleep(30)\"",
                    description="Wake idle agent",
                    persistent=True,
                    timeout_ms=0,
                ),
            )
            self.assertTrue(observation.ok)
            self._collect_until_output_available(workspace)
            run_agent = Mock(return_value=SimpleNamespace(run_id="monitor-run"))

            def trigger_idle(_prompt, callback, *, input_func, interval_seconds=1.0):
                callback()
                return "/exit"

            with (
                patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=trigger_idle),
                patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                patch("vibeagent.cli_interactive.print_agent_result"),
                patch("vibeagent.cli_interactive.Path.cwd", return_value=root),
                patch("sys.stdout", new_callable=StringIO) as stdout,
            ):
                exit_code = run_interactive_loop(
                    command_namespace={},
                    create_chat_client_func=Mock(return_value=object()),
                    run_agent_func=run_agent,
                    get_resume_context_func=Mock(
                        return_value=("monitor-run", "next context", "loaded")
                    ),
                    initial_resume_run_id="source-run",
                    initial_resume_context="source context",
                )
            self.assertIsNone(
                read_persistent_process_record(workspace.root, observation.task_id)
            )

        self.assertEqual(exit_code, 0)
        prompt = run_agent.call_args.args[0]
        self.assertIn("Untrusted background Monitor", prompt)
        self.assertIn("idle event", prompt)
        self.assertEqual(run_agent.call_args.kwargs["task_metadata"]["source"], "monitor")
        self.assertIn("Monitor event received", stdout.getvalue())

    @staticmethod
    def _collect_until_exit(workspace) -> list:
        collected = []
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            collected.extend(collect_monitor_notifications(workspace))
            if any(item.status in {"exited", "timed_out"} for item in collected):
                return collected
            time.sleep(0.02)
        raise AssertionError("monitor did not exit")

    @staticmethod
    def _collect_until_output_available(workspace) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            records = list((workspace.root / ".vibeagent" / "processes").glob("*.json"))
            if records:
                record = read_persistent_process_record(workspace.root, records[0].stem)
                if record is not None and record.stdout_path.exists() and record.stdout_path.stat().st_size:
                    return
            time.sleep(0.02)
        raise AssertionError("monitor produced no output")


if __name__ == "__main__":
    unittest.main()
