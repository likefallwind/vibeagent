from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tests.test_plugins import write_demo_marketplace, write_demo_plugin
from vibeagent.cli_interactive import run_interactive_loop
from vibeagent.plugin_auto_update import PluginAutoUpdateNotification


class CliPluginTests(unittest.TestCase):
    def test_idle_loop_prints_plugin_auto_update_notifications(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-plugin-update-") as base:
            root = Path(base)
            updater = Mock()
            updater.start.return_value = True
            updater.collect_notifications.side_effect = [
                [
                    PluginAutoUpdateNotification(
                        marketplace="team-tools",
                        updated_plugins=("demo-plugin",),
                    )
                ]
            ]
            stdout = io.StringIO()

            def idle_input(_prompt, callback, *, input_func):  # type: ignore[no-untyped-def]
                callback()
                return "/exit"

            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.cli_interactive_project_runtime.create_peer_runtime", return_value=None),
                    patch("vibeagent.cli_interactive_project_runtime.PluginAutoUpdateRuntime", return_value=updater),
                    patch("vibeagent.cli_interactive.input_with_idle_callback", side_effect=idle_input),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(command_namespace={})
            finally:
                os.chdir(old_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIn("updated demo-plugin", stdout.getvalue())
        self.assertIn("/reload-plugins", stdout.getvalue())
        updater.close.assert_called_once()

    def test_plugin_lifecycle_commands_do_not_initialize_model_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-plugin-") as base:
            root = Path(base)
            write_demo_plugin(root)
            create_client = Mock(return_value=object())
            inputs = iter(
                [
                    "/plugin validate extensions/demo-plugin",
                    "/plugin install extensions/demo-plugin",
                    "/reload-plugins",
                    "/plugin disable demo-plugin",
                    "/plugin enable demo-plugin",
                    "/plugin details demo-plugin",
                    "/plugin uninstall demo-plugin",
                    "/exit",
                ]
            )
            stdout = io.StringIO()
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.cli_interactive_project_runtime.create_peer_runtime", return_value=None),
                    patch(
                        "vibeagent.cli_interactive.input_with_idle_callback",
                        side_effect=lambda _prompt, _callback, *, input_func: next(inputs),
                    ),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        create_chat_client_func=create_client,
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(exit_code, 0)
            create_client.assert_not_called()
            output = stdout.getvalue()
            self.assertIn("Plugin validation passed.", output)
            self.assertIn("Installed plugin demo-plugin 1.2.3", output)
            self.assertIn("Reloaded 1 enabled plugin", output)
            self.assertIn("Disabled plugin demo-plugin.", output)
            self.assertIn("Uninstalled plugin demo-plugin.", output)

    def test_marketplace_lifecycle_commands_do_not_initialize_model_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-marketplace-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            create_client = Mock(return_value=object())
            inputs = iter(
                [
                    "/plugin validate catalog",
                    "/plugin marketplace add catalog",
                    "/plugin marketplace list",
                    "/plugin install demo-plugin@team-tools",
                    "/plugin marketplace details team-tools",
                    "/plugin marketplace update team-tools",
                    "/plugin marketplace remove team-tools",
                    "/exit",
                ]
            )
            stdout = io.StringIO()
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
                    patch("vibeagent.cli_interactive_project_runtime.create_peer_runtime", return_value=None),
                    patch(
                        "vibeagent.cli_interactive.input_with_idle_callback",
                        side_effect=lambda _prompt, _callback, *, input_func: next(inputs),
                    ),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        create_chat_client_func=create_client,
                    )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(exit_code, 0)
            create_client.assert_not_called()
            output = stdout.getvalue()
            self.assertIn("Marketplace validation passed.", output)
            self.assertIn("Added marketplace team-tools", output)
            self.assertIn("Installed plugin demo-plugin 1.2.3 (enabled) from team-tools.", output)
            self.assertIn("Updated marketplace team-tools", output)
            self.assertIn("Removed marketplace team-tools and its installed plugins.", output)


if __name__ == "__main__":
    unittest.main()
