from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from vibeagent.cli_interactive_idle import (
    InteractiveIdleContext,
    run_interactive_idle_tasks,
)


class CliInteractiveIdleTests(unittest.TestCase):
    def test_peer_turn_refreshes_session_id_before_followup_delivery(self) -> None:
        state = {"run_id": "old-run"}
        workspace = SimpleNamespace(session_dir=Path("/tmp/session"))
        project_runtime = Mock()
        project_runtime.peer = object()
        project_runtime.collect_plugin_notifications.return_value = []
        recap = Mock()

        def run_code_task(task: str, metadata: dict[str, object] | None):
            self.assertEqual(task, "peer task")
            self.assertEqual(metadata, {"source": "peer"})
            state["run_id"] = "new-run"
            return object(), None

        context = InteractiveIdleContext(
            project_root=Path("/tmp/project"),
            project_runtime=project_runtime,
            file_changed_runtime=None,
            config_change_runtime=None,
            idle_notification=Mock(due=Mock(return_value=False)),
            current_resume_run_id=lambda: state["run_id"],
            current_pending_workspace=lambda: None,
            additional_directories=(),
            safe_mode=False,
            bare_mode=False,
            disable_slash_commands=False,
            setting_sources=("user", "project", "local"),
            settings_override_json=None,
            invocation_plugin_dirs=(),
            current_approval_handler=lambda: None,
            current_approval_policy=lambda: "ask",
            command_timeout_ms=lambda: 30_000,
            scheduled_tasks_enabled=lambda: True,
            run_notification_hooks=Mock(),
            run_code_task=run_code_task,
            maybe_generate_automatic_recap=recap,
        )

        with (
            patch(
                "vibeagent.cli_interactive_idle.peer_messages_as_task",
                return_value=("peer task", {"source": "peer"}),
            ),
            patch(
                "vibeagent.cli_interactive_idle.create_local_workspace",
                return_value=workspace,
            ) as create_workspace,
            patch(
                "vibeagent.cli_interactive_idle.collect_async_hook_notifications",
                return_value=[],
            ),
            patch(
                "vibeagent.cli_interactive_idle.collect_monitor_notifications",
                return_value=[],
            ),
            patch(
                "vibeagent.cli_interactive_idle.collect_due_scheduled_tasks",
                return_value=[],
            ),
        ):
            with redirect_stdout(io.StringIO()):
                run_interactive_idle_tasks(context)

        self.assertEqual(
            [call.args[1] for call in create_workspace.call_args_list],
            ["new-run", "new-run"],
        )
        recap.assert_called_once_with()

    def test_missing_session_only_checks_recap_after_local_notifications(self) -> None:
        project_runtime = Mock()
        project_runtime.peer = None
        project_runtime.collect_plugin_notifications.return_value = []
        recap = Mock()
        context = InteractiveIdleContext(
            project_root=Path("/tmp/project"),
            project_runtime=project_runtime,
            file_changed_runtime=None,
            config_change_runtime=None,
            idle_notification=Mock(due=Mock(return_value=True)),
            current_resume_run_id=lambda: None,
            current_pending_workspace=lambda: None,
            additional_directories=(),
            safe_mode=False,
            bare_mode=False,
            disable_slash_commands=False,
            setting_sources=("user", "project", "local"),
            settings_override_json=None,
            invocation_plugin_dirs=(),
            current_approval_handler=lambda: None,
            current_approval_policy=lambda: "ask",
            command_timeout_ms=lambda: 30_000,
            scheduled_tasks_enabled=lambda: True,
            run_notification_hooks=Mock(),
            run_code_task=Mock(),
            maybe_generate_automatic_recap=recap,
        )

        with patch("vibeagent.cli_interactive_idle.create_local_workspace") as create_workspace:
            run_interactive_idle_tasks(context)

        create_workspace.assert_not_called()
        context.run_notification_hooks.assert_not_called()
        recap.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
