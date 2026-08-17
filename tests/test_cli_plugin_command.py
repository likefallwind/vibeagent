from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_plugins import write_demo_plugin
from vibeagent.cli import main
from vibeagent.cli_args import has_local_flag, parse_args
from vibeagent.cli_plugin_command_args import decode_plugin_command_arguments


class CliPluginCommandTests(unittest.TestCase):
    def test_parser_preserves_plugin_arguments_aliases_and_global_options(self) -> None:
        direct = parse_args(["plugin", "install", "extensions/team tools", "--scope", "project"])
        alias = parse_args(["--json", "plugins", "details", "demo", "--cwd", "/tmp"])
        ordinary = parse_args(["fix", "plugin", "integration"])

        self.assertEqual(
            decode_plugin_command_arguments(direct.plugin_command),
            ["install", "extensions/team tools", "--scope", "project"],
        )
        self.assertEqual(
            decode_plugin_command_arguments(alias.plugin_command),
            ["details", "demo"],
        )
        self.assertTrue(alias.json)
        self.assertEqual(alias.cwd, "/tmp")
        self.assertEqual(alias.task, [])
        self.assertTrue(has_local_flag(alias))
        self.assertIsNone(ordinary.plugin_command)
        self.assertEqual(ordinary.task, ["fix", "plugin", "integration"])

    def test_list_is_provider_free_and_does_not_create_session_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-plugin-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            stdout = io.StringIO()

            with (
                patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", str(project), "plugins", "list"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "No plugins installed.\n")
            self.assertFalse(project.joinpath(".vibeagent/sessions").exists())
            create_chat_client.assert_not_called()

    def test_validate_install_details_disable_enable_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-plugin-write-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            write_demo_plugin(project)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                validate_code, validate_payload = self._run_json(
                    ["--json", "--cwd", str(project), "plugin", "validate", "extensions/demo-plugin"]
                )
                install_code, install_payload = self._run_json(
                    ["plugin", "install", "extensions/demo-plugin", "--cwd", str(project), "--json"]
                )
                details_code, details_payload = self._run_json(
                    ["--cwd", str(project), "plugins", "details", "demo-plugin", "--json"]
                )
                disable_code, disable_payload = self._run_json(
                    ["plugin", "disable", "demo-plugin", "--json", "--cwd", str(project)]
                )
                enable_code, enable_payload = self._run_json(
                    ["plugin", "enable", "demo-plugin", "--cwd", str(project), "--json"]
                )
                uninstall_code, uninstall_payload = self._run_json(
                    ["--json", "plugin", "uninstall", "demo-plugin", "--cwd", str(project)]
                )

            self.assertEqual(validate_code, 0)
            self.assertFalse(validate_payload["plugin"]["changed"])
            self.assertIn("Plugin validation passed.", validate_payload["text"])
            self.assertEqual(install_code, 0)
            self.assertTrue(install_payload["plugin"]["changed"])
            self.assertIn("Installed plugin demo-plugin 1.2.3", install_payload["text"])
            self.assertEqual(details_code, 0)
            self.assertIn("Plugin demo-plugin 1.2.3", details_payload["text"])
            self.assertEqual(disable_code, 0)
            self.assertTrue(disable_payload["plugin"]["changed"])
            self.assertEqual(enable_code, 0)
            self.assertTrue(enable_payload["plugin"]["changed"])
            self.assertEqual(uninstall_code, 0)
            self.assertTrue(uninstall_payload["plugin"]["changed"])

    def test_invalid_and_missing_plugins_fail_without_provider(self) -> None:
        for argv, expected_code, prefix in (
            (["plugin", "unknown"], 2, "Usage: vibeagent plugin"),
            (["plugin", "details", "missing"], 1, "Plugin error:"),
        ):
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, expected_code)
                self.assertTrue(stdout.getvalue().startswith(prefix))
                create_chat_client.assert_not_called()

    def test_help_is_successful_and_provider_free(self) -> None:
        for argv in (["plugin"], ["plugins", "--help"], ["plugin", "help"]):
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 0)
                self.assertTrue(
                    stdout.getvalue().startswith("Plugin commands:\nUsage: vibeagent plugin")
                )
                create_chat_client.assert_not_called()

    def _run_json(self, argv: list[str]) -> tuple[int, dict[str, object]]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(argv)
        return exit_code, json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
