from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call, patch

from vibeagent.cli_interactive_project_runtime import InteractiveProjectRuntime


class InteractiveProjectRuntimeTests(unittest.TestCase):
    def test_starts_project_services_and_delegates_runtime_updates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-project-runtime-") as base:
            root = Path(base)
            peer = Mock()
            plugin_updates = Mock()
            notifications = [Mock()]
            plugin_updates.collect_notifications.return_value = notifications
            plugin_updates.start.side_effect = [True, False]
            with (
                patch(
                    "vibeagent.cli_interactive_project_runtime.create_peer_runtime",
                    return_value=peer,
                ) as create_peer,
                patch(
                    "vibeagent.cli_interactive_project_runtime.PluginAutoUpdateRuntime",
                    return_value=plugin_updates,
                ) as create_plugin_updates,
            ):
                runtime = InteractiveProjectRuntime(root, "ask", initial_session_id="run-1")
                runtime.register_session("run-2")
                runtime.update_approval_policy("auto")

                self.assertEqual(runtime.collect_plugin_notifications(), notifications)
                self.assertFalse(runtime.start_plugin_updates())

        create_peer.assert_called_once_with(root.resolve(), "ask")
        create_plugin_updates.assert_called_once_with(root.resolve())
        self.assertEqual(plugin_updates.start.call_count, 2)
        peer.update_approval_policy.assert_called_once_with("auto")
        self.assertEqual(runtime.owned_session_ids, frozenset({"run-1", "run-2"}))

    def test_replacing_workflow_closes_previous_manager(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-project-runtime-") as base:
            with (
                patch(
                    "vibeagent.cli_interactive_project_runtime.create_peer_runtime",
                    return_value=None,
                ),
                patch("vibeagent.cli_interactive_project_runtime.PluginAutoUpdateRuntime"),
            ):
                runtime = InteractiveProjectRuntime(Path(base), "ask")
                first = Mock()
                second = Mock()

                self.assertIs(runtime.set_workflow(first), first)
                self.assertIs(runtime.set_workflow(second), second)
                runtime.close_workflow()

        first.close.assert_called_once_with()
        second.close.assert_called_once_with()
        self.assertIsNone(runtime.workflow)

    def test_close_releases_all_owned_resources_once(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-project-runtime-") as base:
            root = Path(base).resolve()
            additional = root / "shared"
            additional.mkdir()
            peer = Mock()
            plugin_updates = Mock()
            workflow = Mock()
            workspaces = {"run-1": Mock(), "run-2": Mock()}
            with (
                patch(
                    "vibeagent.cli_interactive_project_runtime.create_peer_runtime",
                    return_value=peer,
                ),
                patch(
                    "vibeagent.cli_interactive_project_runtime.PluginAutoUpdateRuntime",
                    return_value=plugin_updates,
                ),
                patch(
                    "vibeagent.cli_interactive_project_runtime.create_local_workspace",
                    side_effect=lambda _root, run_id, **_kwargs: workspaces[run_id],
                ) as create_workspace,
                patch(
                    "vibeagent.cli_interactive_project_runtime.stop_session_monitors"
                ) as stop_monitors,
                patch(
                    "vibeagent.cli_interactive_project_runtime.close_session_async_hooks"
                ) as close_async_hooks,
                patch("vibeagent.cli_interactive_project_runtime.close_project_lsp") as close_lsp,
            ):
                runtime = InteractiveProjectRuntime(root, "ask", initial_session_id="run-1")
                runtime.register_session("run-2")
                runtime.set_workflow(workflow)

                runtime.close((additional,), close_lsp=True)
                runtime.close((additional,), close_lsp=True)

        stop_monitors.assert_has_calls(
            [call(root, "run-1"), call(root, "run-2")],
            any_order=True,
        )
        self.assertEqual(create_workspace.call_count, 2)
        for workspace_call in create_workspace.call_args_list:
            self.assertEqual(workspace_call.kwargs["additional_roots"], (additional,))
        close_async_hooks.assert_has_calls(
            [call(workspaces["run-1"]), call(workspaces["run-2"])],
            any_order=True,
        )
        workflow.close.assert_called_once_with()
        peer.close.assert_called_once_with()
        plugin_updates.close.assert_called_once_with()
        close_lsp.assert_called_once_with(root)
        self.assertEqual(runtime.owned_session_ids, frozenset())
        self.assertIsNone(runtime.peer)


if __name__ == "__main__":
    unittest.main()
