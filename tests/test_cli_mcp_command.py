from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.cli import main
from vibeagent.cli_args import has_local_flag, parse_args
from vibeagent.cli_mcp_command_args import decode_mcp_command_arguments


class CliMcpCommandTests(unittest.TestCase):
    def test_parser_preserves_mcp_argument_array_and_global_prefix(self) -> None:
        direct = parse_args(["mcp", "add", "demo", "--", "python", "-m", "server"])
        prefixed = parse_args(["--json", "--cwd", "/tmp", "mcp", "get", "demo"])
        passthrough = parse_args(
            ["mcp", "add", "demo", "--", "python", "--cwd", "child", "--json"]
        )
        ordinary = parse_args(["fix", "mcp", "integration"])

        self.assertEqual(
            decode_mcp_command_arguments(direct.mcp_command),
            ["add", "demo", "--", "python", "-m", "server"],
        )
        self.assertEqual(decode_mcp_command_arguments(prefixed.mcp_command), ["get", "demo"])
        self.assertEqual(
            decode_mcp_command_arguments(passthrough.mcp_command),
            ["add", "demo", "--", "python", "--cwd", "child", "--json"],
        )
        self.assertFalse(passthrough.json)
        self.assertTrue(prefixed.json)
        self.assertEqual(prefixed.task, [])
        self.assertTrue(has_local_flag(prefixed))
        self.assertIsNone(ordinary.mcp_command)
        self.assertEqual(ordinary.task, ["fix", "mcp", "integration"])

    def test_list_is_provider_free_and_does_not_create_session_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-mcp-") as base:
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
                exit_code = main(["--cwd", str(project), "mcp", "list"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue(), "No MCP servers configured.\n")
            self.assertFalse(project.joinpath(".vibeagent").exists())
            create_chat_client.assert_not_called()

    def test_add_json_get_and_remove_use_existing_scoped_store(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-mcp-write-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            server = json.dumps({"type": "stdio", "command": sys.executable, "args": []})

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                add_code, add_payload = self._run_json(
                    [
                        "--json",
                        "--cwd",
                        str(project),
                        "mcp",
                        "add-json",
                        "--scope",
                        "project",
                        "demo",
                        server,
                    ]
                )
                get_code, get_payload = self._run_json(
                    ["mcp", "get", "demo", "--cwd", str(project), "--json"]
                )
                remove_code, remove_payload = self._run_json(
                    [
                        "--json",
                        "--cwd",
                        str(project),
                        "mcp",
                        "remove",
                        "--scope",
                        "project",
                        "demo",
                    ]
                )

            self.assertEqual(add_code, 0)
            self.assertTrue(add_payload["mcp"]["changed"])
            self.assertIn("Added MCP server demo", add_payload["text"])
            self.assertEqual(get_code, 0)
            self.assertFalse(get_payload["mcp"]["changed"])
            self.assertIn("MCP server demo", get_payload["text"])
            self.assertEqual(remove_code, 0)
            self.assertTrue(remove_payload["mcp"]["changed"])
            stored = json.loads(project.joinpath(".mcp.json").read_text(encoding="utf-8"))
            self.assertNotIn("demo", stored.get("mcpServers", {}))

    def test_invalid_subcommand_fails_without_provider(self) -> None:
        stdout = io.StringIO()
        with patch("vibeagent.cli.create_chat_client") as create_chat_client, redirect_stdout(stdout):
            exit_code = main(["mcp", "unknown"])

        self.assertEqual(exit_code, 2)
        self.assertTrue(stdout.getvalue().startswith("Usage: vibeagent mcp"))
        create_chat_client.assert_not_called()

    def test_help_is_successful_and_provider_free(self) -> None:
        for argv in (["mcp"], ["mcp", "--help"], ["mcp", "help"]):
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 0)
                self.assertTrue(
                    stdout.getvalue().startswith("MCP commands:\nUsage: vibeagent mcp")
                )
                create_chat_client.assert_not_called()

    def _run_json(self, argv: list[str]) -> tuple[int, dict[str, object]]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(argv)
        return exit_code, json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
